# Evidence audit: the four label-only early local-sign rows (2026-11-07)

Scope: the four `knowledge/clinical_table.csv` rows that have a cited **frequency** but **no cited
onset window**, and that dominate the Phase 2 critical-error result (docs/phase2_results.md,
finding 6). All facts below come from `knowledge/clinical_table.csv`, `knowledge/sources.bib` and
the extraction notes (`knowledge/extraction/vipers.md`, `elapids.md`, `onsets_vipers.md` §4,
`onsets_elapids.md`). No onset is invented here. Not clinical guidance.

## Row-by-row

| row | citation | population and setting | what the source supports | denominator / frequency used | applicability to India | verification |
|---|---|---|---|---|---|---|
| Daboia russelii, local_pain (freq 1.00) | kularatne2014revisiting (PLoS ONE 2014, doi 10.1371/journal.pone.0090198), full text read, Table 2 "Pain 53 (96)" | Sri Lanka (Anuradhapura teaching hospital), 55 specimen-proven Russell's viper bites (the 154 suspected cases are not used); 2 dry | **Presence only.** Table 2 covers the whole admission, not findings at presentation, so it gives neither an onset nor an upper bound. The "onset within 30 min" score item belongs to abdominal pain, not local pain | 53/55 reported; recorded as 53/53 envenomed (55 minus 2 dry), i.e. assumes all 53 painful bites are among the envenomed | Partial. Same species; Sri Lankan and South Indian Russell's vipers share neurotoxic features other populations lack (vipers.md). Not an Indian cohort | `verified=False`; clinician check pending (docs/clinician_review_protocol.md) |
| Daboia russelii, local_swelling (freq 0.925) | kularatne2014revisiting, Table 2 "Swelling 49 (89)" | as above | **Presence only**, same caveat (whole admission, no timing) | 49/55 reported; recorded as 49/53 envenomed | as above | `verified=False`; pending |
| Naja naja, local_swelling (freq 1.00) | kularatne2009cobra (Trans R Soc Trop Med Hyg 2009, doi 10.1016/j.trstmh.2009.04.002), **abstract only**: "5 dry bites (20%), 20 local reactions (80%)"; corroborated by silva2026cobra (Clin Toxicol 2026, abstract only): local envenoming 45/54 | Sri Lanka; 25 authenticated cobra bites (kularatne2009cobra); 54 bites in rural Sri Lanka (silva2026cobra) | **Presence only.** Neither abstract gives a time; full texts are paywalled. "Local reaction" is **mapped** to swelling (an interpretation: the abstract does not say swelling) | 20/25 bites recorded as 20/20 envenomed (assumes the 5 dry bites are exactly the 5 without a local reaction). silva2026cobra gives 45/54 (0.83) of all bites | Partial. Same species, Sri Lankan cohorts, no Indian series with per-sign counts was found | `verified=False`; pending. Abstract-only source: higher priority for full-text check |
| Echis carinatus, local_pain (freq 0.958) | gnanathasan2012sawscaled (Am J Trop Med Hyg 2012, doi 10.4269/ajtmh.2012.11-0447), full text read, Table 2 "Local pain 46 (96%)" | Sri Lanka (Jaffna, Northern Province); 48 bites with the snake brought in; *E. c. carinatus* | **Presence only**, no timing | 46/48 **bites**; the number envenomed is not stated, so 0.958 is a frequency among all bites used as if among envenomed (a lower bound if some bites were dry) | Limited. The authors note the Sri Lankan saw-scaled viper is notably mild; Indian *E. c. sochureki* (Rajasthan, gopalakrishnan2025antivenom) is more severe. Pooling regions changes the syndrome mix | `verified=False`; pending |

## Searches for an onset (none found)

Documented in `knowledge/extraction/onsets_vipers.md` §4 and `onsets_elapids.md` §1:
re-grep of cached full texts; Isbister et al. 2015 PLoS NTD (local effects 134/146, no per-sign
timing); the Silva/Isbister 2016 cohort (pain and swelling 244/245, no onset, full text blocked);
Echis TMA case report (no bite-to-admission time); a 15-patient Echis series seen only in search
snippets (source not identified, not used); North American pit viper and Hong Kong *Naja atra*
statements (wrong species or region, not used). WHO 2016 and MoHFW 2017 give only qualitative
or treatment-criterion statements ("within 48 h", "rapid extension"), not onset windows.

## Third search (2026-11-07): one cited general statement

knowledge/extraction/onsets_vipers.md section 5. Still no species-specific case series with a
measured time to local swelling or pain. One citable **secondary** statement was found for vipers in
general: mehta2002clinical (Med J Armed Forces India 2002, citing Warrell, Oxford Textbook of
Medicine 1996): "Swelling may become apparent within 15 minutes", and "If there is no swelling 2
hours after a viper bite, it is safe to assume that there has been no envenoming". This gives a
[0.25, 2] h window for **Russell's viper local swelling** only. Saw-scaled viper swelling already has a
cited window. Pain is described as "immediately" with no upper bound. A cobra figure
caption (Bawaskar 2004, n=1) is not an onset.

Used as a **cited-alternative sensitivity** (`configs/sim_v2_viper_swelling.yaml`), not in the primary
table. That is because the statement is secondary, not species-specific, and the 2 h bound is a rule of thumb.
Effect (test split, 3 model seeds; SIMULATION):

| model | sim_v2 macro-F1 / critical error | with cited Russell's viper swelling window |
|---|---|---|
| rule | 0.571 / 0.347 | 0.579 / 0.295 |
| xgboost | 0.654 / 0.347 | 0.693 / 0.294 |
| xgboost_context | 0.689 / 0.248 | 0.718 / 0.196 |
| logistic_regression | 0.644 / 0.347 | 0.688 / 0.295 |
| random_forest | 0.651 / 0.339 | 0.688 / 0.292 |

Envenomed Russell's viper patients with nothing observable at presentation fall from 40% to 17.5%.
So the cited evidence alone moves critical error to about 0.29. The fully assumed window for all four
rows (`sim_v2_early_local`) gives about 0.12.

**Decision (2026-11-07, project lead): keep as sensitivity only.** The secondary window is not
adopted in the primary table, and sim_v2 stays the primary dataset. Revisit if a species-specific
source is found. A clinician estimate (docs/clinician_priority_review.md) or cohort data
(docs/outreach_drafts.md) would settle it better.

## How the rows are used (observed vs label-only)

- In the primary dataset (`sim_v2`, `unknown_onset: label_only`) these symptoms occur at the cited
  frequency and **count toward the venom-syndrome label**, but have **no onset time and are never
  part of the model input** (`onset_unknown=True` in events.csv; enforced by `build_sequences` and
  `tests/test_leakage.py`). They are "label-only", as distinct from "observed" symptoms, which have a
  cited onset and are visible when onset <= presentation time.
- Sensitivity variants: `sim_v1` (all unknown onsets filled with the assumed 0-24 h window) and
  `sim_v2_early_local` (these four rows only, assumed [0, 1.5] h by analogy with cited Echis
  swelling and Hypnale local-sign windows). Both are labelled `experiment_type: sensitivity`.

## Assumptions that materially affect results

Measured on `sim_v2` (all splits, SIMULATION):

- 4,049 of 11,405 envenomed simulated patients (35.5%) have **no observed symptom** at
  presentation. **3,097 of those (76%)** carry at least one of these four label-only signs. Among
  the affected species, the share with any of the four is 1.00 (Daboia), 1.00 (Naja) and 0.98 (Echis).
  So these patients are labelled envenomed because of a sign the model is never allowed to see.
  At the argmax they are critical errors. That is why critical error is about 0.35 for every model.
- Giving only these four rows an assumed early window (`sim_v2_early_local`) moves XGBoost from
  macro-F1 0.654 / critical error 0.347 to 0.784 / 0.124 (docs/phase2_results.md). That gap comes from
  the evidence gap. It is not a property of the models.
- Label-only status is itself an assumption: a real clinician would usually see local pain or
  swelling at presentation. The primary dataset is therefore deliberately pessimistic about early
  local signs. The sensitivity dataset is optimistic, and its window is assumed.
- Denominator choices (53/53, 49/53, 20/20, 46/48 as if among envenomed) and the mapping of
  "local reaction" to swelling (Naja) are interpretations recorded in the `evidence` column.

## Pending

1. Clinician verification of all four rows (`verified=False`), with priority on Naja local_swelling
   (abstract-only source, mapped term).
2. Real time-to-local-sign data: a clinician co-author, the Silva/Isbister cohort authors, Phillips
   1988 QJM or Warrell 2010 Lancet (library access). Review form: docs/clinician_priority_review.md and
   docs/clinician_onset_elicitation.csv; email drafts: docs/outreach_drafts.md.
3. Indian cohorts with per-sign counts (all four rows currently rest on Sri Lankan series).
