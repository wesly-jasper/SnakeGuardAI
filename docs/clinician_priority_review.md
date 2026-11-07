# Clinician review: priority rows and onset elicitation (2026-11-07)

For a clinician who manages snakebite in South Asia. About 30-45 minutes. This is a
review of a **research simulator's input table**. It is not a clinical study and uses no patient data.
Nothing here will be used to treat anyone.

Why your input matters: the simulator draws synthetic patients from published frequencies and
onset times. For several common early signs the literature gives **how often** they occur but
not **when** they first appear, so the simulator cannot make them visible at presentation. That
single gap moves the main safety metric (envenomed patients missed) between about 12% and 35% in
our simulations (docs/evidence_audit_local_signs.md). An expert estimate would be recorded as
`expert opinion`, kept separate from published evidence, and used only in labelled sensitivity
analyses unless a published source is found.

Full list of all 145 rows to check against the sources: docs/verification_checklist.md.

## Part A: onset elicitation (most important)

Fill in `docs/clinician_onset_elicitation.csv`, one row per sign. For each, think of envenomed
adult patients bitten by that species in your region who **will** develop the sign:
- `typical_onset_min`: the usual time from bite to the sign being noticeable (minutes).
- `earliest_min` / `latest_min`: the range that covers about 9 in 10 such patients.
- `confidence_1_to_5`, `region_and_setting`, `n_patients_seen_roughly`, `comments`.

Leave a row blank if you have not managed enough such bites. "I don't know" is a useful answer.

| tier | species | sign | published frequency (source) | why it matters |
|---|---|---|---|---|
| 1 | Russell's viper (*Daboia russelii*) | local pain | 53/53 envenomed (kularatne2014revisiting, Sri Lanka) | no onset in any source we could read |
| 1 | Russell's viper | local swelling | 49/53 (same) | only a general viper statement exists: "within 15 minutes", absent at 2 h = no envenoming (mehta2002clinical, citing Warrell 1996) |
| 1 | Spectacled cobra (*Naja naja*) | local swelling | 20/20 envenomed, "local reaction" (kularatne2009cobra, abstract only) | no onset; the mapping "local reaction = swelling" also needs checking |
| 1 | Saw-scaled viper (*Echis carinatus*) | local pain | 46/48 bites (gnanathasan2012sawscaled, Sri Lanka) | no onset |
| 2 | Cobra | local necrosis | 0.40 | no onset |
| 2 | Saw-scaled viper | systemic bleeding | 0.29 | no onset |
| 2 | Hump-nosed pit viper (*Hypnale*) | blistering, regional lymphadenopathy | 0.67, 0.45 | no onset |
| 2 | Common krait (*Bungarus caeruleus*) | abdominal pain | 0.91; window 0-4 h from low-quality sources | check the window |

## Part B: frequencies and labels (quick yes / no / correction)

1. Do the tier-1 frequencies above look right for **Indian** patients? All four rest on Sri Lankan
   series, and the Sri Lankan saw-scaled viper is described as milder than Indian *E. c. sochureki*.
2. Dry-bite rates used: cobra 0.20, krait 0.045, Russell's viper 0.036, saw-scaled viper 0.075,
   hump-nosed viper 0.086. Plausible for your setting?
3. Syndrome labels: a patient with both bleeding and neurotoxic signs (Russell's viper in South
   India / Sri Lanka) is labelled haemotoxic. Do you agree with that precedence for triage?
4. Local-only: an envenomed patient with only local signs is labelled "local-only". Is this a
   meaningful triage class in your practice?

## Part C (optional): blinded vignettes

40 simulated patients, as seen at presentation, to rate for realism and to guess the syndrome
(docs/clinician_review_protocol.md).

## How answers are used

- Expert onset windows are entered as `onset_basis = expert opinion` with the reviewer's initials
  and date. They are never mixed into the primary evidence-only dataset without a citation.
- Corrections to cited rows are checked against the source and then marked `verified=true`.
- Reviewers are acknowledged (or co-authors, by agreement). Disagreements between reviewers are
  reported, not averaged away.
