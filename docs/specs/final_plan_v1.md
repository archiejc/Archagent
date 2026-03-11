# Final Plan Contract v1

## 1. Purpose
`final_plan.json` is the canonical output contract for downstream visualization/generation apps.
It must be sufficient for:

1. Reproducible research replay.
2. Grasshopper regeneration (`local_batch` mode in phase-1).
3. Visualization app loading (selected design + candidate index + artifacts).

Schema source:

- `schemas/final_plan.v1.schema.json`
- `schemas/design_option.v1.schema.json`

## 2. Top-level structure
`final_plan.json` must include:

1. `semantic_plan`: negotiated constraints + KPI/fairness/pareto summaries.
2. `generation_recipe`: GH definition and sampling recipe (`variant_count=12`, `coordinate_strategy=dual`).
3. `selected_variant`: single winner with artifact references.
4. `candidates_index`: index of candidate variants and JSONL location.
5. `selection_trace`: 3-judge vote trace with final choice.

## 3. Hard requirements
1. `generation_recipe.variant_count` is fixed to `12` in phase-1.
2. `generation_recipe.runtime.mode` must be `local_batch`.
3. `generation_recipe.coordinate_strategy` must be `dual`.
4. `selected_variant.variant_id` must exist in candidate set and be `constraint_pass=true`.
5. `selection_trace.final_choice` must equal `selected_variant.variant_id`.
6. `selection_trace.judges` must contain exactly 3 judge traces.

## 4. Candidate sidecar row (`design_options.jsonl`)
Each line must provide:

1. Identification: `variant_id`, `source_plan_id`, `gh_definition`.
2. Parameters: `param_vector`.
3. Artifacts: `geometry_ref.rhino_3dm`, `preview_ref.birdview_png`, `preview_ref.siteplan_png`.
4. Metrics: `kpi`.
5. Feasibility: `constraint_pass`.
6. Traceability: `object_guid_map` and `geometry_objects`.
7. Coordinates: dual metadata via `local_coord` + `geo_coord`, or conversion fallback with `transform_ref` + `coordinate_meta.transform_info`.

## 5. Validation and error codes
Validation is provided by `scripts/validate_contracts.py`.

Error codes:

1. `E_SCHEMA_VALIDATION`: schema-level contract violation.
2. `E_PARAM_INVALID`: invalid adapter/generation input parameter.
3. `E_GH_EXECUTION_FAILED`: adapter runtime failure.
4. `E_ARTIFACT_MISSING`: referenced artifact path not found.
5. `E_COORD_MAPPING_FAILED`: coordinate transform metadata missing when dual coordinates are incomplete.
6. `E_SELECTION_INVALID`: winner/selection trace inconsistency.
7. `E_CONTRACT_INCONSISTENT`: cross-file data mismatch (variant id, guid map, count mismatch).

## 6. Reference commands
```bash
# Generate mock phase-1 outputs
python3 scripts/run_mock_pipeline.py --output-dir examples --seed 42

# Validate contracts
python3 scripts/validate_contracts.py --final-plan examples/final_plan.json --json
```
