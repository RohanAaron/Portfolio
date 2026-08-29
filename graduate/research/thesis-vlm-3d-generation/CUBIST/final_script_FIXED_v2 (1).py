"""
TRELLIS Iterative Feedback Loop
================================
Controls:
  --zero-mean / --no-zero-mean  : toggle zero-mean rebalancing (default: enabled)
  --uniform                     : use uniform boosting (no phase categorization)
                                  for the TATI-vs-uniform ablation
"""

import subprocess
import random
import sys
import os
from pathlib import Path
import json
import shutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class ExperimentConfig:
    """Configuration for the feedback loop experiment."""
    max_iterations: int = 8
    target_similarity: float = 1.01
    target_entropy: float = 0.0
    min_improvement: float = 0.01
    patience: int = 8
    revert_on_decline: bool = False
    max_boost_tokens: int = 5

    # Script paths
    trellis_script: str = "/projects/tealab/rohan19/Trellis/TRELLIS/example_text.py"
    vlm_script: str = "/projects/tealab/rohan19/Trellis/TRELLIS/Semantic_score_VLM.py"
    entropy_script: str = "/projects/tealab/rohan19/Trellis/TRELLIS/text_to_text_entropy_ratio.py"

    # Zero-mean rebalancing toggle (Simon's suggestion)
    zero_mean: bool = True

    # Uniform mode for TATI-vs-uniform ablation
    uniform_mode: bool = False


@dataclass
class IterationResult:
    iteration: int
    entropy_pct: float
    avg_similarity: float
    video_path: str
    mesh_path: str
    config_path: str
    eval_path: str
    is_best: bool = False


# ============================================================================
# MAIN FEEDBACK LOOP
# ============================================================================

def run_trellis_feedback_loop(config: ExperimentConfig = None):
    if config is None:
        config = ExperimentConfig()

    prompt_name = "experiment"
    try:
        with open('prompt.txt', 'r') as f:
            prompt = f.read().strip()
            words = prompt.split()[:3]
            prompt_name = "_".join(w.lower()[:10] for w in words if w.isalnum())
            if not prompt_name:
                prompt_name = "experiment"
    except:
        pass

    _custom = os.environ.get("EXPERIMENT_NAME", "")
    if _custom:
        prompt_name = _custom

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    experiment_dir = Path(f"./experiments/{prompt_name}") if _custom else Path(f"./experiments/{prompt_name}_{timestamp}")
    experiment_dir.mkdir(parents=True, exist_ok=True)

    config_path = experiment_dir / "experiment_config.json"
    with open(config_path, 'w') as f:
        json.dump(asdict(config), f, indent=2)

    print("="*70)
    print("TRELLIS ITERATIVE FEEDBACK LOOP (IMPROVED)")
    print("="*70)
    print(f"Experiment: {experiment_dir}")
    print(f"Max Iterations: {config.max_iterations} (1 baseline + 7 refined)")
    print(f"Early Stopping: DISABLED — all iterations will run")
    print(f"Zero-Mean Rebalancing: {'ENABLED' if config.zero_mean else 'DISABLED'}")
    print(f"Intervention Mode: {'UNIFORM (ablation)' if config.uniform_mode else 'PHASED (TATI)'}")
    print("="*70)

    results: List[IterationResult] = []
    best_result: Optional[IterationResult] = None
    best_similarity: float = 0.0
    no_improvement_count: int = 0

    video_path = None
    mesh_path = None
    eval_path = None
    config_file_path = None
    entropy_pct = 0
    avg_similarity = 0

    for i in range(1, config.max_iterations + 1):
        print(f"\n{'='*70}")
        print(f" ITERATION {i}/{config.max_iterations} {'(BASELINE)' if i == 1 else f'(REFINED {i-1}/7)'}")
        print(f"{'='*70}")

        iter_dir = experiment_dir / f"iteration_{i:02d}"
        iter_dir.mkdir(exist_ok=True)

        # ===== PHASE 1: TRELLIS GENERATION =====
        print(f"\n[STEP 1] TRELLIS Generation...")

        if i == 1:
            if Path("trellis_intervention_config.json").exists():
                os.remove("trellis_intervention_config.json")
            print("  (Baseline - removed stale config → TRUE clean baseline)")
        elif config.revert_on_decline and best_result is not None and not results[-1].is_best:
            shutil.copy(best_result.config_path, "trellis_intervention_config.json")
            print(f"  (Iteration {results[-1].iteration} declined — reverting to "
                  f"BEST config from iteration {best_result.iteration})")
        elif results and Path(results[-1].config_path).exists():
            shutil.copy(results[-1].config_path, "trellis_intervention_config.json")
            print(f"  (Using config from iteration {results[-1].iteration})")
        else:
            print(f"  (Using config from iteration {i-1})")

        try:
            env_step1 = os.environ.copy()
            iter_seed = random.randint(1000, 9999)
            if i == 1:
                print(f"  Random seed (baseline): {iter_seed}")
            else:
                print(f"  Random seed (iter {i}): {iter_seed}")
            env_step1["TRELLIS_ITERATION"] = str(iter_seed)
            env_step1["TRELLIS_UNIFORM"] = "1" if config.uniform_mode else "0"
            env_step1["TRELLIS_ZERO_MEAN"] = "1" if config.zero_mean else "0"

            result = subprocess.run(
                ['python', config.trellis_script],
                env=env_step1
            )

            outputs_ok = (
                Path(".outputs/trellis_latest.mp4").exists() and
                Path(".outputs/trellis_latest.glb").exists()
            )
            if not outputs_ok:
                raise RuntimeError("TRELLIS outputs missing after generation")

            print(f"  ✓ Generation complete (seed={iter_seed})")

            video_path = iter_dir / f"output_iter_{i:02d}.mp4"
            mesh_path = iter_dir / f"mesh_iter_{i:02d}.glb"

            if Path(".outputs/trellis_latest.mp4").exists():
                shutil.copy(".outputs/trellis_latest.mp4", video_path)
                print(f"  Saved: {video_path.name}")

            if Path(".outputs/trellis_latest.glb").exists():
                shutil.copy(".outputs/trellis_latest.glb", mesh_path)
                print(f"  Saved: {mesh_path.name}")

        except Exception as e:
            print(f"  ❌ TRELLIS failed: {e}")
            break
        print("  ✓ TRELLIS complete")

        # ===== PHASE 2: VLM EVALUATION =====
        print(f"\n[STEP 2] VLM Evaluation...")

        env_step2 = os.environ.copy()
        env_step2['TRELLIS_VIDEO_PATH'] = str(video_path.resolve())

        try:
            result = subprocess.run(
                ['python', config.vlm_script],
                capture_output=False,
                text=True,
                timeout=300,
                env=env_step2
            )
            print("  ✓ VLM complete")

            eval_path = iter_dir / "evaluation_results.json"
            if Path("evaluation_results.json").exists():
                shutil.copy("evaluation_results.json", eval_path)

                try:
                    with open("evaluation_results.json") as f:
                        eval_data = json.load(f)
                        desc = eval_data.get("vlm_description", "")[:60]
                        print(f"  VLM saw: {desc}...")
                except:
                    pass

        except subprocess.CalledProcessError as e:
            err_text = e.stderr if e.stderr else 'Unknown error'
            print(f"  ❌ VLM failed:")
            print(err_text[-1500:] if len(err_text) > 1500 else err_text)

            eval_path = iter_dir / "evaluation_results.json"

            fallback_eval = {
                "vlm_description": "VLM evaluation failed",
                "similarity_scores": [],
                "average_similarity": 0.0
            }

            with open(eval_path, "w") as f:
                json.dump(fallback_eval, f, indent=2)

            print("  ⚠️ Using fallback evaluation (similarity = 0.0)")
            avg_similarity = 0.0

        # ===== PHASE 3: ENTROPY CALCULATION =====
        print(f"\n[STEP 3] Entropy Calculation...")

        prev_config_arg = []
        if i > 1 and results and Path(results[-1].config_path).exists():
            prev_config_arg = ['--previous', results[-1].config_path]

        zero_mean_arg = ['--zero-mean'] if config.zero_mean else ['--no-zero-mean']
        max_boost_arg = ['--max-boost-tokens', str(config.max_boost_tokens)]

        try:
            result = subprocess.run(
                ['python', config.entropy_script] + prev_config_arg + zero_mean_arg + max_boost_arg,
                capture_output=False,
                text=True,
                check=True
            )
            print("  ✓ Entropy calculated")

            config_file_path = iter_dir / "trellis_intervention_config.json"
            if Path("trellis_intervention_config.json").exists():
                shutil.copy("trellis_intervention_config.json", config_file_path)

            entropy_pct = None
            avg_similarity = None

            try:
                with open("trellis_intervention_config.json") as f:
                    config_data = json.load(f)
                    entropy_pct = config_data.get("high_entropy_percentage", 0)
                    quality_metrics = config_data.get("quality_metrics", {})
                    avg_similarity = quality_metrics.get("average_similarity",
                                     config_data.get("average_similarity", 0))
            except:
                for line in result.stdout.splitlines():
                    if "High Entropy Percentage:" in line:
                        entropy_pct = float(line.split(":")[1].strip().replace('%', ''))
                    if "Average Similarity Score:" in line:
                        avg_similarity = float(line.split(":")[1].strip())

            if entropy_pct is None:
                entropy_pct = 0
            if avg_similarity is None:
                avg_similarity = 0

        except subprocess.CalledProcessError as e:
            err_text = e.stderr if e.stderr else 'Unknown error'
            print(f"  ❌ Entropy calculation failed:")
            print(err_text[-1500:] if len(err_text) > 1500 else err_text)

            entropy_pct = 100.0
            avg_similarity = avg_similarity if avg_similarity is not None else 0.0

            print("  ⚠️ Using fallback entropy = 100%")

        iter_result = IterationResult(
            iteration=i,
            entropy_pct=entropy_pct,
            avg_similarity=avg_similarity,
            video_path=str(video_path),
            mesh_path=str(mesh_path),
            config_path=str(config_file_path),
            eval_path=str(eval_path)
        )
        results.append(iter_result)

        is_new_best = avg_similarity > best_similarity
        if is_new_best:
            best_similarity = avg_similarity
            best_result = iter_result
            iter_result.is_best = True
            no_improvement_count = 0
            print(f"\n  ⭐ NEW BEST! Similarity: {avg_similarity*100:.2f}%")
        else:
            no_improvement_count += 1
            print(f"\n  Similarity: {avg_similarity*100:.2f}% (best: {best_similarity*100:.2f}%)")

        print(f"  Entropy: {entropy_pct:.2f}%")

        if i > 1:
            prev_sim = results[-2].avg_similarity
            change = avg_similarity - prev_sim
            if change > 0:
                print(f"  ✓ Similarity improved by {change*100:.2f}%")
            elif change < 0:
                print(f"  ⚠️ Similarity decreased by {abs(change)*100:.2f}%")
            else:
                print(f"  → No change in similarity")

        # NO EARLY STOPPING — all 8 iterations always run

    summary = {
        "experiment_dir": str(experiment_dir),
        "prompt_file": "prompt.txt",
        "total_iterations": len(results),
        "converged": False,
        "best_iteration": best_result.iteration if best_result else None,
        "best_similarity": best_similarity,
        "final_similarity": results[-1].avg_similarity if results else 0,
        "final_entropy": results[-1].entropy_pct if results else 0,
        "config": asdict(config),
        "iterations": [
            {
                "iteration": r.iteration,
                "entropy_pct": r.entropy_pct,
                "avg_similarity": r.avg_similarity,
                "is_best": r.is_best,
                "video": r.video_path,
                "mesh": r.mesh_path
            }
            for r in results
        ]
    }

    summary_path = experiment_dir / "experiment_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    if best_result:
        best_dir = experiment_dir / "BEST"
        best_dir.mkdir(exist_ok=True)

        if Path(best_result.video_path).exists():
            shutil.copy(best_result.video_path, best_dir / "best_output.mp4")
        if Path(best_result.mesh_path).exists():
            shutil.copy(best_result.mesh_path, best_dir / "best_mesh.glb")
        if Path(best_result.config_path).exists():
            shutil.copy(best_result.config_path, best_dir / "best_config.json")
        if Path(best_result.eval_path).exists():
            shutil.copy(best_result.eval_path, best_dir / "best_evaluation.json")

    print(f"\n{'='*70}")
    print("EXPERIMENT COMPLETE")
    print(f"{'='*70}")
    print(f"Results: {experiment_dir}/")
    print(f"Summary: {summary_path.name}")
    if best_result:
        print(f"Best Output: {experiment_dir}/BEST/")

    if len(results) > 1:
        print(f"\n{'='*70}")
        print("PROGRESSION")
        print(f"{'='*70}")
        print(f"{'Iter':<6} {'Similarity':<12} {'Entropy':<10} {'Status':<10}")
        print("-"*70)

        for r in results:
            status = "⭐ BEST" if r.is_best else ""
            print(f"{r.iteration:<6} {r.avg_similarity*100:<12.2f} {r.entropy_pct:<10.2f} {status}")

        print("-"*70)
        if best_result:
            print(f"Best: Iteration {best_result.iteration} with {best_similarity*100:.2f}% similarity")

    print(f"{'='*70}\n")

    return summary


# ============================================================================
# CLI ENTRY
# ============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Run TRELLIS feedback loop")
    parser.add_argument('--max-iterations', '-n', type=int, default=8,
                        help='Maximum iterations (default: 8 = 1 baseline + 7 refined)')
    parser.add_argument('--target-similarity', '-t', type=float, default=1.01,
                        help='Target similarity (default: 1.01 = never converges early)')
    parser.add_argument('--patience', '-p', type=int, default=8,
                        help='Patience (default: 8 = never stops early)')
    parser.add_argument('--no-revert', action='store_true',
                        help='Disable reverting to best config on decline')
    parser.add_argument('--max-boost-tokens', type=int, default=5,
                        help='Max tokens boosted simultaneously per round (default: 5). '
                             'Set to 1 for single-worst-token-only boosting.')
    parser.add_argument('--zero-mean', dest='zero_mean', action='store_true', default=None,
                        help='Enable zero-mean rebalancing (default: enabled)')
    parser.add_argument('--no-zero-mean', dest='zero_mean', action='store_false',
                        help='Disable zero-mean rebalancing (additive-only boosting)')
    parser.add_argument('--uniform', dest='uniform_mode', action='store_true',
                        help='Use uniform boosting (no phase categorization). '
                             'For the TATI-vs-uniform ablation.')

    args = parser.parse_args()

    config = ExperimentConfig(
        max_iterations=args.max_iterations,
        target_similarity=args.target_similarity,
        patience=args.patience,
        revert_on_decline=not args.no_revert,
        max_boost_tokens=args.max_boost_tokens,
        zero_mean=args.zero_mean if args.zero_mean is not None else True,
        uniform_mode=args.uniform_mode,
    )

    run_trellis_feedback_loop(config)