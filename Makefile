# All targets run through `conda run` so they work from any shell.
# If `conda` is not on your PATH, invoke as:  make CONDA=~/miniconda3/condabin/conda <target>
CONDA ?= conda
RUN   ?= $(CONDA) run -n sysdes

.PHONY: env lab test test-fast strip

env:  ## Create (or update) the sysdes environment and install the helper package
	$(CONDA) env create -f environment.yml -y || $(CONDA) env update -f environment.yml
	$(RUN) python -m pip install -e .

lab:  ## Launch JupyterLab in the course environment
	$(RUN) jupyter lab

test:  ## Run everything: unit tests + execute every notebook end to end (slow)
	$(RUN) python -m pytest

test-fast:  ## Run only the unit tests for the sysdes package
	$(RUN) python -m pytest -m "not notebooks"

strip:  ## Clear all notebook outputs (run this before committing notebooks)
	find notebooks -name '*.ipynb' -not -path '*.ipynb_checkpoints*' \
		-exec $(RUN) jupyter nbconvert --clear-output --inplace {} +
