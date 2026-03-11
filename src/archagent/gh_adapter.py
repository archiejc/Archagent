from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
import json
import random
import uuid

from .coordinates import local_to_geo
from .error_codes import ErrorCode


class AdapterError(Exception):
    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AdapterRunResult:
    design_options: List[dict]
    adapter_run_log: dict


def _sample_in_bounds(bounds: Dict[str, float], rng: random.Random) -> float:
    if "min" not in bounds or "max" not in bounds:
        raise AdapterError(ErrorCode.E_PARAM_INVALID, "Parameter bounds must include min and max.")
    lo = float(bounds["min"])
    hi = float(bounds["max"])
    if lo > hi:
        raise AdapterError(ErrorCode.E_PARAM_INVALID, f"Invalid bounds: min {lo} > max {hi}.")
    return round(rng.uniform(lo, hi), 4)


def _touch(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate_local_batch_candidates(
    generation_recipe: dict,
    source_plan_id: str,
    output_root: Path,
) -> AdapterRunResult:
    """Mock local batch runner that emulates Grasshopper outputs and sidecar data."""
    try:
        if generation_recipe.get("runtime", {}).get("mode") != "local_batch":
            raise AdapterError(ErrorCode.E_PARAM_INVALID, "Only local_batch mode is supported in phase-1 mock adapter.")

        variant_count = int(generation_recipe.get("variant_count", 12))
        if variant_count <= 0:
            raise AdapterError(ErrorCode.E_PARAM_INVALID, "variant_count must be positive.")

        parameter_bounds = generation_recipe.get("parameter_bounds", {})
        if not parameter_bounds:
            raise AdapterError(ErrorCode.E_PARAM_INVALID, "parameter_bounds cannot be empty.")

        gh_definition = generation_recipe.get("gh_definition")
        if not gh_definition:
            raise AdapterError(ErrorCode.E_PARAM_INVALID, "gh_definition is required.")

        rng = random.Random(int(generation_recipe.get("seed", 42)))
        origin_geo = generation_recipe.get("coordinate_context", {}).get(
            "geo_origin", {"lon": 121.4737, "lat": 31.2304, "alt": 0.0}
        )

        artifacts_dir = output_root / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        design_options: List[dict] = []
        for idx in range(1, variant_count + 1):
            variant_id = f"v_{idx:03d}"
            param_vector = {
                name: _sample_in_bounds(bounds, rng) for name, bounds in parameter_bounds.items()
            }

            base_x = rng.uniform(0.0, 180.0)
            base_y = rng.uniform(0.0, 220.0)
            local_a = {"x": round(base_x, 3), "y": round(base_y, 3), "z": 0.0}
            local_b = {"x": round(base_x + rng.uniform(8, 24), 3), "y": round(base_y + rng.uniform(8, 24), 3), "z": round(rng.uniform(25, 95), 3)}

            geo_a = local_to_geo(local_a, origin_geo)
            geo_b = local_to_geo(local_b, origin_geo)

            guid_a = str(uuid.uuid4())
            guid_b = str(uuid.uuid4())

            rhino_path = artifacts_dir / f"{variant_id}.3dm"
            bird_path = artifacts_dir / f"{variant_id}_birdview.png"
            site_path = artifacts_dir / f"{variant_id}_siteplan.png"

            _touch(rhino_path, f"Mock Rhino model for {variant_id}\n")
            _touch(bird_path, f"Mock birdview for {variant_id}\n")
            _touch(site_path, f"Mock siteplan for {variant_id}\n")

            far = float(param_vector.get("far", 2.8))
            green_ratio = float(param_vector.get("green_ratio", 0.35))
            public_space_ratio = float(param_vector.get("public_space_ratio", 0.18))
            carbon_proxy = round(900 + far * 120 - green_ratio * 250 + rng.uniform(-15, 15), 3)
            roi = round(0.07 + far * 0.008 + rng.uniform(-0.003, 0.003), 6)
            fairness_proxy = round(min(max(0.4 + public_space_ratio * 1.2 + green_ratio * 0.6, 0.0), 1.0), 6)

            design_options.append(
                {
                    "variant_id": variant_id,
                    "source_plan_id": source_plan_id,
                    "gh_definition": gh_definition,
                    "param_vector": param_vector,
                    "geometry_ref": {
                        "rhino_3dm": str(rhino_path.relative_to(output_root)),
                    },
                    "preview_ref": {
                        "birdview_png": str(bird_path.relative_to(output_root)),
                        "siteplan_png": str(site_path.relative_to(output_root)),
                    },
                    "kpi": {
                        "roi": roi,
                        "carbon_proxy": carbon_proxy,
                        "public_space_ratio": public_space_ratio,
                        "fairness_proxy": fairness_proxy,
                    },
                    "constraint_pass": True,
                    "object_guid_map": {
                        guid_a: "podium_mass",
                        guid_b: "tower_mass",
                    },
                    "coordinate_meta": {
                        "strategy": "dual",
                        "transform_info": {
                            "method": "local_metric_to_wgs84",
                            "origin_lon": origin_geo["lon"],
                            "origin_lat": origin_geo["lat"],
                            "unit": "meter",
                        },
                    },
                    "geometry_objects": [
                        {
                            "object_guid": guid_a,
                            "semantic_component": "podium_mass",
                            "local_coord": local_a,
                            "geo_coord": geo_a,
                        },
                        {
                            "object_guid": guid_b,
                            "semantic_component": "tower_mass",
                            "local_coord": local_b,
                            "geo_coord": geo_b,
                        },
                    ],
                }
            )

        run_log = {
            "status": "success",
            "runtime_mode": "local_batch",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "generated_count": len(design_options),
            "gh_definition": gh_definition,
            "errors": [],
        }
        return AdapterRunResult(design_options=design_options, adapter_run_log=run_log)

    except AdapterError:
        raise
    except Exception as exc:  # pragma: no cover - defense path
        raise AdapterError(ErrorCode.E_GH_EXECUTION_FAILED, f"Unexpected adapter failure: {exc}") from exc


def write_design_options_jsonl(design_options: List[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for entry in design_options:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
