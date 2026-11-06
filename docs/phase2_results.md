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
  split is never used to fit or select models (it only fits the post-hoc calibrators reported below);
  its probabilities are saved for Phase 6. Metrics on `test` (n=4,000).
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

## Phase 2 completion: variability, splits, calibration, explanations (2026-11-07)

All numbers in this section are **SIMULATION results** on synthetic patients. They measure how
well models recover the simulator, not clinical performance. Test split n=4,000 unless stated;
3 model seeds (0, 1, 2). Every run directory holds `run.json` (config, seeds, commit, dataset and
knowledge hashes, input columns, split distributions, package versions), `metrics.json`,
`report.md` and the saved raw and calibrated predictions. Commit provenance of the regenerated
outputs is in the "Reproduction" section below.

| experiment | what was tested | dataset / config | output |
|---|---|---|---|
| primary | all 7 models | `sim_v2` (primary, simulator seed 42) / `configs/phase2_sim_v2.yaml` | `outputs/phase2/sim_v2` |
| sensitivity: fallback onsets | unknown onsets filled with an assumed 0-24 h window | `sim_v1` / `configs/phase2_sim_v1.yaml` | `outputs/phase2/sim_v1` |
| sensitivity: early local signs | the 4 label-only local signs given an assumed [0, 1.5] h window | `sim_v2_early_local` / `configs/phase2_sim_v2_early_local.yaml` | `outputs/phase2/sim_v2_early_local` |
| split check | same patients as sim_v2, stratified species x syndrome splits | `sim_v2_stratified` / `configs/phase2_sim_v2_stratified.yaml` (no transformer) | `outputs/phase2/sim_v2_stratified` |
| simulator seeds | sim_v2 regenerated with seeds 42-46, 3 model seeds each | `configs/phase2_simseed_sim_v2.yaml` | `outputs/phase2/simseed_sim_v2` |
| explanations | XGBoost (with and without context), random forest; model seed 0 | sim_v2 / `configs/phase2_explain_sim_v2.yaml` | `outputs/phase2/explain_sim_v2` |
| ablations / robustness | as in the hardening section (re-run, identical numbers) | sim_v2 | `outputs/phase2/ablation_sim_v2`, `robustness_sim_v2` |

### Simulator-seed variability (5 simulated datasets x 3 model seeds)

The configs/sim_v2.yaml dataset was regenerated with seeds 42-46, changing only the seed. Seed 42
reproduces sim_v2 byte for byte. Each column is a separate source of variation:

| model | macro-F1 mean | simulator-seed sd (range) | model-seed sd | test bootstrap sd | critical error mean | simulator-seed sd (range) |
|---|---|---|---|---|---|---|
| rule | 0.573 | 0.006 (0.566-0.580) | 0 | 0.009 | 0.356 | 0.010 (0.346-0.368) |
| xgboost | 0.646 | 0.009 (0.635-0.656) | 0.001 | 0.009 | 0.356 | 0.010 (0.346-0.368) |
| xgboost_context | 0.685 | 0.006 (0.678-0.694) | 0.002 | 0.008 | 0.257 | 0.008 (0.248-0.270) |
| logistic_regression | 0.643 | 0.009 (0.630-0.656) | 0.001 | 0.009 | 0.356 | 0.010 (0.346-0.368) |
| random_forest | 0.642 | 0.010 (0.632-0.653) | 0.002 | 0.009 | 0.348 | 0.010 (0.337-0.359) |
| transformer | 0.643 | 0.009 (0.633-0.656) | 0.005 | 0.009 | 0.356 | 0.010 (0.346-0.368) |

- The spread across simulated datasets (about 0.01) is about the size of the test-set bootstrap sd.
  So it is mostly test-sampling noise, not a different population. Model-seed sd is 2-10 times
  smaller. The ± values reported earlier (model seeds only) understated the uncertainty.
- The primary sim_v2 (seed 42) sits at the favourable end: XGBoost 0.654 versus a mean of 0.646
  over seeds. Differences between learned models (0.642-0.646) are smaller than the
  simulator-seed sd, so the symptom-only learned models cannot be ranked against each other.
  Their gain over the rule (+0.07) and the context gain (+0.04 F1, −0.10 critical error) are well
  outside the noise.
- These intervals do not cover uncertainty in the knowledge table, or any difference between the
  simulator and real patients.

### Random vs stratified splits

The random split on sim_v2 is already balanced: per-split syndrome shares are within 1.1 points
of each other, species shares are 0.117-0.135, and every class is present in every split. The
stratified split (19 species x syndrome strata, no fallback needed with min stratum 20) narrows
them to within 0.03 points. On the same patients with a different test split (n=3,995):

| model | random macro-F1 / critical error | stratified macro-F1 / critical error |
|---|---|---|
| rule | 0.571 / 0.347 | 0.579 / 0.351 |
| xgboost | 0.654 / 0.347 | 0.642 / 0.351 |
| xgboost_context | 0.689 / 0.248 | 0.683 / 0.239 |
| logistic_regression | 0.644 / 0.347 | 0.628 / 0.351 |
| random_forest | 0.651 / 0.339 | 0.637 / 0.342 |

The differences (up to 0.016) are within the simulator-seed and bootstrap spread above, so the
split strategy does not change any conclusion. Random splitting stays the default, so the primary
dataset is unchanged. No held-out patient in any run has inputs identical to a training patient's.

### Post-hoc calibration (fitted on the calibration split only, evaluated on test)

Syndrome output, sim_v2, mean of 3 seeds. "helps" = number of seeds where test NLL went down.

| model | raw NLL / ECE | temperature | Platt (sigmoid) | isotonic |
|---|---|---|---|---|
| xgboost | 0.7261 / 0.014 | 0.7265 / 0.022 (0/3) | 0.7266 / 0.019 (0/3) | 0.7353 / 0.023 (0/3) |
| xgboost_context | 0.6158 / 0.017 | 0.6156 / 0.019 (3/3) | 0.6156 / 0.017 (2/3) | 0.6219 / 0.016 (0/3) |
| logistic_regression | 0.7348 / 0.021 | 0.7350 / 0.019 (0/3) | 0.7342 / 0.015 (3/3) | 0.7340 / 0.018 (1/3) |
| random_forest | 0.7711 / 0.040 | 0.7707 / 0.039 (2/3) | 0.7681 / 0.037 (3/3) | **0.7586 / 0.015 (2/3)** |
| transformer | 0.7324 / 0.029 | 0.7319 / 0.027 (3/3) | 0.7305 / 0.027 (3/3) | 0.7503 / 0.022 (0/3) |

P(envenomed) (binary) behaves the same way. XGBoost: raw NLL 0.373 / ECE 0.011, made worse by every
method. Random forest: isotonic improves ECE from 0.045 to 0.018.

- **Calibration mostly does not help.** XGBoost, logistic regression and the transformer are
  already well calibrated on simulated data (ECE 0.01-0.03). Every change in NLL is under 0.002,
  except where isotonic makes it worse. The only clear gain is isotonic for the random forest
  (ECE 0.040 → 0.015), which is also the model that was least calibrated before.
- Isotonic can assign a near-zero probability to a class. One such patient costs a lot of NLL, so
  isotonic sometimes worsens the mean NLL even when it improves ECE (e.g. sim_v1 random forest:
  2/3 seeds better, mean NLL 0.723 → 0.730). The same pattern holds on sim_v1, sim_v2_early_local
  and the stratified split (per-run tables in each `report.md`).
- Raw probabilities stay the primary outputs. Every reported metric, threshold table and
  conformal input above uses them. Calibrated probabilities are saved next to them
  (`p_syndrome_<method>`, `p_envenomed_<method>`). Fitted parameters are in metrics.json. No class
  was ever absent from a calibration split, so the single-class identity fallback was never used
  in these runs.

### Explanations (XGBoost TreeSHAP; random forest tree-path contributions; permutation importance)

These describe associations learned from SIMULATED data. They are **not causal** and not clinical
evidence (`outputs/phase2/explain_sim_v2/report.md`). The contributions add up to the model output
(maximum error 5e-6 for XGBoost, 1e-15 for the random forest).

| model | permutation importance, macro-F1 drop (test): largest blocks | top single features (mean abs. contribution) |
|---|---|---|
| xgboost | timing 0.187, symptom count 0.139, symptom identity 0.073, presentation delay 0.005 | n_observed, presentation_hours, ptosis (onset, presence), local_swelling |
| xgboost_context | symptom count 0.147, timing 0.116, context 0.091, symptom identity 0.053 | n_observed, presentation_hours, asleep, indoor, ptosis |
| random_forest | timing 0.246, symptom count 0.090, symptom identity 0.036, presentation delay 0.007 | n_observed, presentation_hours, local_swelling onset, ptosis onset |

- The single strongest signal is the **number of observed symptoms**. For a patient with nothing
  observed, `n_observed = 0` pushes toward non-venomous/dry. That is how the simulator's
  label-only local signs turn into critical errors (finding 6; docs/evidence_audit_local_signs.md).
- By symptom: ptosis, incoagulable blood, local swelling and abdominal pain matter most. This
  matches the leave-one-symptom-out ablation.
- Timing columns carry much of the macro-F1, mostly by separating haemotoxic from local-only. This
  matches ablation B (presence only: −0.029). Presentation delay matters little by permutation
  (−0.005), but it has large mean contributions, because it shifts the base rate for patients
  with nothing observed.
- With context, `asleep` and `indoor` rank right after symptom count. This is the cited krait
  pattern built into the simulator (night, indoors, asleep), not a discovered clinical fact.

### Ablations and robustness

Re-run with the new metadata; the numbers are identical to the hardening section above.

### Reproduction and verification

`python -m src.verify_runs <run dirs>` re-checks every training run (sim_v2, sim_v1,
sim_v2_early_local, sim_v2_stratified and the five simulator-seed runs; 149 prediction files):
- every saved patient is in its recorded split, with the dataset's labels;
- fit and validation patients are exactly the train split, for every seed;
- calibrators were fitted on exactly the calibration split;
- every test metric regenerates from the saved predictions to within 1e-9.

No problems were found. The commit each output was produced from is recorded in its
`run.json` (`git.commit`, `git.dirty`).

## Limitations

- Simulated data only; knowledge rows are not yet human-verified. Train and test come from the
  same simulator, so results measure how well a model recovers the simulator, not clinical validity.
- The critical-error level (about 0.35) is driven by four label-only early local signs with no
  cited onset (docs/evidence_audit_local_signs.md). It is a property of the evidence gap, not of
  the models.
- Uniform species mix; GPS and month are placeholders (not used).
- No hyperparameter search beyond fixed defaults (deliberately: no selection on calibration/test).
- ± in the earlier sections covers training seeds on one dataset. Variation across simulator
  seeds and test bootstrap is reported separately above and is about 5-10 times larger.
- Threshold tables are research-only and evaluated on the test split without selection; they are
  not clinical thresholds and need independent validation and clinician approval.
- Robustness corruptions are simple synthetic models of reporting error (the omission symptom set
  is an assumption); models are trained on clean data only.
- Not a medical device; never to be used for diagnosis, triage or treatment decisions.
