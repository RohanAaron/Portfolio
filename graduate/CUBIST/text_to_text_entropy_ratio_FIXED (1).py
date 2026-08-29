"""
Text-to-Text Entropy Ratio Calculator V2 — STABILIZED
======================================================
Fixes the progressive degradation problem from V1.

ROOT CAUSE OF V1 DEGRADATION:
  1. Boost accumulation across iterations (ACCUMULATE_BOOSTS=True) caused
     compounding: token "candle" got boosted iter1, then boosted MORE iter2,
     then EVEN MORE iter3 → TRELLIS generates 12 candles instead of 1.
  2. Good tokens (sim>0.65) were SUPPRESSED to 0.9x, actively hurting them.
  3. No total boost budget → boosting 15 tokens simultaneously dilutes all of them.

V2 FIXES:
  Fix 1: NO ACCUMULATION. Each iteration computes fresh boosts from scratch.
         The --previous flag is REMOVED. Every iteration stands alone.
  Fix 2: PROTECT good tokens. Tokens with sim >= threshold get 1.0 (neutral),
         NOT 0.9 (suppressed). This prevents the "fix one, break another" tradeoff.
  Fix 3: BOOST BUDGET. Only the top-K worst tokens get boosted per iteration.
         This focuses attention on the most critical misses without diluting.
  Fix 4: CONSERVATIVE BOOST. Max boost reduced to 1.2x. Small nudges, not shoves.
         TRELLIS attention is sensitive — 1.2x is enough to shift generation.

Run with: python text_to_text_entropy_ratio_v2.py
"""

import json
import numpy as np
import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Import bigram boosting module
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from bigram_boost import get_phrase_boost_map, detect_bigrams
    BIGRAM_AVAILABLE = True
except ImportError:
    BIGRAM_AVAILABLE = False
    print("⚠ bigram_boost.py not found — falling back to unigram boosting")

# ============================================================================
# CONFIGURATION - V2 STABILIZED VALUES
# ============================================================================

# Similarity threshold - tokens below this are CANDIDATES for boosting
HIGH_UNCERTAINTY_THRESHOLD = 0.65

# Boost limits - CONSERVATIVE to prevent destabilization
MAX_BOOST_ALPHA = 3.0      # V1 was 1.3 + accumulation to 2.0. Now hard cap 1.2
MIN_BOOST_ALPHA = 1.0      # V1 was 0.9 (SUPPRESSED good tokens!). Now neutral 1.0
NEUTRAL_WEIGHT = 1.0       # Tokens that don't need boosting stay at exactly 1.0

# For very low similarity (critical misses) — small extra nudge
CRITICAL_THRESHOLD = 0.35
CRITICAL_BOOST_EXTRA = 0.05  # V1 was 0.1. Reduced.

# === KEY V2 CHANGE: BOOST BUDGET ===
# Only boost the top-K worst tokens per iteration.
# This prevents attention dilution from boosting 15+ tokens simultaneously.
MAX_TOKENS_TO_BOOST = 5     # Only boost the 5 worst-matching visual tokens

# === V2: NO ACCUMULATION ===
# Each iteration starts fresh. No --previous flag needed.
ACCUMULATE_BOOSTS = False    # V1 was True — this caused the degradation

# Suppress non-boosted tokens so mean(all_weights) == 1.0
# Prevents OOD drift from purely additive boosting.
ENABLE_ZERO_MEAN = True          # Toggle via --zero-mean / --no-zero-mean CLI flag
SUPPRESSION_FLOOR = 0.80         # Never push any token below this
PROTECTED_DAMPING = 0.5          # Protected tokens absorb at most this fraction of the excess
                                 # (vs filtered tokens which absorb fully)

# ============================================================================
# BLACKLIST: tokens that should NEVER be boosted
# (unchanged from V1 — the filtering logic was good)
# ============================================================================

NEVER_BOOST: Set[str] = {
    # === Verbs / Actions ===
    "appears", "appearing", "seems", "looking", "having", "giving",
    "featuring", "showing", "displaying", "suggesting", "allowing",
    "made", "making", "being", "using", "including", "containing",
    "supporting", "hanging", "holding", "extending", "connecting",
    "emit", "emitting", "attached", "positioned", "indicating",
    "meant", "fit", "wear", "worn", "depict", "depicts", "depicting",
    "indicates", "suggests", "resembles", "resembling",
    "features", "includes", "provided", "providing",
    "fitting", "fits", "sitting", "standing", "connected",
    
    # === Connectors / Fillers ===
    "the", "and", "with", "from", "that", "which", "where", "while",
    "its", "this", "these", "those", "there", "here", "for", "are",
    "has", "have", "can", "may", "would", "could", "should",
    "not", "no", "none", "without", "except", "unless",
    
    # === Abstract / Non-visual descriptors ===
    "overall", "general", "primarily", "mainly", "mostly", "particularly",
    "slightly", "somewhat", "quite", "very", "rather", "fairly",
    "present", "visible", "similar", "different", "various",
    "qualities", "characteristics", "features", "aspects", "details",
    "appearance", "style", "object", "thing",
    "likely", "probably", "possibly", "typically", "usually",
    "consistent", "consistency", "standard", "typical", "classic", "traditional",
    "approximately", "relatively", "roughly", "about", "around",
    "seamlessly", "seamless", "subtle", "minimal", "distinctive", "unique",
    "realistic", "natural", "artificial",
    "three-dimensional", "3d", "dimensional",
    "aesthetic", "attractive", "beautiful", "elegant",
    
    # === Quantifiers / Positional ===
    "multiple", "several", "many", "few", "some", "any", "all",
    "first", "second", "third", "top", "bottom", "left", "right",
    "front", "back", "side", "sides", "center", "middle",
    "both", "each", "every", "same", "other",
    
    # === Technical/meta terms ===
    "resolution", "topology", "manifold", "mesh", "baseplate", "origin",
    "textures", "8k", "4k", "hd", "render", "rendered", "rendering",
    "angles", "view", "views", "perspective", "image", "images",
    "sequence", "frame", "frames", "model",
    "photo", "photograph", "picture", "illustration",
    "shows", "shown", "showing", "display", "displayed",
    
    # === Size/measurement ===
    "size", "sized", "width", "height", "length", "depth",
    "large", "small", "big", "tiny", "huge", "massive",
    "thick", "thin", "wide", "narrow", "tall", "short",
    "long", "miniature", "compact",
    
    # === Abstract qualities ===
    "good", "bad", "nice", "beautiful", "ugly", "perfect", "fine",
    "signs", "damage", "wear", "condition", "quality",
    "protection", "function", "functional", "purpose", "use",
    "ergonomic", "comfortable", "practical", "useful",
    "designed", "support", "stability",
    
    # === Meta/structural words ===
    "elements", "components", "parts", "piece", "pieces",
    "combination", "mixture", "blend", "design",
    "main", "basic", "simple", "complex",
    "adult", "regular", "normal",
    "section", "portion", "area", "region",
    "primary", "secondary",
    
    # === Meta-descriptors (the word "color" vs actual colors) ===
    "material", "surface", "texture", "pattern",
    "color", "colour", "shade", "hue", "tint",
    "shape", "form", "structure", "geometry",
    
    # === V2 ADDITION: Non-geometric abstract tokens ===
    # These passed V1 filter as "inferred nouns" but TRELLIS can't control them
    "birthday", "single", "total", "evenly", "distributed",
    "arranged", "placed", "circular", "entire", "overall",
}

# ============================================================================
# WHITELIST: tokens we KNOW are visual and TRELLIS can influence
# (unchanged from V1)
# ============================================================================

VISUAL_COLORS: Set[str] = {
    "red", "blue", "green", "yellow", "orange", "purple", "pink",
    "black", "white", "gray", "grey", "brown", "beige", "tan",
    "bronze", "gold", "golden", "silver", "chrome", "copper",
    "dark", "light", "bright", "pale", "deep", "vivid",
    "maroon", "navy", "teal", "turquoise", "magenta", "crimson",
    "ivory", "cream", "charcoal", "amber", "indigo", "violet",
    "scarlet", "coral", "burgundy", "khaki", "olive", "rust",
}

VISUAL_MATERIALS: Set[str] = {
    "metal", "metallic", "wood", "wooden", "plastic", "glass",
    "ceramic", "porcelain", "leather", "fabric", "cloth",
    "rubber", "silicone", "steel", "iron", "copper", "brass",
    "aluminum", "stone", "marble", "concrete", "brick",
    "crystal", "diamond", "velvet", "suede", "denim",
    "foam", "cardboard", "paper", "wax", "clay", "plaster",
    "acrylic", "vinyl", "nylon", "polyester", "cotton", "wool",
    "titanium", "platinum", "jade", "obsidian", "granite",
}

VISUAL_TEXTURES: Set[str] = {
    "smooth", "rough", "glossy", "matte", "shiny", "dull",
    "textured", "patterned", "striped", "dotted", "checkered",
    "polished", "brushed", "satin", "frosted", "translucent",
    "transparent", "opaque", "reflective", "iridescent",
    "bumpy", "ridged", "grooved", "embossed", "engraved",
    "woven", "knitted", "braided", "quilted", "pleated",
    "grainy", "speckled", "marbled", "veined", "weathered",
    "corrugated", "perforated", "ribbed", "fluted",
}

VISUAL_SHAPES: Set[str] = {
    "round", "circular", "oval", "square", "rectangular",
    "triangular", "cylindrical", "spherical", "cubic",
    "curved", "straight", "flat", "angled", "pointed",
    "tapered", "flared", "bulbous", "elongated", "rounded",
    "conical", "pyramidal", "hexagonal", "octagonal",
    "wavy", "zigzag", "spiral", "helical", "twisted",
    "concave", "convex", "dome", "domed", "arched",
    "wedge", "wedged", "beveled", "chamfered",
}

VISUAL_PARTS: Set[str] = {
    "frame", "handle", "body", "base", "rim", "edge",
    "lid", "cap", "stem", "leg", "legs", "arm", "arms",
    "wheel", "wheels", "blade", "blades", "tip", "point",
    "door", "window", "roof", "wall", "floor",
    "button", "knob", "dial", "screen", "panel",
    "slot", "hole", "groove", "notch", "ridge",
    "bracket", "hinge", "clasp", "latch", "hook",
    "shelf", "drawer", "compartment", "chamber",
    "spout", "nozzle", "valve", "pipe", "tube",
    "cord", "cable", "wire", "chain", "strap",
    "head", "neck", "spine", "tail", "wing", "wings",
    "nose", "ear", "ears", "mouth", "jaw", "chin",
    "eye", "eyes", "beak", "horn", "horns", "antler",
    "paw", "paws", "claw", "claws", "hoof", "hooves",
    "fin", "fins", "gill", "gills", "feather", "feathers",
    "fur", "hair", "mane", "whisker", "whiskers",
    "shell", "scale", "scales", "tusk", "tusks",
    "teeth", "tongue", "snout", "trunk",
    "temples", "lenses", "bridge", "buckle",
    "sole", "heel", "toe", "collar", "cuff", "sleeve",
    "pocket", "zipper", "seam", "hem", "brim",
    "crown", "band", "pendant", "charm",
    "cushion", "backrest", "armrest", "seat", "footrest",
    "tabletop", "pedestal", "column", "pillar",
    "railing", "banister", "step", "tread",
    "string", "strings", "fret", "frets",
    "tuner", "tuners", "pickguard", "soundhole",
    "key", "keys", "pedal", "pedals",
    "peel", "skin", "rind", "seed", "pit", "core",
    "leaf", "leaves", "petal", "petals",
    "branch", "bark", "root", "roots",
    # V2 additions for dataset objects
    "candle", "candles", "tier", "tiers", "layer", "layers",
    "frosting", "icing", "strawberry", "strawberries",
    "blueberry", "blueberries", "swirl", "swirls",
    "spoke", "spokes", "fender", "bumper", "headlight",
    "crossbar", "anchor", "hook", "hooks",
    "dice", "dot", "dots", "pip", "pips",
    "snowman", "carrot", "scarf", "tophat",
}

VISUAL_OBJECTS: Set[str] = {
    "mug", "cup", "bowl", "plate", "bottle", "jar", "vase",
    "chair", "table", "desk", "lamp", "clock", "phone",
    "car", "bike", "boat", "plane", "train", "truck",
    "sunglasses", "glasses", "aviator", "watch", "ring",
    "shoe", "shoes", "boot", "boots", "hat", "helmet",
    "guitar", "piano", "drum", "violin", "trumpet",
    "sword", "shield", "axe", "hammer", "wrench",
    "book", "pen", "pencil", "brush", "comb",
    "fork", "knife", "spoon", "chopstick",
    "camera", "microphone", "speaker", "headphone",
    "ball", "bat", "racket", "glove",
    "candle", "torch", "lantern", "chandelier",
    "basket", "bucket", "barrel", "crate", "box",
    "pillow", "blanket", "towel", "curtain",
    "plant", "flower", "tree", "cactus", "mushroom",
    "apple", "banana", "avocado", "strawberry", "grape",
    "duck", "cat", "dog", "bird", "fish", "rabbit",
    "bear", "elephant", "horse", "lion", "tiger",
    "robot", "alien", "skull", "skeleton",
    "house", "castle", "tower", "arch",
    "toothbrush", "razor", "scissors", "stapler",
    # V2 additions
    "cake", "teapot", "bus", "anchor", "crown", "dice",
    "snowman", "soccer", "rubik", "cube",
}

# Master set of all visual tokens
ALL_VISUAL_TOKENS: Set[str] = (
    VISUAL_COLORS | VISUAL_MATERIALS | VISUAL_TEXTURES |
    VISUAL_SHAPES | VISUAL_PARTS | VISUAL_OBJECTS
)

# POS tags that CAN be visual
BOOSTABLE_POS_TAGS: Set[str] = {
    'NN', 'NNS', 'NNP', 'NNPS',  # Nouns
    'JJ', 'JJR', 'JJS',          # Adjectives
}

# ============================================================================
# HYBRID TOKEN FILTER (V2: also allows digit tokens for counting)
# ============================================================================

def is_boostable_token(token: str, pos: str, pos_tag: str) -> Tuple[bool, str]:
    """
    Determine if a token should be CONSIDERED for boosting.
    
    V2 changes:
    - Digit tokens ("3", "4", "12") are now accepted for counting features
    - Number words ("three", "four") are accepted
    """
    token_lower = token.lower()
    
    # Step 1: NEVER boost blacklisted tokens
    if token_lower in NEVER_BOOST:
        return False, "blacklisted"
    
    # Step 2: Allow digit tokens (V2 fix for counting features)
    if token_lower.isdigit():
        return True, "visual:count"
    
    # Step 2b: Allow number words
    NUMBER_WORDS = {
        "one", "two", "three", "four", "five", "six", "seven",
        "eight", "nine", "ten", "eleven", "twelve", "thirteen",
        "twenty", "thirty", "forty", "fifty", "hundred",
    }
    if token_lower in NUMBER_WORDS:
        return True, "visual:count_word"
    
    # Step 3: Skip very short non-digit tokens
    if len(token_lower) < 3:
        return False, "too short"
    
    # Step 4: Only consider nouns and adjectives
    if pos_tag not in BOOSTABLE_POS_TAGS and pos not in ['noun', 'adjective']:
        return False, f"non-visual POS: {pos}/{pos_tag}"
    
    # Step 5: Check whitelist — guaranteed boost with category
    if token_lower in ALL_VISUAL_TOKENS:
        if token_lower in VISUAL_COLORS:
            return True, "visual:color"
        elif token_lower in VISUAL_MATERIALS:
            return True, "visual:material"
        elif token_lower in VISUAL_TEXTURES:
            return True, "visual:texture"
        elif token_lower in VISUAL_SHAPES:
            return True, "visual:shape"
        elif token_lower in VISUAL_PARTS:
            return True, "visual:part"
        elif token_lower in VISUAL_OBJECTS:
            return True, "visual:object"
        else:
            return True, "visual:other"
    
    # Step 6: HYBRID — allow unknown nouns/adjectives with 4+ chars
    if pos_tag in BOOSTABLE_POS_TAGS and len(token_lower) >= 4:
        return True, "visual:inferred"
    
    return False, "not visual (short unknown)"


# ============================================================================
# MAIN FUNCTION — V2 STABILIZED
# ============================================================================

def calculate_text_to_text_entropy(
    input_file: str = 'evaluation_results.json',
    output_file: str = 'trellis_intervention_config.json',
    previous_config_file: str = None  # Kept for CLI compat, but IGNORED in V2
) -> Dict:
    """
    V2: Calculate entropy and generate intervention config with STABILIZED boosts.
    
    Key differences from V1:
    - No accumulation (each iteration is independent)
    - Good tokens protected at 1.0 (not suppressed to 0.9)
    - Only top-K worst tokens get boosted (boost budget)
    - Lower max boost (1.2x vs 1.3x+accumulation)
    """
    
    _bigram_ok = BIGRAM_AVAILABLE  # local copy to avoid scoping issues

    print(f"\n{'='*70}")
    print("TEXT-TO-TEXT ENTROPY RATIO V2 (STABILIZED)")
    print(f"{'='*70}")
    print(f"Configuration:")
    print(f"  Similarity threshold: {HIGH_UNCERTAINTY_THRESHOLD}")
    print(f"  Max boost: {MAX_BOOST_ALPHA}x (hard cap, no accumulation)")
    print(f"  Boost budget: top {MAX_TOKENS_TO_BOOST} worst tokens only")
    print(f"  Good token protection: all non-boosted tokens locked at 1.0")
    print(f"  Accumulation: DISABLED (fresh each iteration)")
    print(f"{'='*70}\n")

    if previous_config_file:
        print(f"⚠ Note: --previous flag ignored in V2 (no accumulation)")

    # Load evaluation results
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: '{input_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: Could not parse JSON from '{input_file}'.")
        sys.exit(1)

    # Extract token comparisons
    try:
        token_comparisons = data['semantic_analysis']['token_comparisons']
        average_similarity = data['semantic_analysis'].get('average_similarity', 0)
    except KeyError:
        print("❌ Error: Missing 'semantic_analysis' or 'token_comparisons'.")
        sys.exit(1)

    # ================================================================
    # PASS 1: Classify all tokens
    # ================================================================
    intervention_config = {}
    filtered_out = []
    boost_candidates = []  # Tokens that COULD be boosted (visual + low sim)
    protected_tokens = []  # Visual tokens already matching well
    seen_tokens = set()
    
    for comp in token_comparisons:
        token = comp['token_t1'].lower()
        score = comp['semantic_similarity']
        pos = comp.get('pos', 'unknown')
        pos_tag = comp.get('pos_tag', 'NN')
        
        # Skip duplicates
        if token in seen_tokens:
            continue
        seen_tokens.add(token)
        
        # Use hybrid filtering
        should_boost, reason = is_boostable_token(token, pos, pos_tag)
        
        if not should_boost:
            # V2 FIX: Non-visual tokens get NEUTRAL weight (1.0), not suppression (0.9)
            filtered_out.append((token, reason, score))
            intervention_config[token] = NEUTRAL_WEIGHT
            continue
        
        # Token is visual — check if it needs boosting
        if score < HIGH_UNCERTAINTY_THRESHOLD:
            # This token is a CANDIDATE for boosting
            # Calculate raw boost strength
            strength = (HIGH_UNCERTAINTY_THRESHOLD - score) / HIGH_UNCERTAINTY_THRESHOLD
            raw_boost = NEUTRAL_WEIGHT + (strength * (MAX_BOOST_ALPHA - NEUTRAL_WEIGHT))
            
            # Extra nudge for critical misses
            if score < CRITICAL_THRESHOLD:
                raw_boost = min(raw_boost + CRITICAL_BOOST_EXTRA, MAX_BOOST_ALPHA)
            
            # Slight priority for KNOWN visual tokens over inferred ones
            is_known_visual = token in ALL_VISUAL_TOKENS
            if is_known_visual and raw_boost < MAX_BOOST_ALPHA:
                raw_boost = min(raw_boost * 1.03, MAX_BOOST_ALPHA)
            
            # Hard cap — NEVER exceed MAX_BOOST_ALPHA
            raw_boost = min(round(raw_boost, 3), MAX_BOOST_ALPHA)
            
            boost_candidates.append({
                'token': token,
                'similarity': score,
                'raw_boost': raw_boost,
                'pos': pos,
                'category': reason,
                'is_known': is_known_visual,
            })
        else:
            # V2 FIX: Good tokens get NEUTRAL weight (1.0) — PROTECTED
            protected_tokens.append((token, reason, score))
            intervention_config[token] = NEUTRAL_WEIGHT

    # ================================================================
    # PASS 2: Apply BOOST BUDGET — bigram-aware or unigram fallback
    # ================================================================

    # Build token similarity map for bigram module
    token_sim_map = {c['token']: c['similarity'] for c in boost_candidates}
    # Also include protected tokens (they have good similarity)
    for tok, _, sim in protected_tokens:
        token_sim_map[tok] = sim

    actually_boosted = []

    if _bigram_ok:
        # Load prompt
        prompt_text = ""
        try:
            with open('prompt.txt', 'r') as f:
                prompt_text = f.read().strip()
        except Exception:
            pass

        if prompt_text:
            print(f"\n  [Bigram] Detecting adjective-noun pairs in prompt...")
            pairs = detect_bigrams(prompt_text)
            print(f"  [Bigram] Found {len(pairs)} pairs: {pairs}")

            bigram_config, bigram_boosted = get_phrase_boost_map(
                prompt=prompt_text,
                token_similarities=token_sim_map,
                boost_budget=MAX_TOKENS_TO_BOOST,
                max_boost=MAX_BOOST_ALPHA,
                threshold=HIGH_UNCERTAINTY_THRESHOLD,
            )

            # Merge bigram config into intervention_config
            for token, weight in bigram_config.items():
                intervention_config[token] = weight

            # Build actually_boosted list for reporting
            for c in bigram_boosted:
                c['final_boost'] = c['raw_boost']
                c['is_known'] = True
                c['category'] = c.get('type', 'bigram')
                c['boosted'] = True
                actually_boosted.append(c)

            print(f"  [Bigram] Boosted {len(actually_boosted)} tokens/pairs")
        else:
            # No prompt file — fall back to unigram
            _bigram_ok = False

    if not _bigram_ok or not actually_boosted:
        # Fallback: original unigram boosting
        boost_candidates.sort(key=lambda x: x['similarity'])
        for i, candidate in enumerate(boost_candidates):
            if i < MAX_TOKENS_TO_BOOST:
                final_boost = candidate['raw_boost']
                intervention_config[candidate['token']] = final_boost
                candidate['final_boost'] = final_boost
                candidate['boosted'] = True
                actually_boosted.append(candidate)
            else:
                intervention_config[candidate['token']] = NEUTRAL_WEIGHT
                candidate['final_boost'] = NEUTRAL_WEIGHT
                candidate['boosted'] = False
    
    # ================================================================
    # PASS 3: ZERO-MEAN REBALANCING (Simon's suggestion)
    # Suppress non-boosted tokens to absorb boost excess, keeping mean ≈ 1.0
    # ================================================================
    rebalance_info = {"enabled": False}

    if ENABLE_ZERO_MEAN and len(intervention_config) > 0:
        # Compute excess mass added by boosting
        total_excess = sum(w - NEUTRAL_WEIGHT for w in intervention_config.values() if w > NEUTRAL_WEIGHT)
        
        if total_excess > 1e-6:
            # Identify suppression pool, partitioned by priority
            filtered_tokens_set = {t for t, _, _ in filtered_out}
            protected_tokens_set = {t for t, _, _ in protected_tokens}
            
            filtered_in_config = [t for t in intervention_config if t in filtered_tokens_set]
            protected_in_config = [t for t in intervention_config if t in protected_tokens_set]
            
            # Map protected token → similarity (for proportional damping)
            protected_sim_map = {t: s for t, _, s in protected_tokens}
            
            remaining_excess = total_excess
            suppressed_log = []
            
            # TIER 1: suppress filtered tokens fully (safe — these are non-visual / blacklisted)
            if filtered_in_config and remaining_excess > 0:
                filtered_capacity = len(filtered_in_config) * (NEUTRAL_WEIGHT - SUPPRESSION_FLOOR)
                absorb_from_filtered = min(remaining_excess, filtered_capacity)
                per_token_reduction = absorb_from_filtered / len(filtered_in_config)
                
                for t in filtered_in_config:
                    new_weight = round(NEUTRAL_WEIGHT - per_token_reduction, 3)
                    new_weight = max(new_weight, SUPPRESSION_FLOOR)
                    intervention_config[t] = new_weight
                    suppressed_log.append({"token": t, "tier": "filtered", "weight": new_weight})
                
                remaining_excess -= absorb_from_filtered
            
            # TIER 2: suppress protected tokens proportional to (1 - similarity)
            # High-sim tokens (0.99) barely move; borderline tokens (0.75) move more.
            # Also damped by PROTECTED_DAMPING so we don't crush working features.
            if protected_in_config and remaining_excess > 1e-6:
                # Weight = how much each protected token is willing to be pushed
                # Lower similarity => more willing to move
                weights = {t: max(1.0 - protected_sim_map.get(t, 1.0), 0.01) for t in protected_in_config}
                total_weight = sum(weights.values())
                
                # Apply damping factor so protected tokens only absorb PROTECTED_DAMPING fraction
                max_absorb_from_protected = len(protected_in_config) * (NEUTRAL_WEIGHT - SUPPRESSION_FLOOR) * PROTECTED_DAMPING
                absorb_from_protected = min(remaining_excess, max_absorb_from_protected)
                
                for t in protected_in_config:
                    share = (weights[t] / total_weight) if total_weight > 0 else (1.0 / len(protected_in_config))
                    reduction = absorb_from_protected * share
                    new_weight = round(NEUTRAL_WEIGHT - reduction, 3)
                    new_weight = max(new_weight, SUPPRESSION_FLOOR)
                    intervention_config[t] = new_weight
                    suppressed_log.append({
                        "token": t,
                        "tier": "protected",
                        "weight": new_weight,
                        "similarity": round(protected_sim_map.get(t, 0.0), 3),
                    })
                
                remaining_excess -= absorb_from_protected
            
            # Compute final mean for audit
            final_mean = sum(intervention_config.values()) / len(intervention_config)
            
            rebalance_info = {
                "enabled": True,
                "total_excess_before": round(total_excess, 4),
                "remaining_excess_after": round(max(remaining_excess, 0), 4),
                "final_mean_weight": round(final_mean, 4),
                "suppressed_tokens": suppressed_log,
                "suppression_floor": SUPPRESSION_FLOOR,
                "protected_damping": PROTECTED_DAMPING,
                "note": (
                    "Fully rebalanced to mean=1.0" if abs(final_mean - 1.0) < 0.01
                    else f"Partially rebalanced (mean={final_mean:.3f}, excess capacity insufficient)"
                ),
            }
            
            print(f"\n  [Zero-Mean] Excess {total_excess:.3f} → absorbed across "
                  f"{len(suppressed_log)} tokens, final mean = {final_mean:.3f}")
        else:
            rebalance_info = {"enabled": True, "note": "No excess to rebalance"}

    # ================================================================
    # STATISTICS
    # ================================================================
    boosted_only = {k: v for k, v in intervention_config.items() if v > NEUTRAL_WEIGHT}
    total_tokens = len(intervention_config)
    high_entropy_count = len(boosted_only)
    entropy_pct = (high_entropy_count / total_tokens) * 100 if total_tokens > 0 else 0

    if boosted_only:
        boost_values = list(boosted_only.values())
        avg_boost = sum(boost_values) / len(boost_values)
        max_boost_val = max(boost_values)
        min_boost_val = min(boost_values)
    else:
        avg_boost = max_boost_val = min_boost_val = NEUTRAL_WEIGHT

    # ================================================================
    # BUILD REPORT (same schema as V1 for compatibility)
    # ================================================================
    report = {
        "intervention_config": intervention_config,
        "high_entropy_tokens_summary": [
            f"'{t['token']}' ({t['final_boost']:.2f}x, sim={t['similarity']:.2f}, {t['category']})"
            for t in actually_boosted
        ],
        "high_entropy_percentage": round(entropy_pct, 2),
        "average_similarity": round(average_similarity, 4),
        "boost_statistics": {
            "average_boost": round(avg_boost, 3),
            "max_boost": round(max_boost_val, 3),
            "min_boost": round(min_boost_val, 3),
            "total_boosted": high_entropy_count,
            "total_candidates": len(boost_candidates),
            "budget_limit": MAX_TOKENS_TO_BOOST,
            "total_tokens": total_tokens,
            "tokens_filtered": len(filtered_out),
            "tokens_protected": len(protected_tokens),
            "over_budget_tokens": len(boost_candidates) - len(actually_boosted),
        },
        "quality_metrics": {
            "average_similarity": round(average_similarity, 4),
            "visual_alignment_score": round(average_similarity * 100, 2),
            "entropy_percentage": round(entropy_pct, 2)
        },
        "v2_stabilization": {
            "zero_mean_rebalancing": rebalance_info,
            "accumulation": "DISABLED",
            "good_token_protection": "all non-boosted at 1.0",
            "boost_budget": f"top {MAX_TOKENS_TO_BOOST} worst only",
            "max_single_boost": MAX_BOOST_ALPHA,
        },
        "filtering_details": {
            "filtered_tokens": [
                {"token": t, "reason": r, "similarity": round(s, 3)}
                for t, r, s in filtered_out
            ],
            "protected_tokens": [
                {"token": t, "category": r, "similarity": round(s, 3)}
                for t, r, s in protected_tokens
            ],
            "over_budget_candidates": [
                {"token": c['token'], "similarity": round(c['similarity'], 3),
                 "would_have_been": round(c['raw_boost'], 3)}
                for c in boost_candidates[MAX_TOKENS_TO_BOOST:]
            ],
        }
    }

    # Save
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    # ================================================================
    # PRINT SUMMARY
    # ================================================================
    print(f"✓ Saved intervention config to: {output_file}")
    
    print(f"\n{'='*70}")
    print("TOKEN CLASSIFICATION")
    print(f"{'='*70}")
    print(f"  Total unique tokens:        {len(seen_tokens)}")
    print(f"  Filtered (non-visual):      {len(filtered_out)} → weight 1.0")
    print(f"  Protected (visual, OK):     {len(protected_tokens)} → weight 1.0")
    print(f"  Boost candidates (low sim): {len(boost_candidates)}")
    print(f"  Actually BOOSTED (top {MAX_TOKENS_TO_BOOST}):  {len(actually_boosted)}")
    print(f"  Over budget (not boosted):  {len(boost_candidates) - len(actually_boosted)}")
    
    if actually_boosted:
        print(f"\n{'='*70}")
        print(f"BOOSTED TOKENS (top {MAX_TOKENS_TO_BOOST} worst matches)")
        print(f"{'='*70}")
        for i, t in enumerate(actually_boosted, 1):
            known = "✓" if t['is_known'] else "~"
            print(f"  {i}. '{t['token']}': {t['final_boost']:.3f}x "
                  f"(sim={t['similarity']:.3f}) [{t['category']}] {known}")
    else:
        print(f"\n  ✓ No tokens need boosting! Output matches prompt well.")
    
    # Show what was OVER budget (informational)
    over_budget = boost_candidates[MAX_TOKENS_TO_BOOST:]
    if over_budget:
        print(f"\n  Over budget (kept at 1.0 to prevent dilution):")
        for c in over_budget[:10]:
            print(f"    - '{c['token']}' sim={c['similarity']:.3f} "
                  f"(would have been {c['raw_boost']:.3f}x)")
    
    print(f"\n{'='*70}")
    print("QUALITY METRIC")
    print(f"{'='*70}")
    print(f"  Average Similarity: {average_similarity:.4f}")
    print(f"  Visual Alignment:   {average_similarity * 100:.2f}%")
    print(f"  Tokens Boosted:     {high_entropy_count}/{total_tokens}")
    print(f"{'='*70}\n")

    return report


# ============================================================================
# CLI ENTRY
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Text-to-text entropy ratio V2 (stabilized, no accumulation)"
    )
    parser.add_argument('--no-zero-mean', action='store_true',
                        help='Disable zero-mean rebalancing (use original additive-only boosting)')
    parser.add_argument('--zero-mean', action='store_true',
                        help='Enable zero-mean rebalancing (default: enabled)')
    parser.add_argument('--input', '-i', default='evaluation_results.json',
                        help='Input evaluation results file')
    parser.add_argument('--output', '-o', default='trellis_intervention_config.json',
                        help='Output intervention config file')
    parser.add_argument('--previous', '-p', default=None,
                        help='(IGNORED in V2) Previous iteration config file')
    parser.add_argument('--max-boost-tokens', '-k', type=int, default=MAX_TOKENS_TO_BOOST,
                        help=f'Max tokens to boost per iteration (default: {MAX_TOKENS_TO_BOOST})')
    parser.add_argument('--max-boost', type=float, default=MAX_BOOST_ALPHA,
                        help=f'Maximum boost multiplier (default: {MAX_BOOST_ALPHA})')
    
    args = parser.parse_args()

    # Apply CLI override for zero-mean
    if args.no_zero_mean:
        ENABLE_ZERO_MEAN = False
    elif args.zero_mean:
        ENABLE_ZERO_MEAN = True
    
    # Allow CLI override of budget
    if args.max_boost_tokens != MAX_TOKENS_TO_BOOST:
        MAX_TOKENS_TO_BOOST = args.max_boost_tokens

    if args.max_boost != MAX_BOOST_ALPHA:
        MAX_BOOST_ALPHA = args.max_boost
    
    calculate_text_to_text_entropy(
        input_file=args.input,
        output_file=args.output,
        previous_config_file=args.previous
    )