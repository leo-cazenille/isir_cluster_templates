#!/usr/bin/env python3

#!/usr/bin/env python3
"""
Quick-n-dirty environment probe for a SLURM node.

Reports
  • CPU cores available
  • Total RAM visible to the process
  • Python interpreter version
  • Contents of /etc/issue
  • Installed Python packages (pip3 list)

Then idles long enough so that the job’s wall-clock time is ~3 minutes,
useful for testing accounting and node allocation.
"""

import os
import platform
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

START = time.time()
TARGET_SECONDS = 30 # 180               # ≈ 3 minutes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cpu_count():
    """Return the core count allotted by SLURM (if defined) or Python’s view."""
    slurm_cores = (
        os.getenv("SLURM_CPUS_ON_NODE") or
        os.getenv("SLURM_CPUS_PER_TASK") or
        os.getenv("SLURM_NPROCS")
    )
    return int(slurm_cores) if slurm_cores else os.cpu_count()


def total_memory_gib():
    """Total RAM visible to this process, in GiB."""
    try:
        import psutil
        return psutil.virtual_memory().total / 2**30
    except ImportError:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    kib = int(line.split()[1])          # value is KiB
                    return kib / 2**20
    # Fallback—should not reach here on Linux
    return None


def pip_list():
    """Return the pip package list as a string."""
    try:
        return subprocess.check_output(
            ["pip3", "list", "--format=columns"], text=True
        )
    except Exception as exc:
        return f"(pip3 list failed: {exc})"


def read_issue():
    """Return the contents of /etc/issue (Linux distro banner) if readable."""
    issue_path = Path("/etc/issue")
    if issue_path.is_file():
        try:
            return issue_path.read_text(errors="replace").strip()
        except Exception as exc:
            return f"(Could not read /etc/issue: {exc})"
    return "(No /etc/issue found on this system)"


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def main():
    print("# SLURM environment probe\n")

    # CPU and memory ---------------------------------------------------------
    print(f"Allocated CPU cores        : {cpu_count()}")
    mem_gib = total_memory_gib()
    print(f"Total visible memory       : {mem_gib:.2f} GiB\n")

    # Python version ---------------------------------------------------------
    print("# Python interpreter\n")
    print(f"Short version              : {platform.python_version()}")
    print("Full sys.version banner    :")
    print(sys.version.replace("\n", "\n                               "))  # indent lines
    print()

    # /etc/issue -------------------------------------------------------------
    print("# /etc/issue contents\n")
    print(read_issue())
    print()

    # Packages ---------------------------------------------------------------
    print("# Python packages (pip3 list)\n")
    print(pip_list())

    # Wait so the job lasts ~3 minutes --------------------------------------
    elapsed = time.time() - START
    remaining = TARGET_SECONDS - elapsed
    if remaining > 0:
        print(
            f"\nIdling for {timedelta(seconds=int(remaining))} "
            "to reach ≈3 minutes wall-clock…"
        )
        time.sleep(remaining)

    print("\nDone. Total runtime:", timedelta(seconds=int(time.time() - START)))


if __name__ == "__main__":
    main()

# MODELINE "{{{1
# vim:expandtab:softtabstop=4:shiftwidth=4:fileencoding=utf-8
# vim:foldmethod=marker
