"""scanner / CLI の結合テスト（tmp リポジトリで完結・オフライン）。"""
import json

from plan_drift import scanner
from plan_drift.cli import main, render


def _make_repo(tmp_path):
    (tmp_path / "app.py").write_text(
        "import analytics\n\n\n"
        "def signup(user):\n"
        "    analytics.track(user.id, 'Signed Up', {'plan': 'pro'})\n"
        "    analytics.track(user.id, 'Mystery Event', {})\n"
        "    analytics.track('Product Viewed', {'product_id': 'p1', 'campaign': 'x'})\n"
    )
    (tmp_path / "tracking-plan.json").write_text(json.dumps({
        "events": [
            {"name": "Signed Up", "properties": {"plan": "string"}},
            {"name": "Product Viewed", "properties": {"product_id": "string"}},
            {"name": "Order Completed", "properties": {"total": "number"}},
        ]
    }))


def test_scan_reports_all_three_drift_types(tmp_path):
    _make_repo(tmp_path)
    plan_file = tmp_path / "tracking-plan.json"
    report = scanner.scan(tmp_path, plan_file)

    statuses = {f["status"] for f in report["findings"]}
    assert statuses == {"unexpected_event", "unimplemented_event", "property_mismatch"}

    by_status = {f["status"]: f for f in report["findings"]}
    assert by_status["unexpected_event"]["event"] == "Mystery Event"
    assert by_status["unimplemented_event"]["event"] == "Order Completed"
    assert "campaign" in by_status["property_mismatch"]["detail"]
    assert report["calls_total"] == 3
    assert report["ok_events"].get("Signed Up") == 1


def test_cli_main_json(tmp_path, capsys):
    _make_repo(tmp_path)
    rc = main(["--plan", str(tmp_path / "tracking-plan.json"), str(tmp_path), "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["calls_total"] == 3
    assert {f["status"] for f in data["findings"]} == {
        "unexpected_event", "unimplemented_event", "property_mismatch"}


def test_render_text_contains_marks(tmp_path, capsys):
    _make_repo(tmp_path)
    main(["--plan", str(tmp_path / "tracking-plan.json"), str(tmp_path)])
    out = capsys.readouterr().out
    assert "UNEXPECTED EVENT" in out
    assert "UNIMPLEMENTED EVENT" in out
    assert "PROPERTY MISMATCH" in out
    assert "summary:" in out
