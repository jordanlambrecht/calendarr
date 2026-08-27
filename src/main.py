# src/main.py
"""Back compat shim so documented `docker exec calendarr python /app/src/main.py`
still triggers a one shot run."""

from calendarr.__main__ import run_single

if __name__ == "__main__":
    raise SystemExit(run_single())
