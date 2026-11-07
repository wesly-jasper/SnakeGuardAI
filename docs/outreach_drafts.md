# Outreach drafts (to send yourself; not sent)

Drafts for the three evidence steps that need people rather than code. Fill in `[...]`. Take
contact addresses from each paper's corresponding-author details; none are guessed here.
Attach or link docs/clinician_priority_review.md where useful.

## 1. Cohort authors: time to first local sign

**To:** corresponding author of Silva et al. 2016 (Sri Lanka, 245 confirmed bites; neurotoxicity /
myotoxicity cohort), and Prof. G. K. Isbister.
**Subject:** Request: time from bite to first local pain / swelling in your confirmed-bite cohort

> Dear Dr [name],
>
> I am [name], working on SnakeGuard AI, a non-commercial research prototype that studies whether
> the venom syndrome of a snakebite can be estimated from symptoms and their timing when the snake
> is not identified. It is not a clinical tool. It is built from a table of published frequencies
> and onset times, each with a citation.
>
> Your cohort reports bite-site pain and swelling in nearly all confirmed bites. We could not find a
> published distribution of **time from bite to first local pain or swelling**, for Russell's viper,
> cobra or saw-scaled viper, in your papers or elsewhere. This one parameter changes our simulated
> missed-envenoming rate between roughly 12% and 35%.
>
> Would you be willing to share, for confirmed bites by species, either (a) the median and
> range or IQR of time from bite to first local sign, or (b) the proportion with local pain or swelling
> already present at admission, together with the bite-to-admission time? Aggregate numbers are
> enough. We would cite them as a personal communication or your preferred source, and would be
> glad to offer co-authorship if you would like to be more involved.
>
> With thanks, [name, affiliation, contact]

Variant for **Prof. S. A. M. Kularatne** (Russell's viper series: kularatne2014revisiting, 55 proven;
Kularatne 2003, 336 patients; cobra series kularatne2009cobra): the same request, plus (for the cobra
series) whether "local reaction" meant swelling, pain or both.

## 2. Clinician reviewer or co-author

**To:** [emergency / internal medicine / toxicology clinician in India managing snakebite]
**Subject:** 30-45 minute expert review for a snakebite triage research prototype

> Dear Dr [name],
>
> We are building a research prototype that estimates snakebite venom syndrome from symptoms
> and timing, with calibrated uncertainty, for settings where the snake is not seen. It is not a
> medical device and makes no treatment recommendations.
>
> The weakest point is clinical judgement that the literature does not record: how soon early local
> signs appear for each species. Would you be willing to complete a short form
> (clinician_priority_review.md and clinician_onset_elicitation.csv, attached), giving your
> typical and range of onset times for nine signs, and to flag any published frequency that looks
> wrong for Indian patients? Your answers would be recorded as expert opinion, kept separate from the
> published evidence, and acknowledged; co-authorship is possible for continued involvement.
>
> With thanks, [name, affiliation, contact]

Aim for 2-3 independent reviewers, so their agreement can be measured.

## 3. Hospital partner for retrospective data (later; needs ethics approval)

Outline to discuss with a hospital partner. No data are requested before approval.

- **Design:** retrospective review of snakebite admissions with the snake identified (specimen,
  photo confirmed by an expert, or venom assay), or with a clear syndromic diagnosis.
- **Approvals:** Institutional Ethics Committee approval at the hospital, waiver of consent for
  de-identified retrospective data where the committee allows it, and a data-sharing agreement.
  Data stay de-identified: no names, exact dates or addresses; district-level location only.
- **Variables:** they mirror the simulator format (data/processed/*/patients.csv, events.csv):
  - species and how it was identified;
  - bite time, admission time, and time of first record of each sign (local pain, swelling,
    ptosis, 20WBCT result, bleeding, etc.);
  - indoor/outdoor and asleep at the time of the bite, month, district;
  - final syndrome, and whether antivenom was given (recorded only as an outcome label, never as
    a model output).
- **First use:** evaluate the Phase 2 models on real cases (external test only, no retraining),
  and estimate the real onset windows that the knowledge table lacks.
- **Out of scope:** any use for patient care, and any dosing or treatment output.
