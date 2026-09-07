# plan-drift

**Detect drift between an analytics tracking plan and the actual implementation. Read-only, deterministic, no LLM.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-31%20passing-brightgreen.svg)](tests/)

`plan-drift` lints your codebase against an analytics **tracking plan**: it finds every `analytics.track(...)` call, and reports where the implementation and the plan disagree.

- ➕ **UNEXPECTED EVENT** — implemented in code, but not in the tracking plan
- ⬜ **UNIMPLEMENTED EVENT** — in the tracking plan, but no `track()` call found
- ⚠️ **PROPERTY MISMATCH** — event name matches, but properties diverge (undeclared / missing required)
- · **DYNAMIC** — event name or properties aren't statically resolvable (manual check needed)

Everything is **deterministic** — `ast` parsing and set comparison only, no LLM, no network. The tool is **read-only**: it never modifies your files.

## Status: practice/portfolio project — honest competition landscape

This tool was inspired by a recurring pain observed in a personal research pipeline: analytics tracking implementations decay — events get renamed, properties drift, new calls bypass the plan — and nothing local catches it.

**Honest competition landscape** (no claim of a blue ocean):

| Existing solution | Approach | Difference |
|---|---|---|
| Segment Protocols / Avo | Hosted paid SaaS with plan enforcement | plan-drift is free, local, and read-only — no vendor, no CI-side credentials |
| Segment Typewriter (OSS, MIT) | *Generates* typed helpers from a plan; officially in maintenance mode | plan-drift *lints existing implementation code* instead of generating new code |
| AI-agent approaches (e.g. skill-based generators) | Generation via LLM | plan-drift is deterministic `ast` analysis — same input, same report, always |

## Tracking plan format

A simple JSON file (close to Segment Protocols, minus the machinery):

```json
{
  "events": [
    {
      "name": "Signed Up",
      "properties": {
        "plan": "string",
        "source": {"type": "string", "required": true}
      }
    },
    {"name": "App Opened"}
  ]
}
```

A property value is a type string, or an object with `type` and `required`. Properties without `required: true` may be omitted by callers (README examples routinely omit optional args).

## Install

```bash
pip install git+https://github.com/sunnydachs/plan-drift.git
```

## Usage

```bash
plan-drift --plan tracking-plan.json            # scan current repository (read-only)
plan-drift --plan tracking-plan.json src/ --json
```

Example output:

```
plan-drift — scanned /home/dev/myproject
  tracking plan events: 3 | track() calls found: 3 (dynamic: 0)
app.py:5  ⚠️ PROPERTY MISMATCH
    event 'Signed Up': undeclared property: campaign
app.py:6  ➕ UNEXPECTED EVENT
    event 'Mystery Event' is implemented (1 call(s)) but not in the tracking plan — app.py:6
```

## What gets recognized

```python
analytics.track("Signed Up", {"plan": "pro"})                 # ✓ event + properties
analytics.track(user_id, "Product Viewed", {...})             # ✓ segment python style
analytics.track(event="Signed Up", properties={...})          # ✓ keyword style
analytics.track(user, "temba.flow_created", dict(name=name))  # ✓ dict() call style
self.client.track("App Opened")                               # ✓ any receiver ending in .track
analytics.track(user, event_name, props)                      # · dynamic — reported, not guessed
```

Test files (`tests.py`, `test_*.py`) are excluded — fixture events are plan noise.

## Known limitations

- **Dynamic events and properties are reported, not resolved.** `track(event_name, props)` can't be verified statically — it's listed as `dynamic` for manual review rather than guessed.
- **Python only** for now. (JavaScript would need a JS parser — tracked for a future version.)
- **Read-only by design.** No autofix, no plan generation. Pair it with your own review process.
- Property *values* are not type-checked (keys only) — the plan's `type` field is accepted but not enforced.
- Calling wrappers that rename events internally (e.g. `track_signup(user)`) are invisible — lint the layer that calls `.track()` directly.

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q   # 31 tests, fully offline
```

Validated against a real open-source repository using the segment Python library: a tracking plan frozen from the codebase produced **zero findings** (correct no-drift verdict), and two injected plan drifts (a removed event, a removed declared property) were both detected.

## Provenance

Inspired by a recurring pain observed in a personal research pipeline: tracking implementations decay silently — events get renamed, new calls bypass the plan, and nothing local catches it. This repository is an independent, general-purpose implementation.

This is the third tool in a small **"drift" family**: [doc-drift](https://github.com/sunnydachs/doc-drift) checks Markdown code examples against the codebase; plan-drift checks an analytics tracking plan against the code. Same design principles throughout: deterministic, read-only, dry-run by default.

## License

[MIT](LICENSE)
