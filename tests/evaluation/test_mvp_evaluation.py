from io import StringIO

from telecom_agent.evaluation.mvp import (
    EvalFeature,
    EvalGroup,
    build_report,
    evaluate_cases,
    load_cases,
    run_cli,
)


def test_versioned_mvp_dataset_has_approved_balanced_36_cases() -> None:
    cases = load_cases()

    assert len(cases) == len({case.id for case in cases}) == 36
    for feature in EvalFeature:
        feature_cases = [case for case in cases if case.feature is feature]
        assert sum(case.group is EvalGroup.ROUTINE for case in feature_cases) == 5
        assert sum(case.group is EvalGroup.SAFETY for case in feature_cases) == 4


def test_baseline_report_exposes_four_routine_scores_and_combined_safety() -> None:
    report = evaluate_cases(load_cases())

    assert set(report.routine_scores) == set(EvalFeature)
    assert report.safety_total == 16
    assert all(result.execution_source == "offline" for result in report.results)


def test_release_requires_every_feature_at_eighty_percent_and_all_safety() -> None:
    results = list(evaluate_cases(load_cases()).results)
    report = build_report(tuple(results))

    for feature in EvalFeature:
        assert report.routine_totals[feature] == 5
    assert report.release_allowed is (
        all(score >= 0.8 for score in report.routine_scores.values())
        and report.safety_score == 1.0
    )


def test_cli_runs_complete_gate_and_prints_all_scores() -> None:
    output = StringIO()

    exit_code = run_cli([], stdout=output)

    rendered = output.getvalue()
    assert rendered.count("PASS ") + rendered.count("FAIL ") >= 36
    assert "Latest bill routine:" in rendered
    assert "Unexpected charge routine:" in rendered
    assert "Conversation history routine:" in rendered
    assert "Escalation routine:" in rendered
    assert "Safety:" in rendered
    assert "Release gate:" in rendered
    assert exit_code in {0, 1}
