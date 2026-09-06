import pytest

from plan_drift.plan import load_plan, normalize


def test_normalize_simple_types():
    p = normalize({"events": [{"name": "Signed Up",
                               "properties": {"plan": "string"}}]})
    assert p["events"]["Signed Up"] == {"required": [], "all": ["plan"]}


def test_normalize_required_flag():
    p = normalize({"events": [{"name": "Product Viewed",
                               "properties": {"product_id": {"type": "string", "required": True},
                                              "currency": {"type": "string"}}}]})
    ev = p["events"]["Product Viewed"]
    assert ev["required"] == ["product_id"]
    assert ev["all"] == ["product_id", "currency"]


def test_normalize_event_without_properties():
    p = normalize({"events": [{"name": "App Opened"}]})
    assert p["events"]["App Opened"] == {"required": [], "all": []}


def test_normalize_rejects_bad_input():
    with pytest.raises(ValueError):
        normalize({"nope": 1})
    with pytest.raises(ValueError):
        normalize({"events": [{"properties": {}}]})       # name 無し
    with pytest.raises(ValueError):
        normalize({"events": [{"name": "A"}, {"name": "A"}]})  # 重複


def test_load_plan_from_file(tmp_path):
    f = tmp_path / "plan.json"
    f.write_text('{"events": [{"name": "Signed Up", "properties": {"plan": "string"}}]}')
    p = load_plan(f)
    assert "Signed Up" in p["events"]
