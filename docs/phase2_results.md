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
- Run: `python -m src.train --config configs/phase2_sim_v2.yaml` (primary); sensitivity runs
  `configs/phase2_sim_v2_early_local.yaml` (assumed early local-sign window, finding 6) and
  `configs/phase2_sim_v1.yaml` (sensitivity: unknown onsets filled with the assumed 0-24 h window).

## Venom syndrome, test split (mean ± sd over 3 seeds)

| model | sim_v2 macro-F1 | sim_v2 critical error | sim_v1 macro-F1 | sim_v1 critical error |
|---|---|---|---|---|
| prior | 0.149 | 1.000 | 0.149 | 1.000 |
| rule | 0.571 | 0.347 | 0.610 | 0.317 |
| xgboost | 0.654 ± 0.001 | 0.347 ± 0.001 | 0.688 ± 0.001 | 0.322 |
| logistic_regression | 0.644 ± 0.002 | 0.347 ± 0.000 | 0.680 | 0.323 |
| random_forest | 0.651 ± 0.003 | 0.339 ± 0.004 | 0.680 | 0.324 |
| transformer | 0.645 ± 0.005 | 0.348 ± 0.000 | 0.677 ± 0.001 | 0.317 ± 0.010 |
| xgboost_context (ref.) | 0.689 ± 0.002 | 0.248 ± 0.003 | 0.723 ± 0.001 | 0.226 ± 0.002 |

(sd omitted where it rounds to 0. sim_v2_early_local: xgboost 0.784 / 0.124, logistic regression
0.781 / 0.124, random forest 0.779 / 0.123, transformer 0.782 / 0.122.)

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
6. **Data gap found: early local signs are label-only, and they dominate the result.** Russell's
   viper local pain (frequency 1.00) and swelling (0.925), cobra local swelling (1.00) and
   saw-scaled viper local pain (0.96) have no cited onset window, so in sim_v2 they are never
   visible. Filling all unknown onsets with the broad assumed 0-24 h window (sim_v1) only moves
   critical error 0.35 → 0.32, because many draws land after presentation. A second literature
   search (knowledge/extraction/onsets_vipers.md section 4) found **no citable since-bite onset**
   for these four rows. To measure what a cited early window would be worth, `sim_v2_early_local`
   (`configs/sim_v2_early_local.yaml`, sensitivity only) gives just these four rows an
   **assumed** [0, 1.5] h window. The window is taken by analogy with the cited early local-sign
   windows of Echis swelling (bawaskar2019diagnosis) and Hypnale (abraham2025single):

   | model (test, 3 seeds) | macro-F1 | critical error | species top-3 |
   |---|---|---|---|
   | rule | 0.643 | 0.124 | - |
   | xgboost | 0.784 ± 0.002 | 0.124 | 0.871 ± 0.002 |
   | transformer | 0.782 ± 0.003 | 0.122 ± 0.003 | 0.874 ± 0.001 |
   | xgboost_context | 0.804 ± 0.002 | 0.082 ± 0.003 | 0.921 ± 0.001 |

   The no-symptom share at presentation drops from 63% to 50%. Critical error falls from about
   0.35 to about 0.12, and the remaining errors are again patients without any visible sign.
   So the headline symptom-only number depends mainly on four uncited onset windows, not on
   the model. Getting real time-to-local-sign data (clinician co-author, the Silva/Isbister cohort
   authors, Phillips 1988 QJM, Warrell 2010 Lancet) is the highest-value data task before Phase 6.
   Until then, report sim_v2 as primary and sim_v2_early_local as the sensitivity bound.

## Phase 2 hardening (2026-11-07)

Audit: `docs/phase2_audit.md`. All numbers below are SIMULATION results on `sim_v2` (test
split, 3 training seeds), regenerated after the hardening; the pre-existing models reproduce
their earlier numbers exactly.

**Leakage.** No leak was present, but nothing structural prevented one: `patients.csv` keeps
targets and simulator diagnostics next to the inputs, and `n_unknown_onsets` alone separates
envenomed patients (P(envenomed) 0.95 vs 0.25). Every model now gets its inputs through an
allowlist (`src/data/features.py`); `build_sequences` re-checks onset <= presentation instead of
trusting the simulator flag. `tests/test_leakage.py` scrambles targets, diagnostics, placeholders,
patients.csv onset columns, and adds post-presentation and label-only events, and requires
bit-identical inputs for every feature spec and the transformer tensors. Deliberately smuggling
`dry_bite`, `venom_syndrome`, `species` or `n_unknown_onsets` into the inputs, or letting hidden
events through, makes that test fail (checked by hand).

**New baselines.** Logistic regression (0.644 macro-F1) and random forest (0.651) match XGBoost
(0.654) and the transformer (0.645). On this simulated data a linear model is enough; all
learned models sit at the same critical error (0.34-0.35), the information limit described in
findings 2-3. Random forest is the least calibrated (ECE 0.040 vs 0.014 XGBoost).

**Experimental threshold policy (research only, not clinical thresholds).** Refer if
P(envenomed) >= t. For patients with no observed symptom, P(envenomed) only ranges over about
0.1-0.5, so the trade-off is steep:

| model | t | referral rate | envenomed classed low risk (of 2,297) | specificity |
|---|---|---|---|---|
| xgboost (symptoms) | 0.15 | 0.97 | 21 (0.9%) | 0.06 |
| xgboost (symptoms) | 0.25 | 0.74 | 224 (9.8%) | 0.48 |
| xgboost_context | 0.15 | 0.81 | 74 (3.2%) | 0.41 |
| xgboost_context | 0.25 | 0.69 | 152 (6.6%) | 0.63 |

With symptoms alone, missing almost no envenomed patient means referring almost everyone.
Context buys real specificity. No threshold here is validated or safe, and none is selected.

**Ablations** (XGBoost, `outputs/phase2/ablation_sim_v2/report.md`). Removing timing (presence
only) costs 0.029 macro-F1; removing symptom identity (times only) 0.055; removing presentation
time only 0.006. Critical error does not move in A-D: it is fixed by the patients with nothing
observed. Removing local symptoms (+0.25 critical error) or systemic symptoms (+0.36) hurts most;
of single symptoms, local swelling (+0.085), ptosis (+0.055) and abdominal pain (+0.051) matter
most. Context alone reaches 0.414 macro-F1 and 0.56 critical error. Only 9 of 18 symptoms ever
appear in the inputs: progressive swelling, blistering, necrosis, lymphadenopathy, systemic
bleeding, AKI, shock, vomiting and headache have no cited onset in sim_v2 and are label-only.
These describe what this model uses on simulated data, not causal clinical evidence.

**Robustness** (`outputs/phase2/robustness_sim_v2/report.md`; trained clean, test inputs
corrupted, levels 0-30%). All models degrade alike and gradually. Randomly missing symptoms are
the most harmful: at 30%, critical error rises from 0.35 to 0.44 and macro-F1 drops from 0.65 to
about 0.58. False symptom reports lower the critical error (0.35 to 0.24 at 30%) only because more
patients look envenomed; macro-F1 falls to about 0.55. Onset-time noise (sd up to 30% of the
presentation time) costs up to 0.05 macro-F1 and leaves critical error unchanged. Omission of
patient-reported symptoms (assumed set) costs at most 0.02. XGBoost loses almost nothing with a
missing presentation time (consistent with ablation D); the other learned models cannot take a
missing value and are reported as not supported.

## Limitations

- Simulated data only; knowledge rows are not yet human-verified. Train and test come from the
  same simulator, so results measure how well a model recovers the simulator, not clinical validity.
- Uniform species mix; GPS and month are placeholders (not used).
- No hyperparameter search beyond fixed defaults (deliberately: no selection on calibration/test).
- ± covers training seeds (and corruption draws) on one simulated dataset, not data-generation seeds.
- Threshold tables are research-only and evaluated on the test split without selection; they are
  not clinical thresholds and need independent validation and clinician approval.
- Robustness corruptions are simple synthetic models of reporting error (the omission symptom set
  is an assumption); models are trained on clean data only.
- Not a medical device; never to be used for diagnosis, triage or treatment decisions.
