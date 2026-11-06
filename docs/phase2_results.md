# Phase 2 results: symptom-only baselines

> **SIMULATION RESULTS** on synthetic patients from a literature-derived table (rows not yet
> human-verified). Not clinical evidence. Full tables: `outputs/phase2/<dataset>/report.md`.

## Setup

- Input: what is known at presentation. Observed symptoms (symptom, onset hours, hours since
  onset) and the bite-to-presentation time. Label-only symptoms (cited frequency, no cited
  onset) and symptoms after presentation never reach the model (`src/data/dataset.py`).
- Models: `prior` (class frequencies), `rule` (Phase 1 syndromic table on observed symptoms),
  `xgboost` (symptom-only, one classifier per head), `transformer` (symptom transformer:
  [CLS] + presentation token + one token per observed symptom with symptom embedding and
  sinusoidal log-time encodings of onset and elapsed time; no positional encoding, so output
  does not depend on event order). `xgboost_context` adds hour of day / indoor / asleep as a
  reference for Phase 5.
- Training: `train` split minus 15% validation (early stopping), 3 seeds. The `calibration`
  split is never fitted on; its probabilities are saved for Phase 6. Metrics on `test` (n=4,000).
- Run: `python -m src.train --config configs/phase2_sim_v2.yaml` (primary) and
  `configs/phase2_sim_v1.yaml` (sensitivity: unknown onsets filled with the assumed 0-24 h window).

## Venom syndrome, test split (mean ± sd over 3 seeds)

| model | sim_v2 macro-F1 | sim_v2 critical error | sim_v1 macro-F1 | sim_v1 critical error |
|---|---|---|---|---|
| prior | 0.149 | 1.000 | 0.149 | 1.000 |
| rule | 0.571 | 0.347 | 0.610 | 0.317 |
| xgboost | 0.654 ± 0.001 | 0.347 ± 0.001 | 0.688 ± 0.001 | 0.322 |
| transformer | 0.645 ± 0.005 | 0.348 ± 0.000 | 0.677 ± 0.001 | 0.317 ± 0.010 |
| xgboost_context (ref.) | 0.689 ± 0.002 | 0.248 ± 0.003 | 0.723 ± 0.001 | 0.226 ± 0.002 |

Species (sim_v2): xgboost top-1 0.476, top-3 0.741; transformer top-1 0.472, top-3 0.744;
with context top-1 0.583, top-3 0.861 (prior: 0.133 / 0.384). The three non-venomous species
have the same cited symptom profile, so they cannot be told apart from symptoms alone.

## Findings

1. **The learned models beat the rule on macro-F1 (+0.08) but not on critical error.** They
   separate haemotoxic from local-only much better (haemotoxic recall 0.58 vs 0.23 for the rule),
   because they use onset timing and the absence of symptoms.
2. **Critical error at the argmax is set by the information available, not by the model.**
   63% of test patients (sim_v2) have no symptom observed by presentation (median presentation
   3.6 h). For them every symptom-only model predicts the most likely class, non-venomous/dry,
   so all envenomed patients in that group become critical errors (≈0.35 overall). On patients
   with at least one observed symptom, the critical error is 0.000 for every model.
3. **The models know about this risk.** On no-symptom test patients the mean predicted
   P(envenomed) is 0.30-0.32, matching the true rate of 0.32 (ECE 0.014-0.029 overall). A
   decision rule that refers patients with non-negligible P(envenomed), i.e. the Phase 6
   conformal gate, can turn that into referrals instead of critical errors. The argmax hides it.
4. **Context helps the most where symptoms cannot.** Night / asleep / indoor cut the critical
   error from 0.35 to 0.25 (krait bites at night while asleep), almost all on no-symptom patients.
   This supports the multimodal design (Phase 5).
5. **XGBoost ≈ transformer** on this data. The simulated timelines are short (median 0 observed
   events) and the features are low-dimensional, so the transformer has nothing extra to exploit
   yet. Its value is as the symptom encoder for Phase 5 fusion, not as a standalone win.
6. **Data gap found: early local signs are label-only.** Russell's viper local pain (frequency 1.00),
   cobra local swelling (1.00) and saw-scaled viper local pain (0.96) have no cited onset window,
   so in sim_v2 they are never visible. Filling them with the broad assumed 0-24 h window (sim_v1)
   only moves critical error 0.35 → 0.32 because many draws land after presentation. These signs
   are usually reported within minutes to hours of the bite; a cited early onset window would
   likely lower the symptom-only critical error considerably. This is a knowledge-table task
   (needs a citation and quote), not a model change.

## Limitations

- Simulated data only; knowledge rows are not yet human-verified.
- Uniform species mix; GPS and month are placeholders (not used).
- No hyperparameter search beyond sensible defaults; argmax decisions only.
