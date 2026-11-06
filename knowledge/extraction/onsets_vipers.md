# Onset-time extraction: Russell's viper, saw-scaled viper, hump-nosed pit viper

Draft, AI-assisted extraction (Phase 1, onset pass). **Every row is unverified** until a human
checks it against the source (`verified=false`). Symptom names follow `knowledge/symptoms.csv`.
This pass only adds what `vipers.md` and `hypnale_nonvenomous.md` did not already record.

How the sources were read (2026-11-05):
- **Full text read directly** (Europe PMC full-text XML, tags stripped, searched for every
  minutes/hours/days statement): kularatne2014revisiting (PMC3936006), silva2016myotoxicity
  (PMC5135039), lath2024strikes (PMC11408150), rathnayaka2022epidemiological (PMC9822102),
  abraham2025single (PMC12020926), sajeethkumar2018clinical (PMC5993036), bawaskar2019diagnosis
  (PMC6510103), ratnayake2019early (PMC6625728), wijewickrama2021serum (PMC8675918),
  vikrant2017clinicopathological (PMC5424437), pushpalatha2024study (PMC11668472),
  senthilkumaran2021ngal (PMC8620021).
- **PDF read directly** (pdftotext): ariaratnam2008frequent (Colombo repository PDF),
  who2016guidelines (WHO SEARO PDF), mohfw2017stg and mohfw2016stg (MoHFW PDFs).
- **Read through WebFetch** (exact quotes requested): gnanathasan2012sawscaled (PMC HTML; the
  Europe PMC XML returned HTTP 500), gopalakrishnan2025antivenom (publisher HTML, first 100k chars).
- **Abstract only** (Europe PMC abstract; full text paywalled or blocked): kularatne2011revisiting
  (OUP page confirmed abstract only by a second WebFetch), silva2016neurotoxicity (Tandfonline 403),
  kularatne2003russell, rathnayaka2019kidney, herath2012thrombotic, wijewickrama2021severe,
  witharana2021hump, joseph2007first, sirur2022hump, wedasingha2025utility.
- Ariaratnam 2009 syndromic survey (AJTMH 81:725) could not be opened (HTTP 403); not used.

Conversion: minutes / 60, rounded to 2 decimals. Days x 24.

## 1. Onset table

| species | symptom | onset_min_h | onset_max_h | onset_basis | source_key | locator | verbatim quote | notes |
|---|---|---|---|---|---|---|---|---|
| Echis carinatus (Sri Lanka, Jaffna) | incoagulable_blood | 0.67 | 18.25 | range | kularatne2011revisiting | Abstract [abstract only] | "In 24 patients (92%), blood incoagulability manifested between 40 and 1095min after the bite, and three patients (12%) developed spontaneous bleeding." | 40 min = 0.67 h; 1095 min = 18.25 h. N = 26 confirmed bites (2 dry). Same quote returned by a second WebFetch of the OUP page. Abstract gives no onset for the 3 bleeding cases. |
| Echis carinatus (India, Maharashtra) | local_swelling | | 1.5 | upper_bound | bawaskar2019diagnosis | Discussion, paragraph after Figures 4-6 | "Soon after envenoming by Echis carinatus species, within one 60-90 minutes there is progressive swelling over the bitten part." | Narrative statement citing refs [5,7,8,25], not a measured series value. "Within 60-90 minutes" taken as an upper bound of 1.5 h (could be read as 1.0 h). "Progressive swelling over the bitten part" maps to local_swelling (bitten segment), not progressive_swelling. Typo "within one 60-90" is in the source. |
| Echis carinatus (India, Maharashtra) | regional_lymphadenopathy | | 1.5 | upper_bound | bawaskar2019diagnosis | Discussion, same paragraph | "Within 60-90 minutes victim experiences a painful lymphadenopathy at drainage area of the bitten part." | Not on the requested list (no Echis lymphadenopathy row in clinical_table.csv yet); recorded for completeness. Narrative, cited to refs. |
| Daboia russelii | ophthalmoplegia | | 8 | upper_bound | silva2016neurotoxicity | Abstract, Results [abstract only] | "Neurotoxicity was characterised by ptosis (100%), blurred vision (93%), and ophthalmoplegia (90%) with weak extraocular movements, strabismus, and diplopia. Neurotoxicity developed within 8 h post-bite in all patients." | Already in vipers.md; re-read today from the Europe PMC abstract. The 8 h bound is for neurotoxicity overall, so it applies to both ptosis and ophthalmoplegia. Full text (Tandfonline) blocked, so no lower bound or median found. |
| Daboia russelii | acute_kidney_injury | | | (proxy only; not an onset window) | ratnayake2019early | Results, time-course paragraph (Fig 4, S3 Fig) | "Serum creatinine increased over the first 8 to 16 h in patients with moderate to severe AKI (AKIN stage 2/3), with a median peak sCr occurring between 8 to 16h post-bite" | Creatinine trajectory, not a clinical onset time. 49/65 confirmed (EIA) envenomings developed AKI. If a reviewer accepts a proxy: creatinine rise 0-16 h, median peak 8-16 h. Left blank on purpose. |
| Hypnale spp. (venom EIA; genus level) | acute_kidney_injury | | | (proxy only; not an onset window) | wijewickrama2021serum | Results, "Time dependent changes in absolute and median biomarker concentrations" | "Serum creatinine increased over the first 4–8 h post-bite in patients with moderate/severe AKI, with the median sCr continuing to rise at 24–48 h" | Genus Hypnale (EIA cannot separate species). 12/52 developed AKI. Proxy only: creatinine rising from 4-8 h, still rising at 24-48 h. Left blank on purpose. |
| Haemotoxic snakebite, generic (India review; RV, SSV, HNPV, green pit viper, sea snake) | acute_kidney_injury | | 96 | upper_bound | vikrant2017clinicopathological | Introduction, para 2 | "The onset of AKI is from a few hours to as late as 96 h after the bite." | Review statement, not species-specific, no lower bound in numbers ("a few hours"). Use only as a generic fallback cap. |
| Snakebite AKI, generic (India series, species not identified) | acute_kidney_injury | | 48 | upper_bound | pushpalatha2024study | Discussion | "AKI is usually associated with oliguria and generally occurs within 48 hours" | "Generally", not all patients. No species identification. The paper says it studied "time of onset" but reports only bite-to-hospital lag (Table 1), not onset. |

### Case-level observations (single patients; not suitable as windows)

| species | symptom | time after bite (h) | source_key | locator | verbatim quote | notes |
|---|---|---|---|---|---|---|
| Hypnale hypnale (confirmed, Kerala) | systemic_bleeding (haematuria) + incoagulable_blood | 18 | abraham2025single | Results, "Mortality" | "Even though initially the blood clotted normally, the patient had profound venom-induced consumptive coagulopathy at 18 h postbite and hematuria." | n = 1 (fatal case). Time when found, not necessarily onset. |
| Hypnale hypnale (same patient) | acute_kidney_injury | before ~53 | abraham2025single | Results, "Mortality" | "She developed breathing difficulty, acute kidney injury which resulted in cardiopulmonary failure, and had a cardiopulmonary arrest at about 53 h postbite" | n = 1; AKI onset only known to be before the 53 h arrest. Pre-existing atrial fibrillation. |
| Daboia russelii (Sri Lanka) | dark urine (haemoglobin/myoglobin; not in vocabulary) | 8 | who2016guidelines | Section on clinical features, Figure 67 caption, PDF p. 103 | "She began to pass dark brown urine containing myoglobin and haemoglobin 8 hours after the bite." | n = 1 figure caption. Not mapped to a vocabulary symptom. |

## 2. BibTeX for new sources

```bibtex
@article{kularatne2011revisiting,
  author  = {Kularatne, S. A. M. and Sivansuthan, S. and Medagedara, S. C. and Maduwage, K. and de Silva, A.},
  title   = {Revisiting saw-scaled viper ({Echis carinatus}) bites in the {Jaffna} {Peninsula} of {Sri Lanka}: distribution, epidemiology and clinical manifestations},
  journal = {Transactions of the Royal Society of Tropical Medicine and Hygiene},
  year    = {2011},
  volume  = {105},
  number  = {10},
  pages   = {591--597},
  doi     = {10.1016/j.trstmh.2011.07.010},
  note    = {PMID 21868049. Only the abstract was read},
  url     = {https://europepmc.org/article/MED/21868049}
}

@article{bawaskar2019diagnosis,
  author  = {Bawaskar, Himmatrao S. and Bawaskar, Pramodini H.},
  title   = {Diagnosis of envenomation by {Russell's} and {Echis carinatus} viper: a clinical study at rural {Maharashtra} state of {India}},
  journal = {Journal of Family Medicine and Primary Care},
  year    = {2019},
  volume  = {8},
  number  = {4},
  pages   = {1386--1390},
  doi     = {10.4103/jfmpc.jfmpc_156_19},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC6510103/}
}

@article{ratnayake2019early,
  author  = {Ratnayake, Indira and Mohamed, Fahim and Buckley, Nicholas A. and Gawarammana, Indika B. and Dissanayake, Dhammika M. and Chathuranga, Umesh and Munasinghe, Mahesh and Maduwage, Kalana and Jayamanne, Shaluka and Endre, Zoltan H. and Isbister, Geoffrey K.},
  title   = {Early identification of acute kidney injury in {Russell's} viper ({Daboia russelii}) envenoming using renal biomarkers},
  journal = {PLoS Neglected Tropical Diseases},
  year    = {2019},
  volume  = {13},
  number  = {7},
  pages   = {e0007486},
  doi     = {10.1371/journal.pntd.0007486},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC6625728/}
}

@article{wijewickrama2021serum,
  author  = {Wijewickrama, Eranga Sanjeewa and Mohamed, Fahim and Gawarammana, Indika B. and Endre, Zoltan H. and Buckley, Nicholas A. and Isbister, Geoffrey K.},
  title   = {Serum and urinary biomarkers for early detection of acute kidney injury following {Hypnale} spp. envenoming},
  journal = {PLoS Neglected Tropical Diseases},
  year    = {2021},
  volume  = {15},
  number  = {12},
  pages   = {e0010011},
  doi     = {10.1371/journal.pntd.0010011},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC8675918/}
}

@article{vikrant2017clinicopathological,
  author  = {Vikrant, Sanjay and Jaryal, Ajay and Parashar, Anupam},
  title   = {Clinicopathological spectrum of snake bite-induced acute kidney injury from {India}},
  journal = {World Journal of Nephrology},
  year    = {2017},
  volume  = {6},
  number  = {3},
  pages   = {150--161},
  doi     = {10.5527/wjn.v6.i3.150},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC5424437/}
}

@article{pushpalatha2024study,
  author  = {Pushpalatha, Avunoori and Itagi, Afreen Begum H. and Vamshidhar, Immadi S. and Rani, S. S. Sabitha and Kalpana, Medala and Vidya, Ganji},
  title   = {A study of clinical profile and outcome of patients with snake bite-induced acute kidney injury},
  journal = {Journal of Family Medicine and Primary Care},
  year    = {2024},
  volume  = {13},
  number  = {11},
  pages   = {5301--5305},
  doi     = {10.4103/jfmpc.jfmpc_784_24},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC11668472/}
}
```

Existing keys reused: silva2016neurotoxicity, abraham2025single, who2016guidelines.

## 3. Gaps (searched, not found)

**Daboia russelii**
- local_pain, local_swelling, blistering, local_necrosis: no number. kularatne2014revisiting and
  silva2016myotoxicity full texts give no onset times for local signs. bawaskar2019diagnosis says only
  "development of rapid swelling extending more than one segment of bitten part within few hours"
  (no number).
- systemic_bleeding, shock: not found in any source read (kularatne2014revisiting gives bleeding counts
  only; WHO and MoHFW give no viper-specific times).
- acute_kidney_injury: only the creatinine proxy above. kularatne2014revisiting says renal failure
  can develop "many hours after the bite" (no number). senthilkumaran2021ngal (PMC8620021) only states
  in general terms that creatinine rises "from approximately 24 to 48 h following the renal injury"
  (cited background, not an onset); not used.
- ptosis / ophthalmoplegia: only the 8 h upper bound (abstract). Full text of silva2016neurotoxicity
  is blocked; no lower bound or median.

**Echis carinatus**
- local_pain, systemic_bleeding, vomiting, abdominal_pain, acute_kidney_injury: not found.
  gnanathasan2012sawscaled full text has no onset times (only "blood became coagulable within 6 hours"
  after antivenom, and an illustrative case whose swelling peaked "on the third day").
  gopalakrishnan2025antivenom times are from antivenom or "day 5/7" lab checks, not onset.
  kularatne2011revisiting abstract gives no onset for its 3 bleeding cases or 1 renal case.
- Note subspecies: kularatne2011revisiting is Sri Lankan E. c. carinatus; bawaskar2019diagnosis is
  Maharashtra (subspecies not stated).

**Hypnale hypnale**
- progressive_swelling, blistering, local_necrosis, regional_lymphadenopathy: no onset number.
  rathnayaka2022epidemiological figure captions show blisters/necrosis "on day 2"/"day 3", but these are
  photo days, not onset. ariaratnam2008frequent full text has no onset times except coagulopathy.
  abraham2025single: "More than 95% of the individuals in this study had a local sign, within the
  first couple of hours of the bite" (any local sign; numeric IQR already in hypnale_nonvenomous.md).
- WHO (p. 133) "Local swelling involving more than half of the bitten limb ... within 48 hr of the
  bite" is an antivenom-indication criterion, not an onset statement; not used.
- systemic_bleeding, acute_kidney_injury: only the single-case times and the creatinine proxy above.
  rathnayaka2019kidney (465 patients, 44 AKI) and herath2012thrombotic report no onset times in the
  abstract; full texts paywalled.
- abdominal_pain, vomiting, headache: not found. wedasingha2025utility (abstract) reports these only
  as "on admission" (10/89 hump-nosed viper bites had any non-specific symptom), with no hours.
- mohfw2016stg/mohfw2017stg statement that hump-nosed pit viper symptoms "can develop after 6-12 hours"
  sits in the neuroparalytic section; already flagged and not used in hypnale_nonvenomous.md.

**General**
- WHO 2016 (searched every page for time statements): only "A common early symptom of systemic
  envenoming is vomiting" (no number) and the generic coagulopathy-within-30-minutes statement
  already in vipers.md.
- Not accessible: Ariaratnam 2009 AJTMH syndromic survey (403), Warrell 2010 Lancet, Phillips 1988 QJM,
  Rathnayaka 2019 TRSTMH kidney paper, Silva 2016 Clin Toxicol full text.

## 4. Second search for early local-sign onsets (2026-11-06, Phase 2 follow-up)

Motivation: Phase 2 (docs/phase2_results.md) showed that Russell's viper local_pain (1.00) and
local_swelling (0.925) and saw-scaled viper local_pain (0.958) are label-only in sim_v2 (no cited
onset), so no model ever sees them. Searched again for a since-bite onset. **Nothing citable found.**

- Cached full texts (data/raw/fulltext_cache/*.txt) re-grepped for timing phrases near pain/swelling
  and for local signs "on admission": none with a since-bite time for these rows.
- kularatne2014revisiting (PMC3936006): admission median 28 min (range 10-180) and Table 2 swelling
  49/55, but Table 2 covers the whole admission, not findings on admission, so it is not an upper
  bound. The score item "Onset within 30 minutes of bite" belongs to abdominal pain.
- Isbister et al. 2015 PLoS NTD (10.1371/journal.pntd.0003968, 146 EIA-confirmed bites): "Local effects
  were reported in 134 (91%) patients"; no per-sign counts, no admission findings, no onset times.
- Silva/Isbister 2016 neurotoxicity cohort (245 bites, median presentation 2.5 h): abstract gives
  "bite site pain and swelling in 244/245" with no onset; full text blocked (Clin Toxicol).
- Saw-scaled viper TMA case report (PMC8283212): n=1, no bite-to-admission time.
- Search snippets mention a 15-patient Echis series with pain 15/15 and swelling 14/15 "on admission";
  source not identified, so not recorded.
- Not used (wrong species or region): Merck/AAFP/NOLS statements on North American pit vipers
  (swelling 30-60 min); Hong Kong Naja atra series (swelling "within 4 hours").

A sensitivity dataset with an ASSUMED [0, 1.5] h window for these rows (by analogy with the cited
Echis swelling and Hypnale local-sign windows) is configs/sim_v2_early_local.yaml.
Best next step: ask a clinician co-author or the Silva/Isbister cohort authors for time-to-local-sign
data, or read Phillips 1988 QJM / Warrell 2010 Lancet in a library.
