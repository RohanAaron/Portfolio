"""
Semantic_score_VLM_VQA.py — VQA scoring with yes/no + open-ended cross-check
==============================================================================
Same drop-in interface as before (same evaluation_results.json schema,
same class name / run_pipeline signature), but each token now gets
TWO differently-framed questions instead of one:

  1. YES/NO framing:  "Is this red?"           -> P(yes)
  2. OPEN framing:    "What color is this?"    -> free-text answer,
                       checked for whether the target word appears

Why: large VLMs (including Qwen2-VL) are known to lean toward answering
"yes" on binary questions even when the true answer is "no". Asking the
same thing a second way, where there's no yes/no bias to lean on, catches
cases where the yes/no score was likely just optimism, not a real signal.

COMBINING: both scores are already 0-1 (open-ended match is scored 1.0
match / 0.0 no match), so no extra unit conversion needed. Final score
= average of the two when both are available, otherwise just the
yes/no score (open-ended check only applies to tokens we can build a
good open question for: colors, shapes, materials, and nouns).

Disagreement between the two (e.g. yes/no says 0.9, open-ended says 0.0)
is logged directly to the console and saved in the output JSON — these
are exactly the cases worth spot-checking for yes-bias.

USAGE: identical to before — python Semantic_score_VLM_VQA.py
"""

import os
import sys
from pathlib import Path
import numpy as np
import json
import cv2
from PIL import Image
import torch
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
import nltk
from nltk.tag import pos_tag

sys.path.insert(0, '/projects/tealab/rohan19/Trellis/TRELLIS')
from prompt_filter import filter_to_boostable_tokens

print("📦 Downloading NLTK data...")
try:
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('averaged_perceptron_tagger_eng', quiet=True)
    print("✓ NLTK data ready\n")
except Exception as e:
    print(f"⚠ Warning: NLTK data issue: {e}\n")

print("✓ All dependencies loaded\n")


# ============================================================================
# CATEGORY KEYWORD SETS — used to build good open-ended questions
# ============================================================================

COLOR_WORDS = {
    'red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'white',
    'black', 'brown', 'gray', 'grey', 'gold', 'golden', 'silver', 'tan',
    'beige', 'maroon', 'navy', 'teal', 'cyan', 'magenta', 'violet', 'crimson',
}
SHAPE_WORDS = {
    'round', 'square', 'circular', 'polygonal', 'curved', 'flat', 'triangular',
    'oval', 'spherical', 'cubic', 'rectangular', 'pointed', 'straight',
    'angular', 'octagonal', 'hexagonal', 'conical', 'cylindrical',
}
MATERIAL_WORDS = {
    'wooden', 'wood', 'metal', 'metallic', 'plastic', 'ceramic', 'rubber',
    'glass', 'leather', 'paper', 'fabric', 'stone', 'clay', 'cardboard',
    'porcelain', 'steel', 'iron', 'bronze', 'copper', 'cloth', 'foam',
}


def classify_category(token: str):
    t = token.lower()
    if t in COLOR_WORDS:
        return 'color'
    if t in SHAPE_WORDS:
        return 'shape'
    if t in MATERIAL_WORDS:
        return 'material'
    return None


# ============================================================================
# PART 1: QWEN VLM PIPELINE — YES/NO PROBABILITY + OPEN-ENDED GENERATION
# ============================================================================

class QWENLocalVLMPipelineVQA:
    def __init__(self, model_name="Qwen/Qwen2-VL-7B-Instruct", device='cuda'):
        print(f"Loading {model_name} on {device}...")

        self.processor = AutoProcessor.from_pretrained(
            model_name, min_pixels=256*28*28, max_pixels=1280*28*28, trust_remote_code=True
        )
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_name, torch_dtype=torch.float16, device_map="auto", trust_remote_code=True
        )
        try:
            self.model = self.model.to_bettertransformer()
            print("✓ Model loaded with FlashAttention2")
        except Exception:
            print("⚠ Loading with standard attention")

        print("✓ VLM ready\n")
        self.device = device

        self._yes_ids = list(set(
            self.processor.tokenizer.encode("yes", add_special_tokens=False) +
            self.processor.tokenizer.encode("Yes", add_special_tokens=False) +
            self.processor.tokenizer.encode(" yes", add_special_tokens=False) +
            self.processor.tokenizer.encode(" Yes", add_special_tokens=False)
        ))
        self._no_ids = list(set(
            self.processor.tokenizer.encode("no", add_special_tokens=False) +
            self.processor.tokenizer.encode("No", add_special_tokens=False) +
            self.processor.tokenizer.encode(" no", add_special_tokens=False) +
            self.processor.tokenizer.encode(" No", add_special_tokens=False)
        ))

    def preprocess_video(self, video_path, num_frames=8):
        cap = cv2.VideoCapture(str(video_path))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            raise ValueError(f"Could not read video: {video_path}")
        indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(frame_rgb))
        cap.release()
        return frames

    def _get_visual_content(self, image_or_video):
        if isinstance(image_or_video, (str, Path)):
            path = Path(image_or_video)
            if path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                return self.preprocess_video(path)
            return [Image.open(path)]
        elif isinstance(image_or_video, list):
            return image_or_video
        return [image_or_video]

    def _build_messages(self, visual_content, prompt_text):
        return [{
            "role": "user",
            "content": [
                *[{"type": "image", "image": frame} for frame in visual_content],
                {"type": "text", "text": prompt_text}
            ]
        }]

    def ask_yes_no(self, image_or_video, question: str) -> float:
        """Returns P(yes) normalized against P(yes)+P(no)."""
        visual_content = self._get_visual_content(image_or_video)
        prompt = f"{question} Answer with only one word: yes or no."
        messages = self._build_messages(visual_content, prompt)

        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(
            text=[text], images=visual_content, videos=None, padding=True, return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs, max_new_tokens=1, do_sample=False,
                output_scores=True, return_dict_in_generate=True,
            )

        logits = outputs.scores[0][0]
        probs = torch.softmax(logits.float(), dim=-1)
        p_yes = sum(probs[i].item() for i in self._yes_ids if i < probs.shape[0])
        p_no = sum(probs[i].item() for i in self._no_ids if i < probs.shape[0])
        total = p_yes + p_no
        return 0.5 if total < 1e-6 else p_yes / total

    def ask_open_ended(self, image_or_video, question: str) -> str:
        """Free-text short answer, used for the cross-check."""
        visual_content = self._get_visual_content(image_or_video)
        prompt = f"{question} Answer in a few words only."
        messages = self._build_messages(visual_content, prompt)

        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(
            text=[text], images=visual_content, videos=None, padding=True, return_tensors="pt"
        ).to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(**inputs, max_new_tokens=20, do_sample=False)

        generated = [out[len(inp):] for inp, out in zip(inputs.input_ids, output_ids)]
        answer = self.processor.batch_decode(generated, skip_special_tokens=True)[0].strip().lower()
        return answer


# ============================================================================
# PART 2: TOKEN EXTRACTION + DUAL-FRAMING QUESTION LOGIC
# ============================================================================

class VQATokenAnalyzer:
    def __init__(self):
        self.pos_tags = {
            'NN': 'noun', 'NNS': 'noun', 'NNP': 'noun', 'NNPS': 'noun',
            'JJ': 'adjective', 'JJR': 'adjective', 'JJS': 'adjective',
            'VB': 'verb', 'VBD': 'verb', 'VBG': 'verb', 'VBN': 'verb',
            'RB': 'adverb', 'RBR': 'adverb', 'RBS': 'adverb'
        }

    def tokenize_and_tag(self, text):
        tokens = nltk.word_tokenize(text.lower())
        try:
            tags = pos_tag(tokens)
        except Exception:
            tags = [(t, 'NN') for t in tokens]
        return tokens, tags

    def filter_meaningful_tokens(self, tokens, pos_tags):
        meaningful = []
        for token, pos in zip(tokens, pos_tags):
            if pos[1] in self.pos_tags and len(token) > 2:
                meaningful.append({'token': token, 'pos': self.pos_tags.get(pos[1][:2], 'other')})
        return meaningful

    def build_yesno_question(self, token: str, pos: str) -> str:
        if pos == 'adjective':
            return f"Is the main object in this image {token}?"
        elif pos == 'noun':
            return f"Is there a {token} visible in this image?"
        else:
            return f"Does this image show {token}?"

    def get_open_questions(self, token: str, pos: str, category):
        """Returns a list of open-ended questions to ask for this token.
        For nouns, asks BOTH 'what is the object' and 'what parts/features
        are visible' — no more guessing which noun is 'the head' vs 'a
        part', since that guess kept breaking (grammar-dependent, and
        POS-tagging fails on bare comma-separated fragments with no
        sentence context). A match against EITHER answer counts as a
        pass. Slightly more compute for nouns, but no longer fragile."""
        if category == 'color':
            return ["What color is the main object in this image?"]
        elif category == 'shape':
            return ["What shape is the main object in this image?"]
        elif category == 'material':
            return ["What material does the main object appear to be made of?"]
        elif pos == 'noun':
            return [
                "What is the main object in this image? Answer with just the object name.",
                "What parts, components, or features can you see on this object? List them in a few words.",
            ]
        return []

    def _answer_contains_token(self, answer: str, token: str) -> bool:
        answer = answer.lower()
        token = token.lower()
        if token in answer:
            return True
        if token.endswith('s') and token[:-1] in answer:
            return True
        if (token + 's') in answer:
            return True
        return False

    def _categorize_entropy(self, score, low_threshold=0.5, high_threshold=0.75):
        if score < low_threshold:
            return 'high'
        elif score < high_threshold:
            return 'medium'
        return 'low'

    def analyze(self, text_t1: str, video_path, vlm_pipeline) -> dict:
        tokens, pos_tags = self.tokenize_and_tag(text_t1)
        meaningful = self.filter_meaningful_tokens(tokens, pos_tags)

        results = []
        scores = []
        disagreements = []

        for item in meaningful:
            token, pos = item['token'], item['pos']
            category = classify_category(token)

            yn_question = self.build_yesno_question(token, pos)
            p_yes = vlm_pipeline.ask_yes_no(video_path, yn_question)

            open_questions = self.get_open_questions(token, pos, category)
            open_answers = []
            open_score = None
            if open_questions:
                matched_any = False
                for oq in open_questions:
                    ans = vlm_pipeline.ask_open_ended(video_path, oq)
                    open_answers.append(ans)
                    if self._answer_contains_token(ans, token):
                        matched_any = True
                open_score = 1.0 if matched_any else 0.0

            if open_score is not None:
                final_score = (p_yes + open_score) / 2.0
                gap = abs(p_yes - open_score)
                disagreements.append({
                    'token': token, 'yes_no_score': p_yes, 'open_score': open_score,
                    'open_answers': open_answers, 'gap': gap,
                })
                if gap > 0.4:
                    print(f"    ⚠ DISAGREEMENT '{token}': yes/no={p_yes:.2f} vs "
                          f"open-ended={open_score:.2f} (answers: {open_answers})")
            else:
                final_score = p_yes

            scores.append(final_score)
            results.append({
                'token_t1': token,
                'pos': pos,
                'category': category,
                'yesno_question': yn_question,
                'yesno_score': float(p_yes),
                'open_questions': open_questions,
                'open_answers': open_answers,
                'open_score': open_score,
                'semantic_similarity': float(final_score),
                'best_match_t2': None,
                'top_3_matches': {},
                'entropy_category': self._categorize_entropy(final_score),
            })
            print(f"    Q: \"{yn_question}\" -> yes/no={p_yes:.3f}" +
                  (f"  |  open-check={open_score:.2f}" if open_score is not None else "") +
                  f"  ->  final={final_score:.3f}")

        avg = float(np.mean(scores)) if scores else 0.0
        return {
            'text_t1': text_t1,
            'text_t2': None,
            'tokens_t1': [r['token_t1'] for r in results],
            'tokens_t2': [],
            'token_comparisons': results,
            'average_similarity': avg,
            'low_entropy_tokens': [r for r in results if r['entropy_category'] == 'low'],
            'high_entropy_tokens': [r for r in results if r['entropy_category'] == 'high'],
            'disagreements': disagreements,
        }


# ============================================================================
# PART 3: PIPELINE MANAGER — SAME INTERFACE AS THE ORIGINAL
# ============================================================================

class CompletePipelineManager:
    def __init__(self):
        self.vlm_pipeline = QWENLocalVLMPipelineVQA(device='cuda')
        self.analyzer = VQATokenAnalyzer()

    def find_trellis_outputs(self, search_dir='./outputs', file_extension='.mp4'):
        search_path = Path(search_dir)
        if not search_path.exists():
            return None
        video_files = list(search_path.glob(f'*{file_extension}'))
        if not video_files:
            return None
        return str(max(video_files, key=lambda f: f.stat().st_mtime))

    def validate_file_path(self, file_path):
        path = Path(file_path)
        if not path.exists():
            return False
        return path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv', '.glb']

    def run_pipeline(self, original_prompt, trellis_video_path=None, auto_find_files=True):
        print("\n" + "=" * 70)
        print("SEMANTIC SCORE PIPELINE — VQA MODE (yes/no + open-ended cross-check)")
        print("=" * 70)

        video_file = None
        if trellis_video_path and self.validate_file_path(trellis_video_path):
            video_file = trellis_video_path
        if video_file is None:
            iter_video = os.environ.get('TRELLIS_VIDEO_PATH')
            if iter_video and Path(iter_video).exists():
                video_file = iter_video
        if video_file is None and auto_find_files:
            for search_dir in ['./.outputs', './outputs', './trellis/outputs']:
                video_file = self.find_trellis_outputs(search_dir=search_dir)
                if video_file:
                    break
        if video_file is None:
            print("❌ Could not find TRELLIS outputs")
            return None

        t1_filtered = filter_to_boostable_tokens(original_prompt)
        print(f"Prompt (filtered): {t1_filtered}")
        print(f"Video: {video_file}\n")

        try:
            analysis = self.analyzer.analyze(t1_filtered, video_file, self.vlm_pipeline)
        except Exception as e:
            print(f"❌ VQA analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return None

        print(f"\nAverage alignment (VQA, dual-check): {analysis['average_similarity']:.3f}")
        if analysis['disagreements']:
            print(f"⚠ {len(analysis['disagreements'])} token(s) had yes/no vs open-ended disagreement")

        results = {
            'original_prompt': original_prompt,
            't1_filtered': t1_filtered,
            'vlm_description_raw': '[VQA mode: no caption generated, dual-framing yes/no + open-ended used instead]',
            't2_filtered': '',
            'trellis_file': video_file,
            'semantic_analysis': analysis,
            'high_entropy_tokens': analysis['high_entropy_tokens'],
            'average_alignment_score': analysis['average_similarity'],
            'scoring_mode': 'vqa_dual_framing',
        }
        return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pipeline_manager = CompletePipelineManager()

    original_prompt = None
    PROMPT_FILE = 'prompt.txt'
    if Path(PROMPT_FILE).exists():
        with open(PROMPT_FILE, 'r') as f:
            original_prompt = f.read().strip()

    if not original_prompt:
        print("❌ Could not find a valid prompt in prompt.txt")
        sys.exit(1)

    result = pipeline_manager.run_pipeline(
        original_prompt=original_prompt,
        trellis_video_path=None,
        auto_find_files=True,
    )

    if result:
        with open("evaluation_results.json", "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Results saved to evaluation_results.json")
        print(f"Average Alignment Score: {result['average_alignment_score']:.3f}")
        print(f"High Entropy Tokens: {len(result['high_entropy_tokens'])}")
    else:
        print("\n❌ Pipeline failed")
        sys.exit(1)
