from plan_drift.compare import compare


def _plan(events: dict) -> dict:
    """{name: (required_list, all_list)} → 正規化済み plan events 形式に変換。"""
    return {name: {"required": req, "all": allk}
            for name, (req, allk) in events.items()}


def _call(event, props=None, partial=False, file="a.py", line=1,
          event_dynamic=False, receiver="analytics"):
    return {"event": event, "props": props or {}, "partial": partial,
            "file": file, "line": line, "event_dynamic": event_dynamic,
            "receiver": receiver}


PLAN = _plan({
    "Signed Up": (["plan"], ["plan", "source"]),
    "Product Viewed": (["product_id"], ["product_id", "price"]),
})


def test_ok_when_event_and_properties_align():
    calls = [_call("Signed Up", {"plan": "pro", "source": "web"}),
             _call("Product Viewed", {"product_id": "p1"})]
    r = compare(PLAN, calls)
    assert r["findings"] == []
    assert r["status_counts"] == {}
    assert r["ok_events"] == {"Signed Up": 1, "Product Viewed": 1}


def test_unexpected_event():
    calls = [_call("Mystery Event", {"x": "y"}, line=3)]
    r = compare(PLAN, calls)
    assert r["findings"][0]["status"] == "unexpected_event"
    assert "not in the tracking plan" in r["findings"][0]["detail"]
    assert "a.py:3" in r["findings"][0]["detail"]


def test_unimplemented_event():
    r = compare(PLAN, [_call("Signed Up", {"plan": "pro"})])
    un = [f for f in r["findings"] if f["status"] == "unimplemented_event"]
    assert len(un) == 1
    assert un[0]["event"] == "Product Viewed"
    assert un[0]["file"] is None


def test_property_mismatch_undeclared():
    calls = [_call("Signed Up", {"plan": "pro", "campaign": "black-friday"})]
    r = compare(PLAN, calls)
    f = [x for x in r["findings"] if x["status"] == "property_mismatch"][0]
    assert "undeclared property: campaign" in f["detail"]


def test_property_mismatch_missing_required():
    calls = [_call("Signed Up", {"source": "web"})]   # 必須の plan が無い
    r = compare(PLAN, calls)
    f = [x for x in r["findings"] if x["status"] == "property_mismatch"][0]
    assert "missing required property: plan" in f["detail"]


def test_optional_omitted_is_ok():
    calls = [_call("Signed Up", {"plan": "pro"}),
             _call("Product Viewed", {"product_id": "p1"})]  # price は任意
    r = compare(PLAN, calls)
    assert r["findings"] == []
    assert r["ok_events"]["Signed Up"] == 1


def test_dynamic_calls_are_informational_only():
    calls = [_call(None, {"plan": "pro"}, partial=True),       # 動的イベント
             _call("Signed Up", {"plan": "pro"}, partial=True)]  # 動的プロパティ
    r = compare(PLAN, calls)
    # 動的呼び出しからは drift を出さない（誤検知防止）
    # ただし静的に観測されない Product Viewed は unimplemented として残る
    #（動的呼び出しがそれかもしれないため、dynamic として別途報告される）
    assert [f["status"] for f in r["findings"]] == ["unimplemented_event"]
    assert r["findings"][0]["event"] == "Product Viewed"
    assert r["dynamic_count"] == 2


def test_sorted_by_status_then_event():
    calls = [_call("Product Viewed", {"product_id": "p1", "extra": 1}),
             _call("Mystery Event", {})]
    r = compare(PLAN, calls)
    statuses = [f["status"] for f in r["findings"]]
    assert statuses == sorted(statuses)


def test_empty_plan_makes_everything_unexpected():
    r = compare({}, [_call("Signed Up", {"plan": "pro"})])
    assert r["findings"][0]["status"] == "unexpected_event"
