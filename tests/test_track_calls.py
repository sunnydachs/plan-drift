from plan_drift.track_calls import extract_track_calls


def test_positional_event_and_props():
    src = "analytics.track('Signed Up', {'plan': 'pro'})\n"
    calls = extract_track_calls(src, "a.py")
    assert len(calls) == 1
    assert calls[0]["event"] == "Signed Up"
    assert calls[0]["props"] == {"plan": True}
    assert calls[0]["partial"] is False
    assert calls[0]["line"] == 1


def test_segment_python_style_positional():
    src = "analytics.track(user_id, 'Product Viewed', {'product_id': pid})\n"
    calls = extract_track_calls(src)
    assert calls[0]["event"] == "Product Viewed"
    assert calls[0]["props"] == {"product_id": True}


def test_keyword_style():
    src = "analytics.track(event='Signed Up', properties={'plan': 'free'})\n"
    calls = extract_track_calls(src)
    assert calls[0]["event"] == "Signed Up"
    assert calls[0]["props"] == {"plan": True}


def test_dynamic_event_is_flagged():
    src = "analytics.track(event_name, {'plan': 'free'})\n"
    calls = extract_track_calls(src)
    assert calls[0]["event"] is None
    assert calls[0]["event_dynamic"] is True
    assert calls[0]["partial"] is True


def test_partial_properties_when_dict_is_variable():
    src = "analytics.track('Signed Up', props)\n"
    calls = extract_track_calls(src)
    assert calls[0]["props"] == {}
    assert calls[0]["partial"] is True


def test_partial_when_kwargs_expansion():
    src = "analytics.track('Signed Up', **props)\n"
    calls = extract_track_calls(src)
    assert calls[0]["partial"] is True


def test_receiver_variants_match():
    for src in ("self.client.track('E', {})\n",
                "segment.track('E', {})\n",
                "obj.analytics.track('E', {})\n"):
        calls = extract_track_calls(src)
        assert len(calls) == 1
        assert calls[0]["receiver"] in ("self", "client", "analytics", "segment")


def test_non_track_calls_ignored():
    src = "analytics.page('Home')\ntrack_something('E', {})\n"
    assert extract_track_calls(src) == []


def test_multiple_calls_with_lines():
    src = "analytics.track('A', {})\nanalytics.track('B', {})\n"
    calls = extract_track_calls(src, "m.py")
    assert [c["event"] for c in calls] == ["A", "B"]
    assert [c["line"] for c in calls] == [1, 2]


# ── dict() 呼び出し形式（実データ e2e で発見したパターン） ──

def test_dict_call_properties():
    """dict(k=v, ...) 形式の properties からキーを抽出する（rapidpro 形式）。"""
    src = "analytics.track(user, 'temba.flow_created', dict(name=name, uuid=flow_uuid))\n"
    calls = extract_track_calls(src)
    assert calls[0]["event"] == "temba.flow_created"
    assert calls[0]["props"] == {"name": True, "uuid": True}
    assert calls[0]["partial"] is False


def test_dict_call_via_kw_properties():
    src = "analytics.track(user, 'temba.org_signup', properties=dict(org=org_name))\n"
    calls = extract_track_calls(src)
    assert calls[0]["props"] == {"org": True}
    assert calls[0]["partial"] is False


def test_dict_call_with_dynamic_values_still_extracts_keys():
    """値が動的（len() 等）でも kw 名からキーは取れる。"""
    src = "analytics.track(user, 'temba.broadcast_created', dict(contacts=len(ids), groups=0, urns=0))\n"
    calls = extract_track_calls(src)
    assert calls[0]["props"] == {"contacts": True, "groups": True, "urns": True}
    assert calls[0]["partial"] is False


def test_no_properties_argument_is_complete_empty():
    """properties 引数自体が無い呼び出しは空で確定（partial にしない）。"""
    src = "analytics.track(self.request.user, 'temba.contact_exported')\n"
    calls = extract_track_calls(src)
    assert calls[0]["props"] == {}
    assert calls[0]["partial"] is False


def test_variable_properties_after_event_is_partial():
    """event の後ろに変数がある場合は partial（中身を推測しない）。"""
    src = "analytics.track(self.request.user, 'temba.flow_start', contact_search)\n"
    calls = extract_track_calls(src)
    assert calls[0]["partial"] is True
