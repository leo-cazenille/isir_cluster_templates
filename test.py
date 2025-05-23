#!/usr/bin/env python3
"""
Quick-n-dirty environment probe for a SLURM node.

New behaviour
  • Tries to build & store a random-data DataFrame **only if**
    numpy, pandas *and* pyarrow are available.
  • If any of those packages are missing, it prints a warning and
    skips the DataFrame section, so the rest of the tests still run.

Existing features
  • CPU cores & total memory
  • Python interpreter version
  • /etc/issue contents
  • pip3 list
  • Optional DataFrame ➜ results/probe_results.feather
  • Idles so total job time ≈3 min
"""

import os
import platform
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Optional imports (handled gracefully)
# ---------------------------------------------------------------------------
try:
    import numpy as np
except ImportError:      # pragma: no cover
    np = None

try:
    import pandas as pd
except ImportError:      # pragma: no cover
    pd = None

# pyarrow is only needed for Feather I/O; check later on demand
PYARROW_AVAILABLE = False
if pd is not None:
    try:
        import pyarrow  # noqa: F401
        PYARROW_AVAILABLE = True
    except ImportError:  # pragma: no cover
        pass

START = time.time()
TARGET_SECONDS = 20          # ≈ 3 minutes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cpu_count():
    """Cores allotted by SLURM (if defined) or Python’s view."""
    slurm_cores = (
        os.getenv("SLURM_CPUS_ON_NODE")
        or os.getenv("SLURM_CPUS_PER_TASK")
        or os.getenv("SLURM_NPROCS")
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
                    kib = int(line.split()[1])  # KiB
                    return kib / 2**20
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
    """Return the contents of /etc/issue (Linux banner) if readable."""
    p = Path("/etc/issue")
    if p.is_file():
        try:
            return p.read_text(errors="replace").strip()
        except Exception as exc:
            return f"(Could not read /etc/issue: {exc})"
    return "(No /etc/issue found on this system)"


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def generate_dataframe():
    """Return a random-value pandas DataFrame or None if deps are missing."""
    if np is None or pd is None:
        print(
            "# DataFrame generation skipped – numpy and/or pandas not installed."
        )
        return None
    df = pd.DataFrame(
        {
            "metric1": np.random.random(100),
            "metric2": np.random.random(100),
        }
    )
    return df


def save_dataframe(df: "pd.DataFrame", outdir: Path):
    """Save DataFrame as Feather if pyarrow present, else as CSV."""
    if PYARROW_AVAILABLE:
        fpath = outdir / "probe_results.feather"
        df.to_feather(fpath)
    else:
        fpath = outdir / "probe_results.csv"
        df.to_csv(fpath, index=False)
    print(f"Saved DataFrame to {fpath.resolve()}")


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
    print(sys.version.replace("\n", "\n                               "))
    print()

    # /etc/issue -------------------------------------------------------------
    print("# /etc/issue contents\n")
    print(read_issue())
    print()

    # Packages ---------------------------------------------------------------
    print("# Python packages (pip3 list)\n")
    print(pip_list())

    # -----------------------------------------------------------------------
    # Optional DataFrame section
    # -----------------------------------------------------------------------
    df = generate_dataframe()
    if df is not None:
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        save_dataframe(df, results_dir)

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
