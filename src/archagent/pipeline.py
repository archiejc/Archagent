from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import json

from .contracts import validate_contract_files
from .gh_adapter import generate_local_batch_candidates, write_design_options_jsonl
from .selection import run_majority_vote, simulate_three_judges


def default_generation_recipe(seed: int = 42) -> Dict[str, Any]:
    return {
        "runtime": {"mode": "local_batch"},
        "gh_definition": "tower_mix_v3.ghx",
        "parameter_bounds": {
            "far": {"min": 2.4, "max": 3.2},
            "green_ratio": {"min": 0.30, "max": 0.45},
            "public_space_ratio": {"min": 0.12, "max": 0.26},
            "podium_height_m": {"min": 12.0, "max": 24.0}
        },
        "sampling_strategy": "lhs",
        "seed": seed,
        "variant_count": 12,
        "coordinate_strategy": "dual",
        "coordinate_context": {
            "local_crs": {"name": "project_local", "unit": "meter"},
            "geo_crs": {"epsg": "EPSG:4326"},
            "geo_origin": {"lon": 121.4737, "lat": 31.2304, "alt": 0.0}
        }
    }


def _build_final_plan(
    source_plan_id: str,
    generation_recipe: dict,
    design_options: list,
    score_summary: dict,
    selection_trace: dict,
    selected_variant_id: str,
) -> dict:
    selected_option = next(option for option in design_options if option["variant_id"] == selected_variant_id)

    social_welfare = round(
        sum(
            0.35 * float(opt["kpi"].get("roi", 0.0))
            + 0.35 * float(opt["kpi"].get("fairness_proxy", 0.0))
            + 0.30 * float(opt["kpi"].get("public_space_ratio", 0.0))
            for opt in design_options
        )
        / len(design_options),
        6,
    )

    return {
        "version": "final_plan.v1",
        "plan_id": source_plan_id,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "semantic_plan": {
            "negotiation_summary": "Mock negotiation output for phase-1 contract validation.",
            "hard_constraints": [
                "FAR <= 3.2",
                "green_ratio >= 0.30",
                "budget_million <= 900"
            ],
            "kpi_summary": {
                "agreement_rate": 1.0,
                "deadlock_rate": 0.0,
                "individual_rationality_rate": 1.0,
                "pareto_frontier_distance": 0.12,
                "social_welfare": social_welfare
            },
            "fairness": {
                "individual_rationality_rate": 1.0,
                "utility_balance_index": 0.87
            },
            "pareto": {
                "distance": 0.12,
                "frontier_estimation_method": "simulation_surrogate_v1"
            }
        },
        "generation_recipe": generation_recipe,
        "selected_variant": {
            "variant_id": selected_variant_id,
            "selection_rationale": "Chosen by 3-judge majority vote with tiebreak by average score.",
            "artifact_refs": {
                "rhino_3dm": selected_option["geometry_ref"]["rhino_3dm"],
                "birdview_png": selected_option["preview_ref"]["birdview_png"],
                "siteplan_png": selected_option["preview_ref"]["siteplan_png"]
            },
            "score_summary": score_summary
        },
        "candidates_index": {
            "source_type": "jsonl_path",
            "path": "design_options.jsonl",
            "variant_ids": [opt["variant_id"] for opt in design_options]
        },
        "selection_trace": selection_trace
    }


def run_mock_pipeline(output_dir: Path, seed: int = 42, source_plan_id: str = "plan_20260311_001") -> Dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    generation_recipe = default_generation_recipe(seed=seed)

    adapter_result = generate_local_batch_candidates(
        generation_recipe=generation_recipe,
        source_plan_id=source_plan_id,
        output_root=output_dir,
    )

    design_options_path = output_dir / "design_options.jsonl"
    write_design_options_jsonl(adapter_result.design_options, design_options_path)

    judges = simulate_three_judges(adapter_result.design_options, seed=seed)
    selected_variant_id, score_summary, selection_trace = run_majority_vote(adapter_result.design_options, judges)

    final_plan = _build_final_plan(
        source_plan_id=source_plan_id,
        generation_recipe=generation_recipe,
        design_options=adapter_result.design_options,
        score_summary=score_summary,
        selection_trace=selection_trace,
        selected_variant_id=selected_variant_id,
    )

    final_plan_path = output_dir / "final_plan.json"
    final_plan_path.write_text(json.dumps(final_plan, ensure_ascii=False, indent=2), encoding="utf-8")

    adapter_log_path = output_dir / "adapter_run_log.json"
    adapter_log_path.write_text(json.dumps(adapter_result.adapter_run_log, ensure_ascii=False, indent=2), encoding="utf-8")

    issues = validate_contract_files(final_plan_path=final_plan_path, design_options_path=design_options_path)

    return {
        "final_plan_path": final_plan_path,
        "design_options_path": design_options_path,
        "adapter_log_path": adapter_log_path,
        "issues": issues,
        "selection_trace": selection_trace,
        "selected_variant_id": selected_variant_id,
    }
