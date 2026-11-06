# Phase 1 plan: clinical knowledge table + synthetic patient simulator

Goal: a cited, auditable knowledge base for the target species and a simulator that
samples synthetic patients from it, so Phase 2 baselines can be trained and evaluated.
Everything the simulator produces is **simulation data**.

## 1. Knowledge base (knowledge/)

Three tables instead of one, so each fact has exactly one home:

| file | one row per | key columns |
|---|---|---|
| `symptoms.csv` | symptom in the controlled vocabulary | `symptom`, `marker` (neurotoxic / haemotoxic / local / none), `definition` |
| `species.csv` | species | `species`, `common_name`, `group` (venomous / non-venomous), `dry_bite_rate`, `source_key` |
| `clinical_table.csv` | (species, symptom) | `onset_min_hours`, `onset_max_hours`, `frequency`, `source_key`, `evidence`, `verified` |
| `context_table.csv` | (species, context feature) | `value`, `probability`, `source_key`, `evidence`, `verified` |

Rules:
- `source_key` may list several keys separated by `;` (e.g. frequency from a case series,
  onset window from a guideline). Every key must exist in `sources.bib`.
- `evidence` holds the locator and a short verbatim quote (table/page) so a reviewer can
  check the number against the PDF.
- `verified` is `false` until a human has checked the number against the source PDF.
  AI-assisted extraction is a draft, never final.
- Frequencies are among *envenomed* patients in the source series; dry bites are handled
  separately through `dry_bite_rate`.
- Onset window conversion (documented per row): reported range -> range; median + IQR ->
  IQR; guideline text only ("within 1-6 h") -> the stated window.

## 2. Literature extraction

Sources, preferring authenticated (snake identified) case series from South Asia:
- Guidelines: WHO SEARO snakebite guidelines (2nd ed., 2016); Indian national snakebite
  protocol / standard treatment guidelines.
- Spectacled cobra and common krait: authenticated case series from India / Sri Lanka.
- Russell's viper and saw-scaled viper: Indian and Sri Lankan case series.
- Hump-nosed pit viper: authenticated Sri Lankan / South Indian series.
- Non-venomous lookalikes (rat snake, wolf snake, checkered keelback): bite reports,
  plus dry-bite rates for venomous species.
- Context: time of day, indoor/outdoor, asleep at time of bite (krait night bites are a
  key signal).

## 3. Simulator changes (src/data/simulator.py)

1. **Label from the full course, input censored at presentation.** Sample the patient's
   whole symptom course, derive the *eventual* venom syndrome from it, then keep only events
   before presentation as model input. This is the clinically useful task: predict the
   syndrome before it is fully expressed.
2. **Syndrome rule** (configurable): haemotoxic marker present -> haemotoxic; else
   neurotoxic marker -> neurotoxic; else local marker -> local-only; else
   non-venomous/dry. Haemotoxic wins over neurotoxic because Russell's viper can cause
   both and the coagulopathy drives the triage pathway. *Needs sign-off.*
3. **Dry bites:** with probability `dry_bite_rate` a venomous species produces no
   envenoming symptoms (label `non-venomous/dry`, species label kept).
4. **Context:** sample time of day, indoor/outdoor and asleep from `context_table.csv`.
   GPS and month stay uniform placeholders until the Phase 3 geo prior.
5. **Generation CLI + config:** `python -m src.data.generate --config configs/sim_v1.yaml`
   writes `data/processed/sim_v1/{patients.parquet,events.parquet,meta.json}`; `meta.json`
   records config, seed, git commit, table hashes and a `SIMULATED` flag.
6. **Fixed splits:** train / calibration / test assigned at generation time (calibration
   set reserved for Phase 6 conformal).

## 4. Sanity checks (tests + a short report)

- Unit tests for every transform (loader, syndrome rule, dry bites, censoring, context, CLI).
- Real-table test: `require_citations=True` passes once the table is filled.
- Simulator report: per-species symptom rates vs. table frequencies, syndrome mix,
  and a rule-based syndromic-table baseline on simulated data (labelled as simulation).

## Done when

- Every target species has rows for its key symptoms, every row cited, with evidence text.
- All rows are `verified=true` after human review against PDFs.
- `generate` produces a reproducible dataset; tests pass.

## Status (2026-11-06): engineering complete, human verification pending

Done:
- Schema, loader, simulator (course labels, censoring, dry bites, context), generation CLI,
  sanity report with rule-based baseline (`report.md` per dataset), verification checklist
  (`python -m src.data.checklist` -> `docs/verification_checklist.md`). 42 tests pass.
- Two extraction passes (`knowledge/extraction/*.md`) merged into the tables: 52 clinical rows
  (50 with a frequency), 20 context rows, 5 dry-bite rates, 43 BibTeX entries.
- Onset windows: 23 active rows have a cited window or cited bound. "Within X h" statements
  become [0, X] (or [0.5, X] for krait neurotoxic signs, after the first sign, ptosis, at 0.5 h).
  The remaining 27 rows use the configurable fallback window 0-24 h (`onset_fallback` in
  `configs/sim_v1.yaml`, cited to mohfw2017stg's 24 h observation rule). Set it to null to drop them.
- Context table: krait, cobra, Russell's viper and pooled non-venomous rows are now derived from
  the Wijayasekara 2026 raw data (S1 Appendix, 4,708 bites, CC BY 4.0) by
  `python -m src.data.wijayasekara <Data.xlsx>`; exact n/N in each row's evidence. Hump-nosed
  viper stays on ariaratnam2008frequent (species-confirmed; the raw data is genus-level).
- Patient-level datasets found but not yet usable from scripts (Newcastle repository blocks
  automated download; get them in a browser): Silva 2016 krait (per-patient neurological timings,
  all rights reserved: ask the authors before use), Silva 2016 Russell's viper myotoxicity
  (all rights reserved), Ratnayake 2019 Russell's viper AKI time course (CC BY 4.0).
- sim_v1 (20k patients, SIMULATED): simulated rates match table frequencies within 0.03; the
  rule-based baseline on the test split gives accuracy 0.68, macro-F1 0.61, critical error 0.33
  (cited presentation delay; 0.84 / 0.81 / 0.14 under the old uniform 0.5-24 h placeholder).

Research-grade additions (2026-11-06):
- Symptom dependence: shared latent severity (Gaussian copula, `severity_correlation`, default
  0.5) links presence and earlier onset while keeping every cited marginal frequency and window.
- Cited onset order (`knowledge/onset_order.csv`): ptosis -> ophthalmoplegia -> bulbar ->
  respiratory / limb (mohfw2017stg, silva2016krait); krait abdominal pain before ptosis
  (kularatne1998krait).
- Automatic quote pre-check (`python -m src.data.quotecheck` -> `docs/quote_check.md`): of 94 rows (incl. 14 delay rows),
  53 quotes found in the open full text, 7 partial, 15 not found (mostly abstract-only access),
  19 without a quote. Not a substitute for human verification.
- Cited time to presentation (`knowledge/presentation_delay.csv`, loaded by
  `src/data/presentation.py`): delay bins from sajeethkumar2018clinical (n=1,500, North Kerala:
  12% < 1 h, 68% 1-6 h, 10% 6-24 h, 6% > 24 h), renormalised and sampled uniformly within each bin.
  This replaces the uncited uniform 0.5-24 h placeholder. Two readings are cited because the
  source sentence is ambiguous ('68% within 6 h' disjoint vs cumulative), plus a faster Sri
  Lankan paediatric profile (rathnayaka2022epidemiological, n=40). The '> 24 h' bin has no
  reported upper bound; `open_bin_max_hours: 48` is an assumption. sim_v1 presentation: median
  3.7 h, IQR 1.9-5.4 h.
- Sensitivity analysis (`python -m src.data.sensitivity --config configs/sensitivity_v1.yaml`,
  16 variants, 10k patients each, SIMULATED, rule-based baseline on the test split):
  - base (cited delay): accuracy 0.67, macro-F1 0.60, critical error 0.31. With the old uniform
    placeholder the same baseline gave critical error 0.145: most patients in the cited series
    present within 6 h, before many systemic signs appear, so the task is much harder than the
    placeholder suggested.
  - Delay: disjoint vs cumulative reading 0.309 vs 0.311; open-bin cap 48 vs 72 h no change;
    faster Sri Lankan paediatric profile 0.47.
  - Onset fallback window 0.23-0.33; severity correlation 0.26-0.32.
  - Dry-bite rates, syndrome precedence, cobra coagulopathy and Echis population each move it by
    <= 0.05.
- Clinician review kit (`python -m src.data.vignettes`, `docs/clinician_review_protocol.md`):
  blinded vignettes, rating form, answer key; can mix in real cases for a real-vs-simulated test.
- Tests: 90, passing on system Python (pandas 2.3) and the project .venv (pandas 3.1).

Next evidence priorities (from the sensitivity analysis):
1. Done: cited bite-to-presentation distribution (see above). Still open: a delay series from a
   second Indian region (e.g. pushpalatha2024study, not yet extracted) and per-species delays.
2. Real onset times (Silva 2016 krait dataset with permission; Ratnayake 2019 AKI, CC BY) to
   shrink the fallback rows and calibrate `severity_correlation`.

Remaining gate (human only):
- Check every row in `docs/verification_checklist.md` against the PDF and set `verified=true`,
  then set `require_citations: true` and `require_verified: true` in the config. Until then,
  every downstream result must say it rests on unverified draft extractions.
- PDFs needed (paywalled / abstract only): Kularatne 2002 (krait), Kularatne 2009 (cobra),
  Ariaratnam 2008 krait Table 2, Silva 2026 (cobra), Kularatne 2003 (Russell's viper),
  Ariaratnam 2009 (non-venomous bites), Thalgaspitiya 2020, Maduwage 2013, Kochar 2007,
  Kularatne 2011 (saw-scaled viper), Silva 2016 Clin Toxicol (Russell's viper neurotoxicity).

Source choices made in the merge (full text over abstract, authenticated over not, larger N,
envenomed denominators where the dry count is printed) are written in each row's `evidence`.

## Decisions taken as defaults (change in the CSVs / config)

- Syndrome precedence: haemotoxic > neurotoxic > local-only > non-venomous/dry.
- Saw-scaled viper: Sri Lankan *E. c. carinatus* series (mild). Rajasthan *E. c. sochureki*
  (severe, AKI common) is not modelled; AKI frequency is left blank because the sources conflict.
- Russell's viper dry-bite rate 4% (hospital series), not ~50% (WHO guideline).
- Cobra coagulopathy 3/20 kept as published, although its authors call it unverified; it makes
  about 12% of simulated cobra bites haemotoxic. Set the frequency to 0 to drop it.
- Non-venomous species share pooled (not species-specific) local-pain and context data
  (context from the 311 non-venomous bites in the Wijayasekara 2026 cohort).
- Species mix uniform; GPS and month uniform until the Phase 3 geo prior.
- Presentation delay: the same Kerala distribution for every species (no per-species series yet);
  'within 6 h' read as disjoint from 'within 1 h'.
- Kidney-injury onset uses the fallback: sources give creatinine curves, not onset times.
