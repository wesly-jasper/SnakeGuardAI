# Clinician review protocol: realism of simulated snakebite patients

Purpose: an external check that the simulator (src/data/simulator.py) produces patients a
clinician finds plausible, and that the syndrome is recognisable from the information
available at presentation. This is a face-validity check of SIMULATED data, not a clinical
study, and uses no patient data unless real cases are mixed in (see below).

## Raters

- 2-3 clinicians who manage snakebite in South Asia (emergency medicine, internal
  medicine or toxicology), recruited independently of the project team.
- Raters work alone and do not discuss cases until all forms are returned.

## Materials

Generate the kit from a frozen dataset:

```bash
python -m src.data.vignettes --dataset data/processed/sim_v2 --n 40 --out data/processed/review_v2
```

- `vignettes.md`: blinded cases (no species, no label, no source), order shuffled. Only
  symptoms up to presentation are shown; later events would reveal the label.
- `rating_form.csv`: one row per case: `realism_1_to_5`, `syndrome_guess`
  (neurotoxic / haemotoxic / local-only / non-venomous-dry), `confidence_1_to_5`, `comments`.
- `answer_key.csv`: kept by the study lead only (includes `n_hidden_later_events`).

Record the dataset's `meta.json` git commit with the results.

## Optional: blinded real-vs-simulated test

If real cases become available with permission (e.g. the Silva 2016 krait dataset, after
the authors agree), convert them to the `patients.csv` / `events.csv` format and add
`--real <folder>`. Raters are told only that some cases may be real. Add a column
`real_or_simulated` to the form for this round.

## Analysis

- Realism: median and distribution per syndrome and per source; flag every case rated 1-2
  and read the comments, which point to specific knowledge-table rows or simulator rules.
- Syndrome recognition: rater accuracy against the answer key, compared with the
  rule-based baseline on the same cases (`src/data/report.py`).
- Inter-rater agreement: Cohen's (2 raters) or Fleiss' (3+) kappa for syndrome guesses,
  weighted kappa for realism.
- Real-vs-simulated round: rater accuracy at telling them apart (50% = indistinguishable).

## Acting on the results

Each issue raised becomes a change to a cited table row or a documented simulator rule,
followed by a new dataset version (sim_v2, ...). Report the review with the dataset version
it applies to. Do not tune the simulator to the raters without a citation or a documented
rationale.
