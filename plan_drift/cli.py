"""cli — plan-drift コマンドライン入口（読み取り専用・dry-run のみ）。

usage:
  plan-drift --plan tracking-plan.json [ROOT]    # ROOT 内の track() を照合（既定: .）
  plan-drift --plan tracking-plan.json . --json  # 機械可読出力
"""
import argparse
import json

from plan_drift import scanner

MARK = {
    "unexpected_event": "➕ UNEXPECTED EVENT",
    "unimplemented_event": "⬜ UNIMPLEMENTED EVENT",
    "property_mismatch": "⚠️ PROPERTY MISMATCH",
    "dynamic": "· DYNAMIC (manual check)",
}


def render(report: dict, json_output: bool) -> str:
    if json_output:
        return json.dumps(report, ensure_ascii=False, indent=2)

    lines = [
        f"plan-drift — scanned {report['root']}",
        f"  tracking plan events: {len(report['plan_events'])} | "
        f"track() calls found: {report['calls_total']} "
        f"(dynamic: {report['dynamic_count']})",
        "",
    ]
    if not report["findings"]:
        lines.append("no drift detected: plan and implementation are aligned.")
    for f in report["findings"]:
        loc = f"{f['file']}:{f['line']}" if f.get("file") else "(codebase)"
        lines.append(f"{loc}  {MARK.get(f['status'], f['status'])}")
        lines.append(f"    {f['detail']}")
    lines.append("")
    if report["ok_events"]:
        lines.append("ok (plan & implementation aligned):")
        for ev, n in report["ok_events"].items():
            lines.append(f"  ✓ {ev} ({n} call(s))")
    lines.append("")
    lines.append(f"summary: {json.dumps(report['status_counts'], ensure_ascii=False)} "
                 f"| dynamic: {report['dynamic_count']}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="plan-drift",
        description="Detect drift between an analytics tracking plan and the implementation. Read-only.")
    ap.add_argument("--plan", required=True, help="tracking plan JSON file")
    ap.add_argument("root", nargs="?", default=".", help="repository root (default: .)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    report = scanner.scan(args.root, args.plan)
    print(render(report, json_output=args.json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
