# Phase 2 audit (2026-11-07)

Audited at branch `main`, commit `5d27cdd` (working tree clean), before any hardening edits.
All data referred to is SIMULATION data. Findings are verified against the current code and
the generated `data/processed/sim_v2`, not carried over from earlier reviews.

## Verified findings

| # | area | finding | severity | status before hardening |
|---|---|---|---|---|
| 1 | leakage | Feature matrices are built only from observed sequences, `presentation_hours` and (for `xgboost_context`) hour/indoor/asleep. No target or diagnostic column enters any model today. | - | OK |
| 2 | leakage | Checked on sim_v2: 0 observed events after presentation, 0 observed label-only events, 0 observed events without an onset, 0 unobserved events that should have been observed. | - | OK |
| 3 | leakage (latent) | `SymptomDataset.patients` holds targets (`species`, `venom_syndrome`, `dry_bite`) and simulator diagnostics (`order_violations`, `n_assumed_onsets`, `n_unknown_onsets`, `onset_*`) in the same frame as the allowed inputs. Nothing structural stops them reaching a model. `n_unknown_onsets` alone is a strong leak: P(envenomed) is 0.95 when it is > 0 vs 0.25 when 0. | high | no allowlist, no guard |
| 4 | leakage | `observed_events` trusts the simulator's `observed` flag; it does not re-check `hours <= presentation_hours` itself. | low | single point of trust |
| 5 | leakage tests | Existing tests check sequence building by example only; no test perturbs targets/diagnostics/future events and checks the model inputs are unchanged; no negative test for injected columns. | medium | missing |
| 6 | multi-task | The transformer's species labels shape the shared encoder through the species loss (legitimate multi-task target use, never an input). XGBoost heads are fully separate. Not documented or tested. | low | undocumented |
| 7 | metrics | Only accuracy, macro-F1, critical error, NLL, ECE, Brier. No per-class precision/recall/F1, sensitivity/specificity, weighted F1, or critical-error numerator/denominator and breakdown by syndrome. Empty groups are skipped safely. | medium | incomplete |
| 8 | decisions | Argmax only. The calibrated P(envenomed) is not evaluated as a threshold policy (referral rate vs missed envenoming). | high | missing |
| 9 | baselines | No linear or bagged-tree baseline; cannot tell whether XGBoost adds anything over logistic regression. | medium | missing |
| 10 | ablations | None. Unknown which inputs (presence, timing, presentation delay, individual symptoms, context) drive performance. | medium | missing |
| 11 | robustness | Models are only evaluated on clean simulated inputs. | medium | missing |
| 12 | reproducibility | `outputs/phase2/*/run.json` were written before commit `63040dd` (logged as `c40d8f3...-dirty`). Seed sd covers training seeds only, not data seeds. | low | documented, not fixed |
| 13 | splits | Validation subset carved from train only; calibration split never fitted on; prior uses training labels only; XGBoost early stopping on validation only. | - | OK |

## Files to change

| file | change |
|---|---|
| `src/data/features.py` (new) | strict input allowlist (`select_allowed`), `ModelInputs`, `FeatureSpec` (ablation switches), feature-name validation, tabular matrix builder |
| `src/data/dataset.py` | re-check `hours <= presentation_hours`; `tabular_features` delegates to `features.py` (same columns, same order) |
| `src/models/sklearn_baselines.py` (new) | logistic regression and random forest heads (imputer/scaler fitted on training rows only) |
| `src/models/registry.py` (new) | one fit/predict interface for prior, rule, XGBoost, LR, RF, transformer; feature specs per model |
| `src/evaluate.py` | extended metrics (per-class, sensitivity/specificity, weighted F1, critical-error breakdown); existing keys and definitions unchanged |
| `src/decision_policy.py` (new) | research-only threshold evaluation of P(envenomed) |
| `src/train.py` | use registry + allowlist, record and validate every model's features, add new metrics and threshold tables |
| `src/reporting.py` (new) | markdown rendering moved out of `train.py` |
| `src/ablation.py` (new) | ablation experiments A-I |
| `src/robustness.py` (new) | evaluation-time input corruption experiments |
| `configs/phase2_*.yaml` | add LR/RF, decision thresholds; new ablation and robustness configs |
| `tests/` | leakage, metrics, decision policy, baselines, ablation, robustness tests |
| `docs/phase2_results.md`, `README.md` | updated results and commands |

Not changed: simulator, knowledge tables, primary dataset `sim_v2`, labels, split assignment.

## Resolution (same day)

| # | resolution |
|---|---|
| 3 | `src/data/features.py`: `select_allowed` allowlist, `build_inputs` as the only dataset-to-model bridge, `validate_feature_names` on every tabular matrix; `run.json` records every model's inputs |
| 4 | `build_sequences` refuses events flagged observed that start after presentation |
| 5 | `tests/test_leakage.py`: perturbation invariance for all feature specs and transformer tensors, forbidden-column injection, label-to-head tests. Hand mutation check: smuggling `dry_bite`, `venom_syndrome`, `species`, `n_unknown_onsets` or hidden events is caught |
| 6 | documented in `src/models/registry.py`; tested with `species_loss_weight: 0` |
| 7 | `src/evaluate.py`: weighted F1, per-class precision/recall/F1/specificity, envenomation sensitivity/specificity, critical-error numerator/denominator by syndrome and observed group; existing keys unchanged |
| 8 | `src/decision_policy.py` (research only; ties referred, probabilities validated) |
| 9 | `src/models/sklearn_baselines.py` (logistic regression, random forest) |
| 10 | `src/ablation.py`, `configs/phase2_ablation_sim_v2.yaml` |
| 11 | `src/robustness.py`, `configs/phase2_robustness_sim_v2.yaml` |
| 12 | data-seed variation: covered by `src/seed_variability.py` (sections 8-17 below). Dirty outputs: still open, see below |

Feature matrices before and after the refactor were compared on sim_v2: identical names and values.
Tests: 249 passed (191 before hardening).

## Sections 8-17 (continuation, 2026-11-07)

Audited at `feaf9e5` (working tree clean) before these edits. Already satisfied before this
continuation and not redone: patient-level separation of train / calibration / test (one split
per patient, finding 13), validation carved from train only, leakage tests, threshold boundary
tests, ablations and robustness.

| # | area | finding at `feaf9e5` | resolution |
|---|---|---|---|
| 14 | variability | seed sd covered training seeds on one dataset only | `src/seed_variability.py`, `configs/phase2_simseed_sim_v2.yaml`: 5 simulator seeds x 3 model seeds; model-seed sd, simulator-seed sd/range and test-bootstrap sd reported separately |
| 15 | splits | `assign_splits` is a random permutation, not stratified; split distributions were not logged. On sim_v2 the random split is already balanced (syndrome shares within 1.1 points; smallest species x syndrome cell 86) | `src/data/splits.py`: opt-in `split_strategy: stratified` (species\|syndrome strata, fallback to syndrome, then a pooled `rare` stratum, all logged). Default stays random, so sim_v2 is regenerated byte-identically (checked). `split_summary` (sizes, syndrome, species, envenomed, dry-bite, missing classes, identical inputs across splits) is in every run.json and report; `check_disjoint` runs for every fit. Check run: `configs/sim_v2_stratified.yaml` |
| 16 | calibration | none; raw probabilities only | `src/uncertainty/calibration.py`: temperature, Platt, isotonic (sample-size gated), multiclass syndrome and binary P(envenomed), fitted on the calibration split only; raw and calibrated NLL / Brier / ECE on test, help/no-help flags, reliability tables and diagrams |
| 17 | explainability | none | `src/explain.py`: XGBoost TreeSHAP (native), RF tree-path contributions (labelled not Shapley), permutation importance by block and symptom, individual examples, additivity check |
| 18 | evidence | the four label-only local-sign rows were documented only in extraction notes | `docs/evidence_audit_local_signs.md` |
| 19 | artifacts | run.json lacked dirty flag, versions, dataset hashes, seeds, split distributions; runs silently overwrote each other; failures were not recorded | `src/artifacts.py` (`RunRecorder`, deterministic run id, `attempts.jsonl`, overwrite guard) used by train, ablation, robustness, explain and seed variability |
| 20 | CI | no lint; pyflakes not a declared dependency | `requirements-dev.txt` (pyflakes, matplotlib), lint step in `.github/workflows/tests.yml` |
| 21 | verification | no tool checked saved predictions against the dataset | `src/verify_runs.py` (split membership, train-only fitting, calibration rows, metric regeneration, commit) |

Finding 12 (dirty outputs) is resolved. The implementation was committed as `0ec7c3c` and
every experiment re-run from the clean tree. All 13 `run.json` files record `0ec7c3c` with
`dirty: false`. The datasets regenerated byte-identically. `src.verify_runs` found 0 problems
over 150 saved prediction files. The documented numbers match the regenerated artifacts.

## Final audit of the experiment outputs (at `0ec7c3c`)

| check | result |
|---|---|
| metrics correspond to saved predictions | all 150 files regenerate their metrics.json values to within 1e-9 (`src.verify_runs`) |
| no train/test or calibration/test leakage | fit + validation = train split for every seed and are disjoint from calibration and test; saved predictions hold only calibration/test patients in their dataset split; no held-out patient has inputs identical to a training patient's |
| allowlist | every tabular model's input columns lie within `allowed_feature_names` and contain no forbidden column; the transformer gets exactly `TRANSFORMER_INPUTS` |
| seeds and configs recorded | every run.json has the config, simulator seed, model seeds, dataset and knowledge hashes, package versions, split assignment and distributions |
| calibration uses calibration data only | `n_fit` equals the calibration-split size and `n_eval` the test size for every model and seed; a unit test shows the fitted parameters do not change when test labels are scrambled |
| missing-class identity fallback | recorded as `identity_single_class` in the fitted parameters (unit-tested). It never triggered in these runs, because every class is present in every calibration split |
| raw and calibrated probabilities preserved | every prediction file holds `p_syndrome`, `p_envenomed_raw` and `p_syndrome_/p_envenomed_<method>` for each fitted method |
| threshold equality | P(envenomed) equal to a threshold (within 1e-9) is referred; covered by `tests/test_decision_policy.py`, which passes |
| simulator vs model seed variability | reported in separate columns (`seed_variability.json`, report.md); the simulator-seed spread is about the size of the test bootstrap spread and 2-10 times the model-seed spread |
| failed experiments | none. Every run recorded one attempt (`attempts.jsonl`, status complete) in both the first batch and the clean-commit rerun |

## Robustness OOM investigation

Earlier session: one robustness run failed with `ArrayMemoryError: Unable to allocate 8.54 MiB
for an array with shape (20000, 56)` in logistic-regression prediction. A rerun with no code
changes succeeded.

Measured in the clean-commit rerun (Windows peak counters via `GetProcessMemoryInfo`):

| step | wall time | peak working set | peak commit |
|---|---|---|---|
| train sim_v2 (7 models x 3 seeds) | 4m42s | 703 MB | 1.76 GB |
| robustness | 9m01s | 675 MB | 1.73 GB |
| seed variability (5 datasets) | 24m38s | 789 MB | 1.86 GB |
| ablation / explain | 2m03s / 54s | 472 / 555 MB | 1.46 / 1.55 GB |

GPU memory: not applicable. torch is a CPU build (`2.15.0+cpu`; CUDA not available), so no GPU is
used even though the machine has an RTX 3050.

The machine has 15.8 GB RAM and a 24.0 GB commit limit (RAM + 8.4 GB pagefile). Before each step,
19.1-20.0 GB was already committed system-wide (browsers, Claude, node, MySQL, Defender, etc.).
Windows refuses an allocation once the commit limit is reached, however much RAM is free. A
failure on an 8.5 MiB request fits that.

- **Ruled out:** a memory leak or growth in the robustness code (peak 1.7 GB, flat across a
  9-minute run and stable between runs); dataset size (20,000 x 56 floats = 8.5 MiB); batch size
  (LR/RF/XGBoost predict on the full matrix; the transformer batch is 256); repeated model loading
  (each model is fitted once per seed and kept in memory, peak 1.7 GB).
- **Most likely cause:** system-wide commit exhaustion from other processes plus this process.
  It is consistent with all measurements but **not proven**: no snapshot of system commit exists
  from the moment of the original failure. Marked **unresolved / probable external cause**. If it
  recurs, record system commit usage at failure time (PowerShell: `Get-CimInstance Win32_OperatingSystem`, TotalVirtualMemorySize - FreeVirtualMemory), or raise the pagefile size.
