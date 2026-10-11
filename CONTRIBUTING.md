# Contributing to EROICA

Thanks for helping make browsers quieter. This project takes a deliberately
small surface: no runtime dependencies, no clever abstractions, and every
setting explained in a comment.

## Development setup

```bash
git clone https://github.com/BeethovenDev/eroica.git
cd eroica
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Quality gates

All of these must pass before a pull request is merged:

```bash
ruff check .
mypy
pytest
```

`ruff` and `mypy` are configured in `pyproject.toml`; `mypy` runs in **strict**
mode. New code must be fully type-annotated.

## Adding a setting

1. Find the movement that owns the concern (`symphonies/*.py`).
2. Append a `FirefoxPref` or `ChromiumFlag` with the correct **minimum tier**.
3. Add a one-line `note` explaining *why* the setting exists.
4. If it is a new Firefox pref, the audit and tests will pick it up
   automatically; run `pytest`.

## Adding a movement

1. Create `src/eroica/symphonies/<name>.py` exporting a single `Movement`.
2. Register it in the `SYMPHONIES` tuple in `symphonies/__init__.py`.
3. Give it a Beethoven work number and a nickname, in keeping with the theme.

## Adding a browser

* Add an entry to `browsers.CATALOG`.
* For Chromium-family browsers, also add a `_CHROMIUM_USER_DATA` entry in
  `paths.py`.

## Pull request checklist

- [ ] `ruff check .`, `mypy` and `pytest` are green.
- [ ] New behaviour is covered by a test.
- [ ] Public functions have docstrings; settings have `note=` explanations.
- [ ] `CHANGELOG.md` has an entry under *Unreleased*.
- [ ] The change is strictly defensive (see below).

## Scope and ethics

EROICA is a defensive privacy tool. Contributions that bypass authentication,
defeat CAPTCHAs, evade access controls, or otherwise enable abuse will be
declined regardless of quality. When in doubt, open an issue first.

## Commit messages

Conventional-ish and imperative: `feat(fate): disable Reporting API`,
`fix(cli): keep audit exit code under --json`, `docs: clarify threat model`.

## Code of conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
