# Architecture

EROICA is a thin, dependency-free pipeline: **movements describe settings →
tiers filter them → a plan is resolved → a strategy writes it to disk**.

```
src/eroica/
├── __init__.py        package metadata and banner
├── __main__.py        `python -m eroica`
├── cli.py             argparse CLI, one function per subcommand
├── config.py          Tier enum, Config dataclass, JSON persistence
├── paths.py           cross-OS path resolution
├── browsers.py        browser catalogue + detection
├── profiles.py        isolated profile lifecycle (.eroica.json sidecar)
├── ua.py              deterministic User-Agent pool
├── symphonies/        the hardening movements
│   ├── base.py        FirefoxPref, ChromiumFlag, Movement
│   ├── first.py       I  · foundations
│   ├── eroica.py      III· anti-fingerprinting
│   ├── fate.py        V  · trackers & telemetry
│   ├── pastoral.py    VI · storage hygiene
│   ├── choral.py      IX · transport security
│   └── __init__.py    registry + aggregation helpers
├── hardening.py       plan resolution and the two write strategies
├── userjs.py          user.js render/merge/backup (idempotent markers)
├── flags.py           Chromium argument-vector builder
├── audit.py           read-only drift detection
└── log.py             stderr logging (text or JSON lines)
```

## Data flow

1. **Describe.** Each movement declares `FirefoxPref` and `ChromiumFlag` objects,
   each tagged with the minimum `Tier` at which it applies.
2. **Filter.** `collect_prefs(tier)` / `collect_flags(tier)` gather settings that
   apply at or below the requested tier. Later movements win on duplicate keys.
3. **Resolve.** `hardening.build_plan(...)` folds in the DoH endpoint and the
   pinned User-Agent, and strips DoH directives when the resolver is `system`.
4. **Write.**
   * *Mozilla* → `userjs.write_user_js` renders the plan into a marked block,
     merging with any existing `user.js` and backing it up first.
   * *Chromium* → `flags.build_args` produces the argument vector, persisted to
     `<profile>/.eroica/flags.json`.
5. **Record.** The profile sidecar (`.eroica.json`) is updated with the tier, UA
   and DoH endpoint so later runs are reproducible.

## Design principles

* **Additive tiers.** `STANDARD ≤ STRICT ≤ PARANOID`; a tier never removes a
  setting another tier added.
* **Idempotent writes.** Re-running `harden` replaces only EROICA's marked block.
* **Read-only audit.** `audit` never mutates anything; it is safe in CI.
* **No dependencies.** The standard library is the whole supply chain.
* **Testable core.** Every module is import-safe and side-effect-free at import.

## Extension points

* **Add a setting** — append a `FirefoxPref` or `ChromiumFlag` to the relevant
  movement, choose a `Tier`, and add a one-line `note`.
* **Add a movement** — create `symphonies/<name>.py` exporting one `Movement`,
  then register it in `symphonies/__init__.py`'s `SYMPHONIES` tuple.
* **Add a browser** — add an entry to `browsers.CATALOG` (and, for
  Chromium-family browsers, a `_CHROMIUM_USER_DATA` entry in `paths.py`).
