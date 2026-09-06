"""compare — Tracking Plan と実装呼び出しを比較し判定する（純関数）。

検出する3種の drift（元スコープどおり）:
  unexpected_event    — 計画に無いイベントが実装されている
  unimplemented_event — 計画済みだが実装されていない
  property_mismatch   — イベント名は一致するがプロパティキーが計画と異なる
                        （undeclared_property / missing_required の2種の詳細つき）

情報扱い（drift には数えない）:
  dynamic — イベント名・プロパティが静的に解決できない呼び出し
            （推測せず「確認が必要」として報告する）
"""
from collections import Counter


def compare(plan_events: dict, calls: list) -> dict:
    """plan_events（plan.normalize の出力）と track 呼び出しを比較する（純関数）。

    返り値: {status_counts, findings: [{event, file, line, status, detail}],
             ok_events: {name: calls}, dynamic_count}
    findings の status: unexpected_event | unimplemented_event |
                        property_mismatch | dynamic
    """
    code_events = Counter()
    props_by_event = {}
    dynamic = []
    ok_events = {}

    for c in calls:
        ev = c["event"]
        if ev is None or c["event_dynamic"]:
            dynamic.append(c)
            continue
        code_events[ev] += 1
        if c["partial"]:
            # イベント名は既知だがプロパティが静的に解決できない →
            # 実装済みとして数えつつ、プロパティ照合は手動確認リストに回す
            dynamic.append(c)
            continue
        props_by_event.setdefault(ev, []).append(c)

    findings = []

    # 1) 計画に無いイベントが実装されている
    for ev in sorted(code_events):
        if ev not in plan_events:
            locs = ", ".join(f"{c['file']}:{c['line']}" for c in props_by_event.get(ev, [])[:3])
            findings.append({
                "event": ev,
                "file": (props_by_event.get(ev) or [{"file": None}])[0]["file"],
                "line": (props_by_event.get(ev) or [{"line": None}])[0]["line"],
                "status": "unexpected_event",
                "detail": f"event {ev!r} is implemented ({code_events[ev]} call(s)) "
                          f"but not in the tracking plan — {locs}",
            })

    # 2) 計画済みだが実装されていない
    for ev in sorted(plan_events):
        if ev not in code_events:
            findings.append({
                "event": ev, "file": None, "line": None,
                "status": "unimplemented_event",
                "detail": f"event {ev!r} is in the tracking plan but no track() call "
                          f"was found in the codebase",
            })

    # 3) プロパティ不一致（イベント名が一致するもの）
    for ev in sorted(set(plan_events) & set(code_events)):
        plan_p = plan_events[ev]
        plan_all = set(plan_p["all"])
        plan_req = set(plan_p["required"])
        calls = props_by_event.get(ev, [])
        for c in calls:
            if c["partial"]:
                continue  # 静的に解決できない呼び出しは dynamic 扱いで別途集計
            code_keys = set(c["props"].keys())
            undeclared = sorted(code_keys - plan_all)
            missing_required = sorted(plan_req - code_keys)
            if not undeclared and not missing_required:
                ok_events.setdefault(ev, []).append(c)
                continue
            bits = []
            if undeclared:
                bits.append(f"undeclared property: {', '.join(undeclared)}")
            if missing_required:
                bits.append(f"missing required property: {', '.join(missing_required)}")
            findings.append({
                "event": ev, "file": c["file"], "line": c["line"],
                "status": "property_mismatch",
                "detail": f"event {ev!r}: " + "; ".join(bits),
            })

    findings.sort(key=lambda f: (f["status"], f["event"], f["file"] or "", f["line"] or 0))
    status_counts = dict(Counter(f["status"] for f in findings))
    return {
        "status_counts": status_counts,
        "findings": findings,
        "ok_events": {k: len(v) for k, v in sorted(ok_events.items())},
        "dynamic_count": len(dynamic),
        "dynamic": [{"file": c["file"], "line": c["line"],
                     "detail": "event/properties not statically resolvable — manual check needed"}
                    for c in dynamic],
        "code_events": dict(code_events),
    }
