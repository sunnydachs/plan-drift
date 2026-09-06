"""track_calls — Python ソースから analytics.track() 呼び出しを抽出する（純関数）。

認識するパターン（レシーバ名は問わない: analytics.track / segment.track /
self.client.track 等すべて .track で終わる呼び出し）:
  track("Signed Up", {...})                       # 位置引数（event, properties）
  track(user_id, "Signed Up", {...})              # segment python 形式
  track(event="Signed Up", properties={...})      # キーワード形式
  track("Signed Up", dict(plan="pro"))            # dict() 呼び出し（実データ e2e で発見）
  track(user, "temba.flow_start", contact_search) # 動的 properties → partial
動的要素は正直に partial/dynamic として記録する（推測しない）:
  - event が文字列リテラルでない → event_dynamic=True
  - properties が辞書リテラル / dict() 呼び出しでない → partial=True
"""
import ast
from pathlib import Path

# tests/ を除外する理由: トラッキングプランは本番コードの仕様であり、
# テストフィクスチャのイベント（foo_created 等のダミー）はノイズになるため
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__",
             "build", "dist", ".tox", ".mypy_cache", ".pytest_cache",
             "tests", "test"}


def _literal_str(node) -> str | None:
    if node is not None and isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _dict_keys(node) -> tuple:
    """ast.Dict のキー一覧（文字列リテラルのみ）。未対応要素があれば (None, False)。"""
    if node is None or not isinstance(node, ast.Dict):
        return None, False
    keys, complete = [], True
    for k, v in zip(node.keys, node.values):
        if k is None:            # **展開
            complete = False
            continue
        s = _literal_str(k)
        if s is None:            # 動的キー
            complete = False
            continue
        keys.append(s)
    return keys, complete


def _props_from(node) -> tuple:
    """properties 引数ノードからプロパティキーを抽出する（純関数）。

    対応: 辞書リテラル / dict(k=v, ...) 呼び出し（実データ e2e で発見した
    rapidpro 等の主要パターン。値が動的でも kw 名からキーは取れる）。
    返り値: (keys, complete) — 未対応形は (None, False) → partial 扱い。
    """
    if node is None:
        return None, False
    if isinstance(node, ast.Dict):
        return _dict_keys(node)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "dict"):
        keys = [kw.arg for kw in node.keywords if kw.arg is not None]
        complete = not any(kw.arg is None for kw in node.keywords)
        return keys, complete
    return None, False


def extract_track_calls(py_source: str, source_path: str = "<text>") -> list:
    """1 ソースから track() 呼び出しを抽出する（純関数）。

    返り値: [{event, event_dynamic, props, partial, file, line, receiver}]
    props は判明したキーのみ（partial の場合は不完全）。イベントが取れない
    呼び出しは event=None で返す（scanner が dynamic として扱う）。
    """
    out = []
    try:
        tree = ast.parse(py_source)
    except SyntaxError:
        return out

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "track"):
            continue
        if isinstance(func.value, ast.Name):
            recv_name = func.value.id
        elif isinstance(func.value, ast.Attribute):
            recv_name = func.value.attr
        else:
            recv_name = "..."

        pos = node.args
        event = None
        event_dynamic = False
        event_idx = None
        props, props_complete = {}, True

        # event: 位置引数の最初の文字列リテラル、または kw event=
        for i, a in enumerate(pos[:2]):
            s = _literal_str(a)
            if s is not None:
                event = s
                event_idx = i
                break
        kw_event = [kw.value for kw in node.keywords if kw.arg == "event"]
        if event is None and kw_event:
            event = _literal_str(kw_event[0])
            if event is None:
                event_dynamic = True
        elif event is None and any(kw.arg == "event" for kw in node.keywords):
            event_dynamic = True

        # properties: kw properties= または event の後ろの位置引数から取得。
        # 対応: 辞書リテラル / dict(k=v) 呼び出し（実データ e2e で発見した主要パターン）。
        # 非対応形（変数等）は partial。プロパティ引数自体が無ければ空で確定
        # （segment python の既定値が None であり、呼び出しとして成立するため）。
        kw_props = [kw.value for kw in node.keywords if kw.arg == "properties"]
        props_node = None
        props_arg_present = bool(kw_props)
        props_node = kw_props[0] if kw_props else None
        if not props_node:
            after_event = (event_idx + 1) if event_idx is not None else 0
            tail = pos[after_event:]
            for a in tail:
                if isinstance(a, (ast.Dict, ast.Call)):
                    props_node = a
                    props_arg_present = True
                    break
            if props_node is None and tail:
                props_arg_present = True   # 判定不能な位置引数（変数等）が properties 槽にある

        if props_node is not None:
            props_keys, props_complete = _props_from(props_node)
        elif props_arg_present:
            # プロパティ相当の引数はあるが解釈不能（変数等）→ partial
            props_keys, props_complete = None, False
        else:
            # プロパティ引数なし → 空で確定（segment python の既定値が None のため）
            props_keys, props_complete = [], True

        if props_keys is not None:
            props = {k: True for k in props_keys}
        else:
            props = {}

        has_dynamic_kw = any(kw.arg is None for kw in node.keywords)  # **kwargs
        out.append({
            "event": event,
            "event_dynamic": event_dynamic or event is None,
            "props": props,
            "partial": (not props_complete) or has_dynamic_kw or event is None,
            "file": source_path,
            "line": node.lineno,
            "receiver": recv_name,
        })
    return out


def find_python_files(root: Path, max_files: int = 3000) -> list:
    skip = {".git", ".venv", "venv", "node_modules", "__pycache__",
            "build", "dist", ".tox", ".mypy_cache", ".pytest_cache"}
    out = []
    for p in sorted(Path(root).rglob("*.py")):
        if any(part in skip for part in p.parts):
            continue
        # テストファイル（tests.py / test_*.py）のフィクスチャイベントは
        # plan 照合のノイズになるため除外する
        if p.name == "tests.py" or p.name.startswith("test_"):
            continue
        out.append(p)
        if len(out) >= max_files:
            break
    return out


def find_track_calls(root: Path, max_files: int = 3000) -> list:
    """リポジトリ全体から track() 呼び出しを収集する。"""
    calls = []
    for p in find_python_files(root, max_files):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        calls.extend(extract_track_calls(text, source_path=p.as_posix()))
    return calls
