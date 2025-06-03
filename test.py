#!/usr/bin/env python3
"""
SLURM environment probe.

If numpy and pandas are installed, generate also a dataframe containing random distributions.
If not, the script can still be launched, but it won't generate any dataframe.

On the ISIR cluster, numpy and pandas are not installed in the barebone cluster computers,
 so you need to launch this script in a singularity/apptainer container
 e.g. with:
    sbatch test_job_singularity.slurm
"""

import argparse
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

def parse_cli() -> str:
    """Return the run-name supplied on the command line (or a default)."""
    parser = argparse.ArgumentParser(
        description="SLURM probe – requires a run-name/ID for output files."
    )
    parser.add_argument(
        "run_name",
        nargs="?",
        default=None,
        help="Run identifier (e.g. $SLURM_JOB_ID); added to results filenames.",
    )
    args = parser.parse_args()
    # Fallback if nothing was given on the CLI
    return args.run_name or os.getenv("SLURM_JOB_ID", "local")


def cpu_count():
    slurm_cores = (
        os.getenv("SLURM_CPUS_ON_NODE")
        or os.getenv("SLURM_CPUS_PER_TASK")
        or os.getenv("SLURM_NPROCS")
    )
    return int(slurm_cores) if slurm_cores else os.cpu_count()


def total_memory_gib():
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
    try:
        return subprocess.check_output(["pip3", "list", "--format=columns"], text=True)
    except Exception as exc:
        return f"(pip3 list failed: {exc})"


def read_issue():
    p = Path("/etc/issue")
    if p.is_file():
        try:
            return p.read_text(errors="replace").strip()
        except Exception as exc:
            return f"(Could not read /etc/issue: {exc})"
    return "(No /etc/issue found on this system)"


# ---------------------------------------------------------------------------
# Data-frame helpers
# ---------------------------------------------------------------------------

def generate_dataframe():
    if np is None or pd is None:
        print("# DataFrame generation skipped – numpy and/or pandas not installed.")
        return None
    return pd.DataFrame(
        {"metric1": np.random.random(100), "metric2": np.random.random(100)}
    )


def save_dataframe(df: "pd.DataFrame", outdir: Path, run_name: str):
    suffix = ".feather" if PYARROW_AVAILABLE else ".csv"
    fpath = outdir / f"probe_results_{run_name}{suffix}"
    if PYARROW_AVAILABLE:
        df.to_feather(fpath)
    else:
        df.to_csv(fpath, index=False)
    print(f"Saved DataFrame to {fpath.resolve()}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    run_name = parse_cli()

    print("# SLURM environment probe\n")
    print(f"Run identifier            : {run_name}\n")

    # CPU + memory ----------------------------------------------------------
    print(f"Allocated CPU cores        : {cpu_count()}")
    mem_gib = total_memory_gib()
    print(f"Total visible memory       : {mem_gib:.2f} GiB\n")

    # Python version --------------------------------------------------------
    print("# Python interpreter\n")
    print(f"Short version              : {platform.python_version()}")
    print("Full sys.version banner    :")
    print(sys.version.replace("\n", "\n                               "))
    print()

    # /etc/issue ------------------------------------------------------------
    print("# /etc/issue contents\n")
    print(read_issue())
    print()

    # Packages --------------------------------------------------------------
    print("# Python packages (pip3 list)\n")
    print(pip_list())

    # Optional DataFrame ----------------------------------------------------
    df = generate_dataframe()
    if df is not None:
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        save_dataframe(df, results_dir, run_name)

    # Idle to reach ~3 min --------------------------------------------------
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
