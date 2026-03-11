from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from jsonschema import Draft202012Validator

from .error_codes import ErrorCode

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "schemas"


@dataclass(frozen=True)
class ContractIssue:
    code: ErrorCode
    message: str
    path: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "code": self.code.value,
            "message": self.message,
            "path": self.path,
        }


def _fmt_json_path(parts: List[Any], root: str = "$") -> str:
    formatted = root
    for part in parts:
        if isinstance(part, int):
            formatted += f"[{part}]"
        else:
            formatted += f".{part}"
    return formatted


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_idx, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_idx}: {exc}") from exc
    return rows


def _schema_issues(schema_name: str, data: Dict[str, Any], root: str) -> List[ContractIssue]:
    schema_path = SCHEMA_DIR / schema_name
    schema = _load_json(schema_path)
    validator = Draft202012Validator(schema)

    issues: List[ContractIssue] = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        issues.append(
            ContractIssue(
                code=ErrorCode.E_SCHEMA_VALIDATION,
                message=error.message,
                path=_fmt_json_path(list(error.absolute_path), root=root),
            )
        )
    return issues


def _resolve_path(path_text: str, base_dir: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _validate_coordinate_rules(option: Dict[str, Any], idx: int) -> List[ContractIssue]:
    issues: List[ContractIssue] = []

    coord_meta = option.get("coordinate_meta", {})
    transform_info = coord_meta.get("transform_info")
    geometry_objects = option.get("geometry_objects", [])

    for obj_idx, geom_obj in enumerate(geometry_objects):
        has_local = "local_coord" in geom_obj
        has_geo = "geo_coord" in geom_obj
        if has_local and has_geo:
            continue

        has_transform_ref = "transform_ref" in geom_obj
        if not (transform_info and has_transform_ref):
            issues.append(
                ContractIssue(
                    code=ErrorCode.E_COORD_MAPPING_FAILED,
                    message=(
                        "Missing dual coordinate info. If local_coord or geo_coord is absent, "
                        "coordinate_meta.transform_info and geometry_objects[].transform_ref are required."
                    ),
                    path=f"$.design_options[{idx}].geometry_objects[{obj_idx}]",
                )
            )

    return issues


def validate_contract_files(
    final_plan_path: Path,
    design_options_path: Optional[Path] = None,
    artifacts_root: Optional[Path] = None,
) -> List[ContractIssue]:
    final_plan_path = final_plan_path.resolve()
    base_dir = final_plan_path.parent
    effective_artifacts_root = artifacts_root.resolve() if artifacts_root else base_dir.resolve()

    issues: List[ContractIssue] = []
    final_plan = _load_json(final_plan_path)
    issues.extend(_schema_issues("final_plan.v1.schema.json", final_plan, root="$final_plan"))

    source_type = final_plan.get("candidates_index", {}).get("source_type", "jsonl_path")

    design_options: List[Dict[str, Any]] = []
    if source_type == "inline":
        design_options = list(final_plan.get("candidates_index", {}).get("entries", []))
    else:
        if design_options_path is None:
            rel_path = final_plan.get("candidates_index", {}).get("path")
            if not rel_path:
                issues.append(
                    ContractIssue(
                        code=ErrorCode.E_CONTRACT_INCONSISTENT,
                        message="candidates_index.path is required when source_type is jsonl_path.",
                        path="$final_plan.candidates_index.path",
                    )
                )
                return issues
            design_options_path = _resolve_path(rel_path, base_dir)

        if not design_options_path.exists():
            issues.append(
                ContractIssue(
                    code=ErrorCode.E_ARTIFACT_MISSING,
                    message=f"design_options.jsonl not found: {design_options_path}",
                    path="$design_options",
                )
            )
            return issues
        design_options = _load_jsonl(design_options_path)

    for idx, option in enumerate(design_options):
        option_issues = _schema_issues("design_option.v1.schema.json", option, root=f"$design_options[{idx}]")
        issues.extend(option_issues)

    variant_ids = [option.get("variant_id") for option in design_options if "variant_id" in option]
    if len(variant_ids) != len(set(variant_ids)):
        issues.append(
            ContractIssue(
                code=ErrorCode.E_CONTRACT_INCONSISTENT,
                message="Duplicate variant_id found in design options.",
                path="$design_options[*].variant_id",
            )
        )

    option_map = {option.get("variant_id"): option for option in design_options if "variant_id" in option}

    indexed_variant_ids = final_plan.get("candidates_index", {}).get("variant_ids", [])
    for variant_id in indexed_variant_ids:
        if variant_id not in option_map:
            issues.append(
                ContractIssue(
                    code=ErrorCode.E_CONTRACT_INCONSISTENT,
                    message=f"Indexed variant_id not found in design options: {variant_id}",
                    path="$final_plan.candidates_index.variant_ids",
                )
            )

    expected_count = int(final_plan.get("generation_recipe", {}).get("variant_count", 0))
    if expected_count and expected_count != len(design_options):
        issues.append(
            ContractIssue(
                code=ErrorCode.E_CONTRACT_INCONSISTENT,
                message=(
                    f"Variant count mismatch: generation_recipe.variant_count={expected_count}, "
                    f"design_options={len(design_options)}"
                ),
                path="$final_plan.generation_recipe.variant_count",
            )
        )

    selected_variant_id = final_plan.get("selected_variant", {}).get("variant_id")
    if selected_variant_id not in option_map:
        issues.append(
            ContractIssue(
                code=ErrorCode.E_SELECTION_INVALID,
                message=f"selected_variant not found in candidate set: {selected_variant_id}",
                path="$final_plan.selected_variant.variant_id",
            )
        )
    else:
        selected_option = option_map[selected_variant_id]
        if not selected_option.get("constraint_pass", False):
            issues.append(
                ContractIssue(
                    code=ErrorCode.E_SELECTION_INVALID,
                    message="selected_variant must be constraint_pass=true.",
                    path="$final_plan.selected_variant.variant_id",
                )
            )

        trace_choice = final_plan.get("selection_trace", {}).get("final_choice")
        if trace_choice != selected_variant_id:
            issues.append(
                ContractIssue(
                    code=ErrorCode.E_SELECTION_INVALID,
                    message="selection_trace.final_choice must equal selected_variant.variant_id.",
                    path="$final_plan.selection_trace.final_choice",
                )
            )

        selected_refs = final_plan.get("selected_variant", {}).get("artifact_refs", {})
        for key, option_key in [
            ("rhino_3dm", "rhino_3dm"),
            ("birdview_png", "birdview_png"),
            ("siteplan_png", "siteplan_png"),
        ]:
            plan_ref = selected_refs.get(key)
            option_ref = (
                selected_option.get("geometry_ref", {}).get(option_key)
                if key == "rhino_3dm"
                else selected_option.get("preview_ref", {}).get(option_key)
            )
            if plan_ref and option_ref and plan_ref != option_ref:
                issues.append(
                    ContractIssue(
                        code=ErrorCode.E_CONTRACT_INCONSISTENT,
                        message=(
                            f"Artifact reference mismatch for {key}: "
                            f"selected_variant={plan_ref}, option={option_ref}"
                        ),
                        path=f"$final_plan.selected_variant.artifact_refs.{key}",
                    )
                )

    for idx, option in enumerate(design_options):
        option_id = option.get("variant_id", f"idx_{idx}")

        object_guid_map = option.get("object_guid_map", {})
        geometry_objects = option.get("geometry_objects", [])

        if not object_guid_map:
            issues.append(
                ContractIssue(
                    code=ErrorCode.E_CONTRACT_INCONSISTENT,
                    message="object_guid_map cannot be empty.",
                    path=f"$design_options[{idx}].object_guid_map",
                )
            )

        for obj_idx, geom_obj in enumerate(geometry_objects):
            object_guid = geom_obj.get("object_guid")
            semantic_component = geom_obj.get("semantic_component")
            mapped_component = object_guid_map.get(object_guid)
            if mapped_component is None:
                issues.append(
                    ContractIssue(
                        code=ErrorCode.E_CONTRACT_INCONSISTENT,
                        message=f"object_guid missing in object_guid_map: {object_guid}",
                        path=f"$design_options[{idx}].geometry_objects[{obj_idx}].object_guid",
                    )
                )
            elif mapped_component != semantic_component:
                issues.append(
                    ContractIssue(
                        code=ErrorCode.E_CONTRACT_INCONSISTENT,
                        message=(
                            f"Semantic mismatch for object_guid {object_guid}: "
                            f"map={mapped_component}, object={semantic_component}"
                        ),
                        path=f"$design_options[{idx}].geometry_objects[{obj_idx}].semantic_component",
                    )
                )

        issues.extend(_validate_coordinate_rules(option, idx))

        for artifact_rel in [
            option.get("geometry_ref", {}).get("rhino_3dm"),
            option.get("preview_ref", {}).get("birdview_png"),
            option.get("preview_ref", {}).get("siteplan_png"),
        ]:
            if not artifact_rel:
                continue
            artifact_path = _resolve_path(artifact_rel, effective_artifacts_root)
            if not artifact_path.exists():
                issues.append(
                    ContractIssue(
                        code=ErrorCode.E_ARTIFACT_MISSING,
                        message=f"Missing artifact for {option_id}: {artifact_rel}",
                        path=f"$design_options[{idx}]",
                    )
                )

    return issues
