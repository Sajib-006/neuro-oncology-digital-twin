"""One place for paths, data versions and dates used by every script.

Paths come from environment variables, with defaults:
  DATA_DIR  input data: stored downloads and the released derived files   (default: <repo>/data)
  OUT_DIR   where scripts write their outputs                              (default: DATA_DIR)
  FIG_DIR   where figure files are written                                 (default: OUT_DIR/figures)

Scripts read an input from OUT_DIR when a fresh copy is there, and from DATA_DIR otherwise.
So you can point DATA_DIR at the released data, write to a new OUT_DIR, and every later
stage picks up the files that earlier stages just made.

API keys are read from environment variables only (SCOPUS_API_KEY). No key is stored here.
"""
import datetime
import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
REPO = SRC.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", REPO / "data")).expanduser().resolve()
OUT_DIR = Path(os.environ.get("OUT_DIR", DATA_DIR)).expanduser().resolve()
FIG_DIR = Path(os.environ.get("FIG_DIR", OUT_DIR / "figures")).expanduser().resolve()
SUPP_DIR = OUT_DIR / "supplement"

# Set OFFLINE=1 to stop any stage from downloading a file that is not already stored.
OFFLINE = os.environ.get("OFFLINE", "0") not in ("", "0", "false", "no")

# ---------------------------------------------------------------- data versions and dates
SCOPUS_RECORDS_DATE = "2026-09-24"      # full records of the AI set (stage literature/02)
SCOPUS_COUNTS_DATE = "2026-09-28"       # count queries and tumor class counts
CTGOV_API_VERSION = "2.0.5"
CTGOV_DATA_DATE = datetime.date(2026, 9, 24)   # ClinicalTrials.gov data timestamp
FDA_LIST_UPDATED = "2026-09-04"         # FDA list of AI-enabled devices, page date
FDA_LIST_PULLED = "2026-09-25"
OPENTARGETS_RELEASE = "26.09"
CTD_REPORT_DATE = "2026-08-28"
DISGENET_VERSION = "7.0"
DISGENET_V7_URL = ("https://storage.googleapis.com/pheknowlator/archived_builds/release_v3.0.2/"
                   "build_01NOV2021/data/original_data/curated_gene_disease_associations.tsv")
GPROFILER_VERSION = "e114_eg62_p19"


def inp(rel):
    """Path of an input file or folder: OUT_DIR/rel if it exists, else DATA_DIR/rel."""
    p = OUT_DIR / rel
    return p if p.exists() else DATA_DIR / rel


def out(rel):
    """Path of an output file under OUT_DIR; its parent folder is created."""
    p = OUT_DIR / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def out_dir(rel):
    """Path of an output folder under OUT_DIR, created if needed."""
    p = OUT_DIR / rel
    p.mkdir(parents=True, exist_ok=True)
    return p


def fig_path(name):
    """Path of a figure file under FIG_DIR."""
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    return FIG_DIR / name


def use(*folders):
    """Make shared modules in src/<folder>/ importable (for example 'literature')."""
    for f in folders:
        p = str(SRC / f)
        if p not in sys.path:
            sys.path.insert(0, p)
