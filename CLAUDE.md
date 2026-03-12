# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Archagent is a research tool for multi-stakeholder architectural negotiation simulation. It models building design negotiations between stakeholders (developer, residents, planner, NGO) as a computational multi-agent system, producing reproducible experimental materials for analyzing game-theoretic outcomes (fairness, Pareto efficiency, social welfare).

The system comprises:
1. **Negotiation protocol** - SAOP-style agent interactions with structured JSON messages
2. **Grasshopper adapter** - Generates spatial design candidates from parameterized constraints
3. **Contract validation** - Schema enforcement for `final_plan.json` and `design_options.jsonl`
4. **Selection protocol** - 3-judge majority vote with tie-break by average score
5. **Evaluation metrics** - Agreement rate, deadlock rate, individual rationality, Pareto distance, social welfare

## Development Commands

### Run mock pipeline (generates test artifacts)
```bash
python scripts/run_mock_pipeline.py --output-dir examples --seed 42
```
Outputs: `final_plan.json`, `design_options.jsonl`, `adapter_run_log.json`, artifacts/

### Validate contracts
```bash
python scripts/validate_contracts.py --final-plan examples/final_plan.json --design-options examples/design_options.jsonl
```
Returns JSON or text report of schema/consistency violations.

### Run tests
```bash
python -m pytest tests/ -v
python -m pytest tests/test_contract_validation.py -v
python -m pytest tests/test_mock_pipeline.py::MockPipelineTests::test_end_to_end_pipeline_outputs_usable_artifacts -v
```

## Architecture

### Core modules (`src/archagent/`)
- `pipeline.py` - End-to-end mock pipeline orchestration
  - `run_mock_pipeline()` generates all artifacts and validates contracts
  - `default_generation_recipe()` defines parameter bounds and sampling config

- `gh_adapter.py` - Grasshopper mock adapter
  - `generate_local_batch_candidates()` simulates GH batch run, creates mock artifacts
  - `write_design_options_jsonl()` emits sidecar JSONL for downstream consumption

- `selection.py` - Judge simulation and majority voting
  - `simulate_three_judges()` creates 3 LLM-style judges with different KPI weight profiles
  - `run_majority_vote()` selects winner (tie-break by avg score, then lex order)

- `contracts.py` - Contract validation engine
  - `validate_contract_files()` checks schema, consistency, artifact existence
  - Cross-validates: variant counts, selected_variant vs candidates, object_guid_map vs geometry_objects, coordinate rules

- `coordinates.py` - Local<->geo coordinate transforms
  - `local_to_geo()`, `geo_to_local()` for dual-coordinate strategy
  - `local_roundtrip_error_m()` for precision validation

- `error_codes.py` - Machine-readable error codes (E_SCHEMA_VALIDATION, E_ARTIFACT_MISSING, etc.)

### Data contracts

**final_plan.json** (root output) contains:
- `semantic_plan`: negotiation summary, hard constraints, KPI summary (agreement_rate, deadlock_rate, etc.)
- `generation_recipe`: GH definition, parameter bounds, sampling strategy, coordinate context
- `selected_variant`: variant_id, artifact_refs (rhino_3dm, birdview_png, siteplan_png), score_summary
- `candidates_index`: source_type (jsonl_path/inline), variant_ids list, path to design_options.jsonl
- `selection_trace`: judge scores, vote_tally, final_choice, tie_break_applied flag

**design_options.jsonl** (one candidate per line) contains:
- `variant_id`, `param_vector` (GH input parameters)
- `geometry_ref` (rhino_3dm), `preview_ref` (birdview_png, siteplan_png)
- `kpi`: roi, carbon_proxy, public_space_ratio, fairness_proxy
- `object_guid_map`: GUID -> semantic_component mapping
- `geometry_objects`: per-object coordinates (local_coord + geo_coord for dual strategy)
- `coordinate_meta`: strategy (dual/local_only/geo_only), transform_info

### Design principles

- **Contract-first**: All outputs validated against strict JSON Schema before acceptance
- **Deterministic mocks**: Fixed seed → reproducible artifacts and metrics
- **Separation of concerns**: Negotiation layer produces parameter constraints; GH adapter generates spatial candidates
- **Traceability**: Every selected variant has full selection_trace with judge scores and rationale
- **Artifact references**: All file paths are relative to output root; validation checks existence

## Project files

- `docs/PRD.md` - Full product requirements and research methodology
- `docs/specs/` - Protocol and adapter specifications
- `schemas/*.schema.json` - JSON Schema definitions for contracts
- `.codex/` - Codex CLI agent configs (explorer, reviewer, docs-researcher)
- `examples/` - Generated artifacts from mock pipeline runs
