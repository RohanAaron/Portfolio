"""
prompt_filter.py
================
Standalone module that takes raw VLM natural language output and filters it
into a clean, boostable token list suitable for the TRELLIS pipeline.

Used by:
  - glb_to_prompt_v2.py  (to generate T1 from GLB description)
  - Semantic_score_VLM.py (to generate T2 from TRELLIS output description)

Both T1 and T2 pass through the same filter, making comparison symmetric.
"""

import nltk
import re

# Download required NLTK data silently
for pkg in ['punkt', 'punkt_tab', 'averaged_perceptron_tagger', 'averaged_perceptron_tagger_eng']:
    try:
        nltk.download(pkg, quiet=True)
    except Exception:
        pass

# ============================================================================
# BANNED WORDS — unboostable in TRELLIS token space
# ============================================================================
BANNED = {
    # Abstract / aesthetic
    "cute", "cuddly", "adorable", "cozy", "comfortable", "beautiful",
    "elegant", "realistic", "detailed", "intricate", "classic", "overall",
    "nice", "lovely", "pretty", "awesome", "interesting",
    # Meta / rendering
    "object", "thing", "model", "render", "image", "video", "design",
    "style", "appearance", "look", "view", "scene", "background",
    "lighting", "camera", "angle", "rendering",
    # Vague size
    "large", "small", "big", "tiny", "huge", "little",
    # Actions / verbs that sneak through as nouns
    "sitting", "standing", "holding", "wearing", "featuring", "showing",
    "displaying", "emitting",
    # Filler
    "various", "several", "multiple", "some", "many", "few",
    # Common stop words that POS tagger misses
    "also", "just", "very", "quite", "rather", "much",
}

# POS tags to KEEP — nouns and adjectives only
KEEP_POS = {
    'NN', 'NNS', 'NNP', 'NNPS',   # nouns
    'JJ', 'JJR', 'JJS',            # adjectives
}

# ============================================================================
# CORE FILTER
# ============================================================================

def filter_to_boostable_tokens(raw_text: str, max_tokens: int = 18) -> str:
    """
    Takes raw VLM natural language description and returns a clean
    comma-separated token string suitable for TRELLIS boosting.

    Args:
        raw_text: Raw VLM output (natural language)
        max_tokens: Maximum number of tokens to return (default 18)

    Returns:
        Comma-separated string of clean boostable tokens
    """
    if not raw_text or not raw_text.strip():
        return ""

    # Clean the text
    text = raw_text.strip().lower()

    # Remove punctuation except commas and hyphens (hyphens kept for compound colors)
    text = re.sub(r'[^\w\s,\-]', ' ', text)

    # Tokenize
    try:
        tokens = nltk.word_tokenize(text)
    except Exception:
        tokens = text.split()

    # POS tag
    try:
        tagged = nltk.pos_tag(tokens)
    except Exception:
        tagged = [(t, 'NN') for t in tokens]

    # Filter: keep only nouns and adjectives, remove banned, remove short tokens
    clean = []
    seen = set()
    for token, pos in tagged:
        token = token.strip().lower().strip('-')
        if (
            pos in KEEP_POS
            and len(token) > 2
            and token not in BANNED
            and token not in seen
            and not token.isdigit()
        ):
            clean.append(token)
            seen.add(token)

    # Limit to max_tokens
    clean = clean[:max_tokens]

    return ", ".join(clean)


def filter_prompt_file(prompt_path: str, max_tokens: int = 18) -> str:
    """
    Read a prompt.txt file, filter its contents, and overwrite with clean tokens.

    Args:
        prompt_path: Path to prompt.txt
        max_tokens: Maximum tokens to keep

    Returns:
        The filtered prompt string
    """
    with open(prompt_path, 'r') as f:
        raw = f.read().strip()

    filtered = filter_to_boostable_tokens(raw, max_tokens)

    with open(prompt_path, 'w') as f:
        f.write(filtered)

    return filtered


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    test_cases = [
        "A golden royal crown with five pointed spikes and red jewels embedded along the rim, smooth metallic finish",
        "Teddy bear, plush, soft, pink, matte, head, body, cute, cuddly, adorable, small, sitting",
        "Candle, cylindrical, wax, white, matte, dripping, flame, wick, wax drips, holder",
        "A snowman made of white spheres with a black top hat, orange carrot nose, red scarf, and stick arms",
        "Bronze menorah with seven curved arms, rounded candle cups, beaded stem, hexagonal base, weathered patina",
    ]

    print("=" * 60)
    print("PROMPT FILTER TEST")
    print("=" * 60)
    for raw in test_cases:
        filtered = filter_to_boostable_tokens(raw)
        print(f"\nRAW:      {raw[:80]}...")
        print(f"FILTERED: {filtered}")
    print("=" * 60)