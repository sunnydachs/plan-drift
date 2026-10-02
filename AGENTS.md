# Working agreement for this repository

Short rules for anyone — human or agent — changing `plan-drift`.

## What this tool is

`plan-drift` lints a codebase against an analytics tracking plan: it finds every
`analytics.track(...)` call and reports where the implementation and the plan
disagree (unexpected event, unimplemented event, property mismatch, dynamic).
It is **read-only** and **deterministic**.

## Ground rules

- **Read-only.** The tool reports drift; it never edits the code or the plan.
- **No network, no LLM.** A lint run must be reproducible offline.
- **Tests come with the change.** `python -m pytest -q` must pass, and each
  reported category needs a fixture that triggers it.
- **No secrets in Git**, and no absolute paths in code, tests or docs — a clone
  must run anywhere.
- **Do not bypass the secret scan.** `git commit --no-verify` is never a fix for a
  gitleaks hit; rotate the credential and rewrite the commit.
- **The README is a promise.** Every documented command must work on a fresh
  clone, and a badge must point at CI rather than hardcode a test count.

## Checks that must pass

```
pip install -e ".[dev]"
python -m pytest -q
```
