# SnakeGuard AI: Uncertainty-Aware Snakebite Triage

## Research question
Can a model predict the venom syndrome of a snakebite (and the likely species) from
symptom progression, bite location/time and optional images, WITHOUT requiring a
photo of the snake, and know when it is unsure?

Context: the snake is never identified in about half of bites. Existing AI work is
photo-based (closest competitor: Animals 2026, DOI 10.3390/ani16203298, which combines
images + geographic prior). Our contribution is the no-photo pathway with calibrated
uncertainty.

This is a research prototype. It is NOT a medical device and must never output
antivenom dosing or treatment instructions. Outputs are triage classes only.

## Scope (India first)
Target species (the "Big Four" plus key others):
- Neurotoxic: Spectacled cobra (Naja naja), Common krait (Bungarus caeruleus)
- Haemotoxic: Russell's viper (Daboia russelii), Saw-scaled viper (Echis carinatus)
- Hump-nosed pit viper (Hypnale hypnale) as a hard case (not covered by Indian polyvalent antivenom)
- Non-venomous lookalikes (e.g. rat snake, wolf snake, checkered keelback)

Output heads:
1. Venom syndrome: neurotoxic | haemotoxic | local-only | non-venomous/dry
2. Species: top-k with probabilities
3. Triage decision from conformal prediction sets: treat-pathway | monitor | refer

## Architecture
1. Inputs (any subset may be missing):
   - Symptom timeline: list of (symptom, hours since bite) events
   - Context: GPS (lat/lon), month, time of day, indoor/outdoor, sleeping or not
   - Bite-wound photo (optional)
   - Snake photo (optional)
2. Per-modality encoders:
   - Symptoms: transformer over (symptom embedding + time encoding)
   - Context: location encoder (sinusoidal / Sphere2Vec-style) + time features
   - Images: frozen DINOv2 or EfficientNet backbone + small head
3. Missing-modality fusion: masked cross-attention with learned "missing" tokens,
   trained with random modality dropout.
4. Geographic prior: P(species | location, month) from occurrence data, combined
   multiplicatively with model logits.
5. Uncertainty gate: split conformal prediction (APS/RAPS) on a held-out
   calibration set. Large or venomous-containing sets map to "refer".

## Data plan
- Images: SnakeCLEF 2023/2024 data (research use; check licence), filtered to Indian species.
- Occurrences for geo prior: GBIF and iNaturalist research-grade records for target species in India.
- Symptoms: NO public patient-level dataset exists. Phase 1 builds a
  literature-derived clinical knowledge table (symptom, typical onset window,
  frequency per species) from published case series and WHO/Indian national
  snakebite guidelines, every row cited. A simulator samples synthetic patients from it.
  All synthetic results must be labelled as simulation results.
- Later: real retrospective data only via a hospital partner with ethics approval.

## Evaluation
- Macro-F1 for venom syndrome and species
- Critical error rate: venomous predicted as non-venomous (most important metric)
- Performance under every modality-missing combination (table of results)
- Conformal: empirical coverage, average set size, refer rate
- Baselines: image-only classifier, symptom-only XGBoost, late fusion, rule-based syndromic table

## Repo layout
```
data/raw/            # downloaded, never edited
data/processed/
knowledge/           # clinical knowledge table (CSV) + sources.bib
src/data/            # downloaders, simulator, datasets
src/models/          # encoders, fusion, heads
src/uncertainty/     # conformal prediction
src/train.py
src/evaluate.py
configs/             # YAML configs per experiment
notebooks/           # exploration only
tests/
```

## Conventions
- Python 3.11, PyTorch, Hydra or plain YAML configs, pytest
- Fixed random seeds; every experiment logs its config and git commit
- Never commit data or model weights; use .gitignore
- Every number in the knowledge table needs a citation in knowledge/sources.bib
- Keep functions small and typed; add a test for each data transform

## Phases
0. Repo setup, environment, tests running
1. Clinical knowledge table + synthetic patient simulator
2. Symptom-only baseline (XGBoost) + symptom transformer
3. Geographic prior from GBIF occurrences
4. Image branch on SnakeCLEF Indian subset
5. Missing-modality fusion model
6. Conformal uncertainty gate + full evaluation
7. Offline mobile export (ONNX / TFLite) and demo app
