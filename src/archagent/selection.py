from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple
import random


@dataclass(frozen=True)
class JudgeResult:
    judge_id: str
    model: str
    scores: Dict[str, float]
    reason_summary: str


def _feasible_variant_ids(candidates: Iterable[dict]) -> List[str]:
    return [c["variant_id"] for c in candidates if c.get("constraint_pass", False)]


def _top_choice(scores: Dict[str, float], feasible_ids: List[str]) -> Tuple[str, float]:
    ranked = sorted(
        [(variant_id, scores.get(variant_id, float("-inf"))) for variant_id in feasible_ids],
        key=lambda x: (x[1], x[0]),
        reverse=True,
    )
    return ranked[0]


def simulate_three_judges(candidates: List[dict], seed: int = 42) -> List[JudgeResult]:
    """Simulate three independent LLM judges with deterministic seeded scoring."""
    feasible_ids = _feasible_variant_ids(candidates)
    if not feasible_ids:
        raise ValueError("No feasible candidates after constraint filter.")

    candidate_map = {c["variant_id"]: c for c in candidates}
    judges: List[JudgeResult] = []

    profiles = [
        ("judge_a", "llm-judge-a-v1", {"roi": 0.30, "public_space_ratio": 0.28, "fairness_proxy": 0.24, "carbon_penalty": 0.18}),
        ("judge_b", "llm-judge-b-v1", {"roi": 0.26, "public_space_ratio": 0.30, "fairness_proxy": 0.22, "carbon_penalty": 0.22}),
        ("judge_c", "llm-judge-c-v1", {"roi": 0.28, "public_space_ratio": 0.24, "fairness_proxy": 0.30, "carbon_penalty": 0.18}),
    ]

    for idx, (judge_id, model, weights) in enumerate(profiles):
        rng = random.Random(seed + idx * 97)
        scores: Dict[str, float] = {}
        for variant_id in feasible_ids:
            kpi = candidate_map[variant_id].get("kpi", {})
            roi = float(kpi.get("roi", 0.0))
            public_ratio = float(kpi.get("public_space_ratio", 0.0))
            fairness_proxy = float(kpi.get("fairness_proxy", 0.0))
            carbon_proxy = float(kpi.get("carbon_proxy", 0.0))

            normalized_carbon_penalty = min(max(carbon_proxy / 2000.0, 0.0), 1.0)
            base_score = (
                roi * weights["roi"]
                + public_ratio * weights["public_space_ratio"]
                + fairness_proxy * weights["fairness_proxy"]
                + (1.0 - normalized_carbon_penalty) * weights["carbon_penalty"]
            )
            jitter = rng.uniform(-0.015, 0.015)
            scores[variant_id] = round(base_score + jitter, 6)

        judges.append(
            JudgeResult(
                judge_id=judge_id,
                model=model,
                scores=scores,
                reason_summary=(
                    "LLM-style holistic assessment with KPI-informed features "
                    "(fairness, ROI, public space, carbon)."
                ),
            )
        )

    return judges


def run_majority_vote(candidates: List[dict], judges: List[JudgeResult]) -> Tuple[str, Dict[str, float], dict]:
    """Run 3-judge majority vote. Tie-break by average score then stable lexical order."""
    if len(judges) != 3:
        raise ValueError("Exactly three judges are required by protocol.")

    feasible_ids = _feasible_variant_ids(candidates)
    if not feasible_ids:
        raise ValueError("No feasible candidates for selection.")

    vote_tally: Dict[str, int] = {variant_id: 0 for variant_id in feasible_ids}
    judge_traces = []

    for judge in judges:
        top_variant, top_score = _top_choice(judge.scores, feasible_ids)
        vote_tally[top_variant] += 1
        judge_traces.append(
            {
                "judge_id": judge.judge_id,
                "model": judge.model,
                "top_choice": top_variant,
                "top_score": top_score,
                "reason_summary": judge.reason_summary,
                "scores": judge.scores,
            }
        )

    max_votes = max(vote_tally.values())
    vote_winners = sorted([variant_id for variant_id, votes in vote_tally.items() if votes == max_votes])

    tie_break_applied = len(vote_winners) > 1
    if tie_break_applied:
        avg_scores = {
            variant_id: sum(judge.scores.get(variant_id, 0.0) for judge in judges) / len(judges)
            for variant_id in vote_winners
        }
        best_avg = max(avg_scores.values())
        avg_winners = sorted([variant_id for variant_id, score in avg_scores.items() if score == best_avg])
        final_choice = avg_winners[0]
    else:
        final_choice = vote_winners[0]

    final_avg_score = round(sum(judge.scores.get(final_choice, 0.0) for judge in judges) / len(judges), 6)

    score_summary = {
        "winner_method": "majority_vote_then_avg_score_tiebreak",
        "vote_count": vote_tally[final_choice],
        "avg_judge_score": final_avg_score,
    }

    selection_trace = {
        "strategy": "llm_majority_vote_v1",
        "judges": judge_traces,
        "vote_tally": vote_tally,
        "tie_break_applied": tie_break_applied,
        "final_choice": final_choice,
    }

    return final_choice, score_summary, selection_trace
