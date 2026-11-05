# SnakeGuard AI

Uncertainty-aware snakebite triage research prototype. It predicts the venom syndrome
(and likely species) from symptom progression, bite location/time and optional images,
**without needing a photo of the snake**, and reports when it is unsure.

> **Not a medical device.** This is a research prototype. It outputs triage classes only
> and must never be used for antivenom dosing or treatment decisions.
> All results from `src/data/simulator.py` are **simulation results** on synthetic patients.

See `CLAUDE.md` for the full research design.

## Setup (Windows, Python 3.11)

```bash
py -3.11 -m venv .venv
.venv/Scripts/python -m pip install --index-url https://download.pytorch.org/whl/cpu torch
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pytest
```

(On Linux/macOS use `.venv/bin/python`. Drop the `--index-url` line to get a GPU build of torch.)

## Layout

```
data/raw/            # downloaded, never edited (git-ignored)
data/processed/      # git-ignored
knowledge/           # clinical_table.csv + sources.bib (every number cited)
src/data/            # downloaders, simulator, datasets
src/models/          # encoders, fusion, heads
src/uncertainty/     # conformal prediction
configs/             # YAML configs per experiment
notebooks/           # exploration only
tests/
```

## Clinical knowledge table

`knowledge/clinical_table.csv` has one row per (species, symptom):

| column | meaning |
|---|---|
| species | binomial name, e.g. `Naja naja` |
| venom_syndrome | `neurotoxic`, `haemotoxic`, `local-only`, `non-venomous` |
| symptom | snake_case symptom name, e.g. `ptosis` |
| onset_min_hours / onset_max_hours | typical onset window, hours since bite |
| frequency | probability (0 to 1) the symptom appears for this species |
| source_key | BibTeX key in `knowledge/sources.bib` |

Rows with `source_key=TODO` or blank numbers are placeholders. The loader skips incomplete
rows with a warning; `load_clinical_table(..., require_citations=True)` refuses uncited rows.

## Status

- [x] Phase 0: repo, environment, tests
- [ ] Phase 1: clinical knowledge table (filled from literature) + simulator.
      The simulator code exists as scaffolding; GPS and month are uniform placeholders until Phase 3.
- [ ] Phase 2: symptom-only baselines
- [ ] Phase 3: geographic prior (GBIF)
- [ ] Phase 4: image branch (SnakeCLEF)
- [ ] Phase 5: missing-modality fusion
- [ ] Phase 6: conformal uncertainty gate + evaluation
- [ ] Phase 7: offline mobile export
