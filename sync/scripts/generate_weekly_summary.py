from __future__ import annotations

import subprocess
import sys


def main() -> None:
    subprocess.check_call([sys.executable, "scripts/generate_daily_summary.py", "--days", "7"])


if __name__ == "__main__":
    main()
