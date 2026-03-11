# Grasshopper Adapter Protocol v1 (Local Batch)

## 1. Scope
Phase-1 adapter protocol for Rhino/Grasshopper local batch generation.
The adapter consumes `generation_recipe + parameter_bounds + seed` and emits:

1. `design_options.jsonl`
2. `artifacts/*` (`.3dm`, birdview, siteplan)
3. `adapter_run_log.json`

## 2. Input contract
Adapter input is taken from `final_plan.generation_recipe`:

1. `runtime.mode`: must be `local_batch`.
2. `gh_definition`: GH file identifier/path.
3. `parameter_bounds`: per-parameter min/max envelope.
4. `sampling_strategy`: `lhs|grid|random`.
5. `seed`: deterministic run seed.
6. `variant_count`: fixed `12` in phase-1.
7. `coordinate_context`: local CRS + geo CRS + geo origin.

## 3. Output contract
### 3.1 `design_options.jsonl`
One row per generated candidate. Required row fields are defined in `design_option.v1.schema.json`.

### 3.2 `artifacts/*`
For each `variant_id`, required files:

1. `artifacts/{variant_id}.3dm`
2. `artifacts/{variant_id}_birdview.png`
3. `artifacts/{variant_id}_siteplan.png`

### 3.3 `adapter_run_log.json`
Recommended keys:

1. `status`: `success|failed`
2. `runtime_mode`
3. `generated_at`
4. `generated_count`
5. `gh_definition`
6. `errors`: list of machine-readable errors

## 4. Failure mode contract
Adapter must never fail silently. Return machine-readable error code on failure:

1. `E_PARAM_INVALID`
2. `E_GH_EXECUTION_FAILED`
3. `E_ARTIFACT_MISSING`
4. `E_COORD_MAPPING_FAILED`

## 5. Selection protocol coupling
After adapter output:

1. Filter `constraint_pass=false` candidates.
2. Run 3 independent judges.
3. Majority vote chooses winner.
4. If tied on votes, break tie by highest average judge score.
5. Persist full trace into `selection_trace`.

## 6. Implementation hooks in this repo
1. Mock adapter: `src/archagent/gh_adapter.py`
2. Selection aggregation: `src/archagent/selection.py`
3. E2E mock runner: `scripts/run_mock_pipeline.py`
4. Contract validation: `scripts/validate_contracts.py`
