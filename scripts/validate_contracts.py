#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archagent.contracts import validate_contract_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate final_plan and design_options contracts.")
    parser.add_argument("--final-plan", required=True, help="Path to final_plan.json")
    parser.add_argument("--design-options", help="Path to design_options.jsonl (optional if referenced in final_plan)")
    parser.add_argument(
        "--artifacts-root",
        help="Base directory for relative artifact paths (defaults to final_plan directory)",
    )
    parser.add_argument("--json", action="store_true", help="Output validation result as JSON")
    args = parser.parse_args()

    final_plan_path = Path(args.final_plan)
    design_options_path = Path(args.design_options) if args.design_options else None
    artifacts_root = Path(args.artifacts_root) if args.artifacts_root else None

    issues = validate_contract_files(
        final_plan_path=final_plan_path,
        design_options_path=design_options_path,
        artifacts_root=artifacts_root,
    )

    payload = {
        "ok": len(issues) == 0,
        "issue_count": len(issues),
        "issues": [issue.to_dict() for issue in issues],
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if payload["ok"]:
            print("Validation passed.")
        else:
            print(f"Validation failed with {payload['issue_count']} issue(s).")
            for issue in payload["issues"]:
                print(f"- {issue['code']} @ {issue['path']}: {issue['message']}")

    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
