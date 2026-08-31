"""sysdes — shared plumbing for the system design crash course notebooks.

The package intentionally stays tiny: lesson code lives *inside* the notebooks
so each notebook is a self-contained lesson. Only two things are shared here
because nearly every notebook needs them:

- ``sysdes.viz``: matplotlib helpers for system diagrams (box-and-arrow
  architecture diagrams, message timelines, consistent-hash rings).
- ``sysdes.sim``: a small deterministic discrete-event simulator with an
  unreliable network (latency, loss, partitions) used by the distributed
  systems notebooks.
"""

import shutil
from pathlib import Path

__version__ = "0.1.0"

# All notebook scratch data (SSTable files, Parquet partitions, ...) goes under
# this directory so the git repo never accumulates generated files.
SCRATCH_ROOT = Path.home() / "tmp" / "sysdes-course"


def scratch_dir(name: str, fresh: bool = True) -> Path:
    """Return a per-notebook scratch directory under ``~/tmp/sysdes-course/``.

    Parameters
    ----------
    name:
        Subdirectory name, usually the notebook's slug (e.g. ``"03-storage-engines"``).
    fresh:
        If True (default), any existing content is deleted first so notebook
        runs are reproducible from a clean slate.
    """
    path = SCRATCH_ROOT / name
    # Safety guard: we only ever delete inside SCRATCH_ROOT. A bug that changed
    # `path` to something outside it must fail loudly rather than delete data.
    if not path.resolve().is_relative_to(SCRATCH_ROOT.resolve()):
        raise ValueError(f"scratch_dir escaped {SCRATCH_ROOT}: {path}")
    if fresh and path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path
