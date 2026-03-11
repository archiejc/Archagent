import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archagent.coordinates import local_roundtrip_error_m
from archagent.pipeline import run_mock_pipeline


class MockPipelineTests(unittest.TestCase):
    def test_end_to_end_pipeline_outputs_usable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_mock_pipeline(output_dir=Path(tmp), seed=11)
            self.assertEqual([], result["issues"])

            final_plan = json.loads(result["final_plan_path"].read_text(encoding="utf-8"))
            options = [json.loads(line) for line in result["design_options_path"].read_text(encoding="utf-8").splitlines() if line.strip()]

            self.assertEqual(12, len(options))
            self.assertIn(final_plan["selected_variant"]["variant_id"], {opt["variant_id"] for opt in options})
            self.assertEqual(3, len(final_plan["selection_trace"]["judges"]))

            for option in options:
                rhino_path = result["final_plan_path"].parent / option["geometry_ref"]["rhino_3dm"]
                bird_path = result["final_plan_path"].parent / option["preview_ref"]["birdview_png"]
                site_path = result["final_plan_path"].parent / option["preview_ref"]["siteplan_png"]
                self.assertTrue(rhino_path.exists())
                self.assertTrue(bird_path.exists())
                self.assertTrue(site_path.exists())

    def test_coordinate_roundtrip_error_under_threshold(self) -> None:
        origin = {"lon": 121.4737, "lat": 31.2304, "alt": 0.0}
        local = {"x": 125.0, "y": 86.0, "z": 48.0}
        err = local_roundtrip_error_m(local, origin)
        self.assertLess(err, 1e-6)


if __name__ == "__main__":
    unittest.main()
