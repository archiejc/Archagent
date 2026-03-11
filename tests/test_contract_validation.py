import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archagent.contracts import validate_contract_files
from archagent.error_codes import ErrorCode
from archagent.pipeline import run_mock_pipeline


class ContractValidationTests(unittest.TestCase):
    def test_contract_validation_passes_for_mock_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = run_mock_pipeline(output_dir=output_dir, seed=42)
            self.assertEqual([], result["issues"])

    def test_missing_object_guid_map_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = run_mock_pipeline(output_dir=output_dir, seed=42)
            self.assertEqual([], result["issues"])

            options_path = result["design_options_path"]
            lines = options_path.read_text(encoding="utf-8").strip().splitlines()
            first = json.loads(lines[0])
            first.pop("object_guid_map", None)
            lines[0] = json.dumps(first, ensure_ascii=True)
            options_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            issues = validate_contract_files(result["final_plan_path"], options_path)
            self.assertTrue(any(i.code == ErrorCode.E_SCHEMA_VALIDATION for i in issues))

    def test_missing_artifact_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            result = run_mock_pipeline(output_dir=output_dir, seed=42)
            self.assertEqual([], result["issues"])

            final_plan = json.loads(result["final_plan_path"].read_text(encoding="utf-8"))
            selected = final_plan["selected_variant"]["artifact_refs"]["rhino_3dm"]
            missing_path = (result["final_plan_path"].parent / selected).resolve()
            missing_path.unlink()

            issues = validate_contract_files(result["final_plan_path"], result["design_options_path"])
            self.assertTrue(any(i.code == ErrorCode.E_ARTIFACT_MISSING for i in issues))


if __name__ == "__main__":
    unittest.main()
