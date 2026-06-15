from __future__ import annotations

import subprocess
import sys


if __name__ == "__main__":
    subprocess.check_call([sys.executable, "scripts/sync_ghl.py", "--entity", "contactos", *sys.argv[1:]])
