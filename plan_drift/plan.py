"""plan — Tracking Plan JSON の読み込みと正規化（純関数）。

対応フォーマット（Segment Protocols に近い簡易スキーマ）:
{
  "events": [
    {
      "name": "Signed Up",
      "properties": {
        "plan": "string",                                # 型のみ（任意扱い）
        "url": {"type": "string", "required": true}      # 型 + 必須フラグ
      }
    }
  ]
}

正規化後: events: {name: {"required": [必須プロパティ], "all": [全プロパティ]}}
- properties が無い/空のイベントは「宣言プロパティなし」（コード側で
  任意のキーを使うと undeclared になる）
"""
import json


def load_plan(path) -> dict:
    return normalize(json.loads(open(path, encoding="utf-8").read()))


def normalize(data: dict) -> dict:
    """Tracking Plan JSON を正規化する（純関数）。"""
    if not isinstance(data, dict) or not isinstance(data.get("events"), list):
        raise ValueError("tracking plan must be {'events': [{'name': ..., 'properties': {...}}]}")

    events = {}
    for i, ev in enumerate(data["events"]):
        if not isinstance(ev, dict) or not ev.get("name"):
            raise ValueError(f"events[{i}] must have a 'name'")
        name = ev["name"]
        if name in events:
            raise ValueError(f"duplicate event name: {name!r}")
        props_raw = ev.get("properties") or {}
        if not isinstance(props_raw, dict):
            raise ValueError(f"event {name!r}: properties must be an object")
        required, all_keys = [], []
        for key, val in props_raw.items():
            all_keys.append(key)
            req = False
            if isinstance(val, dict):
                req = bool(val.get("required", False))
            if req:
                required.append(key)
        events[name] = {"required": required, "all": all_keys}

    return {"events": events}
