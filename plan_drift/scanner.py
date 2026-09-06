"""scanner — Tracking Plan + リポジトリ走査から drift レポートを作る（オーケストレータ）。

読み取り専用。ファイルへの書き込みは一切行わない。
"""
from pathlib import Path

from plan_drift.compare import compare
from plan_drift.plan import load_plan
from plan_drift.track_calls import find_track_calls


def scan(root, plan_path) -> dict:
    """root を走査し、plan_path のトラッキングプランと照合する。

    返り値: {root, plan, files_scanned, calls_total, status_counts,
             findings, ok_events, dynamic, code_events}
    """
    root = Path(root)
    plan = load_plan(plan_path)
    calls = find_track_calls(root)

    res = compare(plan["events"], calls)
    return {
        "root": str(root),
        "plan_events": {name: {"required": p["required"], "all": p["all"]}
                        for name, p in plan["events"].items()},
        "calls_total": len(calls),
        "status_counts": res["status_counts"],
        "findings": res["findings"],
        "ok_events": res["ok_events"],
        "dynamic": res["dynamic"],
        "dynamic_count": res["dynamic_count"],
        "code_events": res["code_events"],
    }
