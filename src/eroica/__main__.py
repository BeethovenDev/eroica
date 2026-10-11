"""Enable ``python -m eroica``."""

from __future__ import annotations

from eroica.cli import main

if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main())
