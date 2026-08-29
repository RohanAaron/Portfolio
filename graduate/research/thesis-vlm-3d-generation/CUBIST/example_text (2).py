import os
os.environ['ATTN_BACKEND'] = 'xformers'
os.environ['SPCONV_ALGO'] = 'native'

import imageio
from trellis.pipelines import TrellisTextTo3DPipeline
from trellis.utils import render_utils, postprocessing_utils
import torch
from typing import Dict, List
import sys
import json
from pathlib import Path

# Load pipeline
pipeline = TrellisTextTo3DPipeline.from_pretrained(
    "/projects/tealab/rohan19/Trellis/TRELLIS/checkpoints/TRELLIS-text-large"
)
pipeline.cuda()

# ====================================================================
# DYNAMIC INPUT LOADING
# ====================================================================

# 1. Load Prompt from prompt.txt
PROMPT_FILE = 'prompt.txt'
try:
    with open(PROMPT_FILE, 'r') as f:
        PROMPT_TEXT = f.read().strip()
    if not PROMPT_TEXT:
        print(f"FATAL ERROR: {PROMPT_FILE} is empty.")
        sys.exit(1)
except FileNotFoundError:
    print(f"FATAL ERROR: {PROMPT_FILE} not found. Please create it.")
    sys.exit(1)

print(f"Prompt: {PROMPT_TEXT}")

# 2. Load Intervention Config
CONFIG_FILE = 'trellis_intervention_config.json'
intervention_config = {}

if Path(CONFIG_FILE).exists():
    print(f"\nLoading intervention config from {CONFIG_FILE}...")
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
            intervention_config = config_data.get('intervention_config', {})

        boosted = {k: v for k, v in intervention_config.items() if v > 1.0}
        print(f"✓ Loaded {len(intervention_config)} token configs")
        print(f"  {len(boosted)} tokens are boosted (>1.0x)")

        if boosted:
            avg_boost = sum(boosted.values()) / len(boosted)
            max_boost = max(boosted.values())
            print(f"  Average boost: {avg_boost:.2f}x")
            print(f"  Maximum boost: {max_boost:.2f}x")

            top_5 = sorted(boosted.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"  Top 5 boosted:")
            for token, boost in top_5:
                print(f"    '{token}': {boost:.2f}x")
    except Exception as e:
        print(f"Warning: Could not load intervention config: {e}")
        print("Proceeding with empty config (no intervention)")
        intervention_config = {}
else:
    print(f"\n{CONFIG_FILE} not found - running WITHOUT intervention (baseline)")
    print("This is normal for the first iteration.")
    intervention_config = {}

# ====================================================================
# FLAGS FROM ENVIRONMENT
# ====================================================================
iteration_number = int(os.environ.get('TRELLIS_ITERATION', 1))
print(f"  Seed: {iteration_number}")

use_phased    = os.environ.get('TRELLIS_PHASED',    '1') == '1'
use_uniform   = os.environ.get('TRELLIS_UNIFORM',   '0') == '1'
use_zero_mean = os.environ.get('TRELLIS_ZERO_MEAN', '1') == '1'

# KEY FIX: zero-mean only when actually boosting
has_boosted_tokens = any(v > 1.0 for v in intervention_config.values())
if use_zero_mean and not has_boosted_tokens:
    use_zero_mean = False
    print("  Zero-Mean: OFF (disabled at baseline — no boosted tokens)")
else:
    print(f"  Zero-Mean: {'ON' if use_zero_mean else 'OFF'}")

print(f"\nRunning Trellis pipeline...")
print(f"  Prompt: '{PROMPT_TEXT}'")
print(f"  Intervention: {'YES (' + str(len([v for v in intervention_config.values() if v > 1.0])) + ' tokens boosted)' if intervention_config else 'NO (baseline)'}")
print(f"  Zero-Mean: {'ON' if use_zero_mean else 'OFF'}")  # ← visible in logs

# ====================================================================
# RUN TRELLIS
# ====================================================================
if has_boosted_tokens and use_phased:
    mode_str = "UNIFORM" if use_uniform else "PHASED (timestep-aware)"
    print(f"  Mode: {mode_str}")
    outputs = pipeline.run_phased(
        prompt=PROMPT_TEXT,
        intervention_config=intervention_config,
        seed=iteration_number,
        uniform_mode=use_uniform,
        zero_mean=use_zero_mean,
    )
else:
    print(f"  Mode: STANDARD")
    outputs = pipeline.run(
        prompt=PROMPT_TEXT,
        seed=iteration_number,
    )

print("✓ Pipeline execution complete")

# ====================================================================
# SAVE OUTPUTS
# ====================================================================
print(f"\nSaving outputs...")

out_dir = Path(".outputs")
out_dir.mkdir(exist_ok=True)

video = render_utils.render_video(outputs['gaussian'][0])['color']
video_path = out_dir / "trellis_latest.mp4"
imageio.mimsave(str(video_path), video, fps=30)
print(f"✓ Video saved: {video_path}")

glb = postprocessing_utils.to_glb(
    outputs['gaussian'][0],
    outputs['mesh'][0],
    simplify=0.95,
    texture_size=1024,
)
glb_path = out_dir / "trellis_latest.glb"
glb.export(str(glb_path))
print(f"✓ GLB saved: {glb_path}")

metadata = {
    "prompt": PROMPT_TEXT,
    "intervention_config": intervention_config,
    "num_boosted_tokens": len([v for v in intervention_config.values() if v > 1.0]),
    "had_intervention": has_boosted_tokens,
    "seed": iteration_number,
    "phased": use_phased,
    "uniform_mode": use_uniform,
    "zero_mean": use_zero_mean,
}

metadata_path = out_dir / "metadata.json"
with open(metadata_path, "w") as f:
    json.dump(metadata, f, indent=2)
print(f"✓ Metadata saved: {metadata_path}")

print(f"\n{'='*70}")
print("GENERATION COMPLETE")
print(f"{'='*70}")
print(f"Outputs in: {out_dir}/")
print(f"  - {video_path.name}")
print(f"  - {glb_path.name}")
print(f"  - {metadata_path.name}")
print(f"{'='*70}\n")
import os
os._exit(0)
