import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from archagent.selection import JudgeResult, run_majority_vote, simulate_three_judges


class SelectionProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidates = [
            {"variant_id": "v_001", "constraint_pass": True, "kpi": {"roi": 0.08, "public_space_ratio": 0.18, "fairness_proxy": 0.70, "carbon_proxy": 1100}},
            {"variant_id": "v_002", "constraint_pass": True, "kpi": {"roi": 0.09, "public_space_ratio": 0.21, "fairness_proxy": 0.74, "carbon_proxy": 1080}},
            {"variant_id": "v_003", "constraint_pass": False, "kpi": {"roi": 0.11, "public_space_ratio": 0.19, "fairness_proxy": 0.65, "carbon_proxy": 1300}},
        ]

    def test_majority_vote_selects_vote_winner(self) -> None:
        judges = [
            JudgeResult("j1", "m1", {"v_001": 0.52, "v_002": 0.56}, "r1"),
            JudgeResult("j2", "m2", {"v_001": 0.58, "v_002": 0.53}, "r2"),
            JudgeResult("j3", "m3", {"v_001": 0.51, "v_002": 0.59}, "r3"),
        ]
        choice, score_summary, trace = run_majority_vote(self.candidates, judges)
        self.assertEqual("v_002", choice)
        self.assertEqual(choice, trace["final_choice"])
        self.assertEqual(2, score_summary["vote_count"])

    def test_tie_break_by_average_score(self) -> None:
        tie_candidates = [
            {"variant_id": "v_001", "constraint_pass": True, "kpi": {}},
            {"variant_id": "v_002", "constraint_pass": True, "kpi": {}},
            {"variant_id": "v_003", "constraint_pass": True, "kpi": {}},
        ]
        judges = [
            JudgeResult("j1", "m1", {"v_001": 0.60, "v_002": 0.59, "v_003": 0.40}, "r1"),
            JudgeResult("j2", "m2", {"v_001": 0.55, "v_002": 0.58, "v_003": 0.61}, "r2"),
            JudgeResult("j3", "m3", {"v_001": 0.52, "v_002": 0.65, "v_003": 0.49}, "r3"),
        ]
        choice, _score_summary, trace = run_majority_vote(tie_candidates, judges)
        self.assertTrue(trace["tie_break_applied"])
        self.assertEqual("v_002", choice)

    def test_simulate_three_judges_returns_three_independent_results(self) -> None:
        judges = simulate_three_judges(self.candidates, seed=7)
        self.assertEqual(3, len(judges))
        self.assertEqual({"judge_a", "judge_b", "judge_c"}, {j.judge_id for j in judges})


if __name__ == "__main__":
    unittest.main()
