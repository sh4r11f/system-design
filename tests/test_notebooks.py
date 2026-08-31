"""End-to-end gate: execute every course notebook and fail on any cell error.

Each notebook carries its own inline `assert`s, so "the notebook runs" means
"every claim the notebook makes was just re-verified". Notebooks are executed
in-memory with their own directory as CWD; outputs are never written back to
the .ipynb files (the repo keeps notebooks output-free).
"""

from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = sorted(
    p for p in (REPO_ROOT / "notebooks").rglob("*.ipynb")
    if ".ipynb_checkpoints" not in p.parts
)


@pytest.mark.notebooks
@pytest.mark.parametrize("nb_path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_executes(nb_path):
    nb = nbformat.read(nb_path, as_version=4)
    client = NotebookClient(
        nb,
        timeout=300,  # per-cell ceiling; course convention keeps cells fast
        kernel_name="python3",
        resources={"metadata": {"path": str(nb_path.parent)}},
    )
    client.execute()  # raises CellExecutionError on the first failing cell
