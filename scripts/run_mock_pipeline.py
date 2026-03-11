#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archagent.pipeline import run_mock_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Run mock phase-1 pipeline and emit final_plan/design_options.")
    parser.add_argument("--output-dir", default=str(ROOT / "examples"), help="Output folder for generated files")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    result = run_mock_pipeline(output_dir=Path(args.output_dir), seed=args.seed)
    issues = result["issues"]

    if issues:
        print("Mock pipeline generated invalid outputs:")
        for issue in issues:
            print(f"- {issue.code.value} @ {issue.path}: {issue.message}")
        return 1

    print(f"Generated: {result['final_plan_path']}")
    print(f"Generated: {result['design_options_path']}")
    print(f"Generated: {result['adapter_log_path']}")
    print(f"Generated artifacts folder: {result['final_plan_path'].parent / 'artifacts'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
