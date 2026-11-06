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

The knowledge base in `knowledge/` (loaded by `src/data/knowledge.py`):

| file | one row per | main columns |
|---|---|---|
| `symptoms.csv` | symptom in the controlled vocabulary | `marker` (neurotoxic / haemotoxic / local / none) |
| `species.csv` | species | `group` (venomous / non-venomous), `dry_bite_rate` |
| `clinical_table.csv` | (species, symptom) | `onset_min_hours`, `onset_max_hours`, `frequency` |
| `context_table.csv` | (species, feature) | `feature` (night / indoor / asleep), `probability` |
| `context_joint.csv` | (species, night, indoor, asleep) | `count` (complete cases, Wijayasekara 2026 raw data) |
| `onset_order.csv` | (species or `*`, before, after) | cited order of onset; cycles are rejected |
| `presentation_delay.csv` | (profile, delay bin) | `min_hours`, `max_hours` (blank = open), `proportion` |

Every numeric row also has `source_key` (one or more BibTeX keys from `sources.bib`,
separated by `;`), `evidence` (locator + short verbatim quote) and `verified` (true only
after a human has checked the number against the source PDF). Draft literature extractions
with quotes live in `knowledge/extraction/`.

Rows with `source_key=TODO` or blank numbers are placeholders and are skipped with a warning.
`load_knowledge(..., require_citations=True)` refuses uncited or blank rows, and
`require_verified=True` refuses unverified ones.

## Simulated data

```bash
python -m src.data.validate                              # schema, citations, onset orders, delay bins
python -m src.data.generate --config configs/sim_v2.yaml # primary, evidence-only dataset
```

Writes `patients.csv`, `events.csv`, `meta.json`, a sanity `report.md` (with a rule-based
syndromic baseline) and `onset_diagnostics.md` to `data/processed/sim_v2/`. `sim_v2` is the
primary dataset: it uses cited onset windows only (`experiment_type: primary`). Symptoms with a
cited frequency but no cited onset are label-only (`unknown_onset: label_only`): they count toward
the venom-syndrome label but have no onset time and are never part of the model input. Filling unknown
onsets with an assumed window (`onset_fallback`) is refused unless a config says
`experiment_type: sensitivity` (e.g. `configs/sim_v1.yaml`, kept as a labelled sensitivity
dataset). `meta.json` records the git commit, knowledge-file hashes, verified/unverified rows
per table and every simulation assumption in force. The venom syndrome label comes from each
patient's full symptom course, while the model only sees events up to presentation. All of this
is **simulation data**. See `docs/phase1_plan.md`.

Knowledge rows are AI-assisted drafts until checked by a person. To list what still needs checking:

```bash
python -m src.data.checklist   # writes docs/verification_checklist.md
python -m src.data.quotecheck  # checks quotes against open full texts -> docs/quote_check.md
```

Robustness and realism checks (all output is simulation data):

```bash
python -m src.data.sensitivity --config configs/sensitivity_v2.yaml   # 17 variants x 5 seeds, 95% CIs
python -m src.data.vignettes --dataset data/processed/sim_v2 --n 40 --out data/processed/review_v2
```

See `docs/clinician_review_protocol.md` for the blinded review.

CI (`.github/workflows/tests.yml`) runs `python -m src.data.validate` and the test suite on
every push and pull request.

## Status

- [x] Phase 0: repo, environment, tests
- [x] Phase 1: clinical knowledge table + simulator (engineering done; rows await human verification,
      see docs/verification_checklist.md). GPS and month are uniform placeholders until Phase 3.
- [ ] Phase 2: symptom-only baselines
- [ ] Phase 3: geographic prior (GBIF)
- [ ] Phase 4: image branch (SnakeCLEF)
- [ ] Phase 5: missing-modality fusion
- [ ] Phase 6: conformal uncertainty gate + evaluation
- [ ] Phase 7: offline mobile export
