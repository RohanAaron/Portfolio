"""
bigram_boost.py
===============
Detects adjective-noun pairs in a prompt using NLTK POS tagging,
then encodes them as phrases using CLIP to get a single combined
embedding direction for boosting.

Integrates with text_to_text_entropy_ratio.py to replace unigram
boosting of adjectives with bigram phrase-level boosting.

Usage (standalone test):
    python bigram_boost.py --prompt "metal crown, crimson gemstones, golden polished band"

Usage (in entropy script):
    from bigram_boost import detect_bigrams, get_phrase_boost_map
"""

import nltk
import argparse
from typing import List, Tuple, Dict

for pkg in ['punkt', 'punkt_tab', 'averaged_perceptron_tagger', 'averaged_perceptron_tagger_eng']:
    try:
        nltk.download(pkg, quiet=True)
    except Exception:
        pass


# ============================================================================
# BIGRAM DETECTION
# ============================================================================

def detect_bigrams(prompt: str) -> List[Tuple[str, str]]:
    """
    Detect adjective-noun pairs in a prompt using NLTK POS tagging.

    FIX (see change log below): NLTK's tagger is a statistical model with
    genuinely ambiguous cases (e.g. "leather" in "black leather wallet" can
    read as either adjective or noun) — even full-sentence context doesn't
    always resolve this. Two changes address the confirmed failure modes:

    1. MATERIAL_WORDS override — same pattern as the existing COLOR_WORDS
       list. Words like 'leather', 'wood', 'metal' are forced to count as
       adjectives regardless of what NLTK guesses that time. Confirmed bug
       fixed: "black leather wallet" was pairing ('black', 'leather')
       instead of ('black', 'wallet') because 'leather' got tagged NN.

    2. Last-noun-in-run scanning — previously stopped at the FIRST
       noun-tagged word found while scanning forward, which breaks when a
       mistagged word (or a repeated word like "rectangular" appearing
       twice in one prompt) sits between the adjective and the true head
       noun. Now scans through a run of CONSECUTIVE noun-tagged words and
       uses the LAST one — matching this dataset's confirmed prompt
       pattern "[color] [material] HEADNOUN with parts". Confirmed bug
       fixed: "small rectangular window" was pairing ('small',
       'rectangular') instead of ('small', 'window').

    Args:
        prompt: The text prompt (comma-separated or natural language)

    Returns:
        List of (adjective, noun) tuples representing paired tokens
    """
    cleaned = prompt.lower().replace(",", " ").replace(";", " ")
    tokens = nltk.word_tokenize(cleaned)
    try:
        tagged = nltk.pos_tag(tokens)
    except Exception:
        tagged = [(t, 'NN') for t in tokens]

    ADJ_TAGS = {'JJ', 'JJR', 'JJS', 'VBD', 'VBN'}

    COLOR_WORDS = {
        'crimson', 'scarlet', 'ivory', 'ebony', 'azure', 'amber', 'ochre',
        'magenta', 'cyan', 'teal', 'maroon', 'beige', 'turquoise', 'indigo',
        'violet', 'khaki', 'tan', 'bronze', 'copper', 'silver', 'gold',
        'charcoal', 'obsidian', 'pearl', 'coral', 'salmon', 'rust', 'olive',
    }

    # NEW: material/texture words NLTK frequently mistags as nouns even
    # with full sentence context (genuinely ambiguous — e.g. "leather" can
    # function as either). Force these to always count as adjectives here,
    # matching how this dataset's prompts consistently use them.
    MATERIAL_WORDS = {
        'leather', 'wood', 'wooden', 'metal', 'metallic', 'glass', 'ceramic',
        'plastic', 'rubber', 'fabric', 'wool', 'cotton', 'silk', 'stone',
        'marble', 'granite', 'brick', 'paper', 'cardboard', 'velvet',
        'satin', 'steel', 'iron', 'aluminum', 'brass', 'chrome', 'crystal',
        'porcelain', 'clay', 'canvas', 'foam', 'felt', 'suede', 'denim',
    }

    NOUN_TAGS = {'NN', 'NNS', 'NNP', 'NNPS'}

    bigrams = []
    for i, (token, pos) in enumerate(tagged):
        if pos in ADJ_TAGS or token in COLOR_WORDS or token in MATERIAL_WORDS:
            # Scan forward through a RUN of consecutive noun-tagged words
            # and take the LAST one — the true head noun — instead of
            # stopping at the first (which may itself be a mistagged
            # adjective/material word, or a repeated word that isn't the
            # actual target).
            last_noun = None
            j = i + 1
            scan_limit = min(i + 4, len(tagged))  # slightly wider window
            while j < scan_limit:
                next_token, next_pos = tagged[j]
                if next_token in {',', '.', ';', ':', '-'}:
                    break  # punctuation ends the run
                if next_pos in NOUN_TAGS:
                    last_noun = next_token
                    j += 1
                    continue  # keep scanning — might be another noun after this
                elif next_pos in ADJ_TAGS or next_token in COLOR_WORDS or next_token in MATERIAL_WORDS:
                    # another modifier in between (e.g. "small rectangular
                    # window") — keep scanning past it, don't stop here
                    j += 1
                    continue
                else:
                    break  # some other word type — stop scanning
            if last_noun is not None:
                bigrams.append((token, last_noun))

    seen = set()
    unique_bigrams = []
    for pair in bigrams:
        if pair not in seen:
            seen.add(pair)
            unique_bigrams.append(pair)

    return unique_bigrams


def get_adj_to_noun_map(prompt: str) -> Dict[str, str]:
    bigrams = detect_bigrams(prompt)
    return {adj: noun for adj, noun in bigrams}


def get_noun_to_adjs_map(prompt: str) -> Dict[str, List[str]]:
    bigrams = detect_bigrams(prompt)
    noun_to_adjs = {}
    for adj, noun in bigrams:
        if noun not in noun_to_adjs:
            noun_to_adjs[noun] = []
        noun_to_adjs[noun].append(adj)
    return noun_to_adjs


# ============================================================================
# PHRASE-LEVEL BOOST MAP  (unchanged from original — no bugs found here)
# ============================================================================

def get_phrase_boost_map(
    prompt: str,
    token_similarities: Dict[str, float],
    boost_budget: int = 5,
    max_boost: float = 1.2,
    threshold: float = 0.65,
) -> Dict[str, float]:
    adj_to_noun = get_adj_to_noun_map(prompt)
    noun_to_adjs = get_noun_to_adjs_map(prompt)

    intervention_config = {}
    boost_candidates = []
    processed_adjs = set()

    for noun, adjs in noun_to_adjs.items():
        noun_sim = token_similarities.get(noun, 1.0)

        if noun_sim < threshold:
            adj_sims = [(adj, token_similarities.get(adj, 0.5)) for adj in adjs]
            adj_sims.sort(key=lambda x: x[1])

            for adj, adj_sim in adj_sims:
                phrase = f"{adj} {noun}"
                combined_sim = (adj_sim + noun_sim) / 2

                strength = (threshold - combined_sim) / threshold
                raw_boost = 1.0 + (strength * (max_boost - 1.0))
                raw_boost = round(min(raw_boost, max_boost), 3)

                boost_candidates.append({
                    'token': phrase,
                    'type': 'bigram',
                    'adj': adj,
                    'noun': noun,
                    'similarity': combined_sim,
                    'raw_boost': raw_boost,
                })
                processed_adjs.add(adj)
        else:
            for adj in adjs:
                processed_adjs.add(adj)
                intervention_config[adj] = 1.0

    all_tokens = list(token_similarities.keys())
    for token in all_tokens:
        if token in processed_adjs:
            continue
        if token in noun_to_adjs:
            continue

        sim = token_similarities.get(token, 1.0)
        if sim < threshold:
            strength = (threshold - sim) / threshold
            raw_boost = 1.0 + (strength * (max_boost - 1.0))
            raw_boost = round(min(raw_boost, max_boost), 3)
            boost_candidates.append({
                'token': token,
                'type': 'unigram',
                'similarity': sim,
                'raw_boost': raw_boost,
            })

    boost_candidates.sort(key=lambda x: x['similarity'])

    boosted_count = 0
    for candidate in boost_candidates:
        if boosted_count >= boost_budget:
            intervention_config[candidate['token']] = 1.0
        else:
            intervention_config[candidate['token']] = candidate['raw_boost']
            boosted_count += 1

    return intervention_config, boost_candidates[:boost_budget]


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="Black leather wallet with a rectangular shape and a small rectangular window displaying the time.")
    args = parser.parse_args()

    prompt = args.prompt
    print(f"\nPrompt: {prompt}")
    print("=" * 60)

    bigrams = detect_bigrams(prompt)
    print(f"\nDetected adjective-noun pairs ({len(bigrams)}):")
    for adj, noun in bigrams:
        print(f"  '{adj}' -> '{noun}'  (phrase: '{adj} {noun}')")
