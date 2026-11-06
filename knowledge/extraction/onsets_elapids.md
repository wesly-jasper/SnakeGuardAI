# Onset-time extraction: elapids + non-venomous (Bungarus caeruleus, Naja naja, non-venomous bites)

Status: AI-assisted DRAFT (2026-11-05). Nothing here is verified. A human must check every row
against the source before it goes into `clinical_table.csv` (`verified=false` until then).
This pass adds to `knowledge/extraction/elapids.md` and does not repeat what that file found.
Rows already there, such as ariaratnam2008krait ptosis 0.5-4 h, silva2016krait bulbar <=7 h, limb <=8 h,
mohfw2017stg cobra 0.5-6 h, krait "after 6-12 hours", the occult-bite sequence, and "In Cobra bite on finger,
necrosis may start in few minutes", are only mentioned again where a new source agrees or disagrees with them.

How the sources were read:
- **Full text read directly** (PDF via `pdftotext`, or Europe PMC full-text XML stripped to text, then
  grepped and read by me): who2016guidelines (CDN PDF), mohfw2017stg (NCDC PDF), silva2016krait
  (PMC4734751 XML), kularatne1998krait (CJMS PDF), mandal2023krait (Semantic Scholar PDF),
  faiz2017monocled (PMC5392636 XML), alirol2010snake (PMC2811174 XML), ranawaka2013neurotoxicity
  (PMC3794919 XML, Table 3 parsed), kohli2007snake (Indian Pediatrics PDF).
- **WebFetch summary only** (the small model returned quotes. I checked one key sentence with a second
  prompt): pannu2024lowdose (PMC page. Europe PMC XML returned HTTP 500).
- **Abstract only**: seneviratne2002neurological (Europe PMC abstract).
- PDF page numbers ("PDF p.") are pages in the downloaded PDF, as counted by `pdftotext` form feeds. Printed
  page numbers are given where the page header could be read.
- Units: hours. Minutes are converted to hours (2 decimals). Days are converted to hours only where
  marked.

## 1. Species-specific onset rows

| species | symptom | onset_min_h | onset_max_h | onset_basis | source_key | locator | verbatim quote | notes |
|---|---|---|---|---|---|---|---|---|
| Bungarus caeruleus | ophthalmoplegia | | 12 | upper_bound | silva2016krait | Results, mild-neurotoxicity paragraph (after Table 2) | "All these patients had partial ptosis on admission. In one patient, this progressed to complete ptosis with partial ophthalmoplegia and mild facial weakness within 12h of the bite, but 2h after antivenom was given." | Single patient (mild group, n=8). Specimen-authenticated cohort. |
| Bungarus caeruleus | ophthalmoplegia | | 7 | upper_bound (derived) | silva2016krait | Abstract (Principal findings); Results | Abstract: "Seventeen patients developed severe neurotoxicity with rapidly descending paralysis, from ptosis to complete ophthalmoplegia, facial, bulbar and neck weakness. ... Despite this, the paralysis worsened requiring intubation and ventilation within 7h post-bite." | DERIVED: the paper does not give a separate ophthalmoplegia time. 7 h is the intubation upper bound, and ophthalmoplegia came before it in the described descending sequence. Severe group n=17 (complete ophthalmoplegia 14/17, Table 2). Use only if the reviewer accepts the inference. |
| Bungarus caeruleus | bulbar_palsy | | 12 | upper_bound (author inference) | silva2016krait | Discussion | "Based on this finding it appears that patients who do not develop bulbar weakness or respiratory paralysis within 12h of the bite, are highly unlikely to develop severe paralysis." | Authors' conclusion from n=33, not an observed maximum. The observed bound (<=7 h) is already in elapids.md. |
| Bungarus caeruleus | neuroparalysis (any; ptosis/bulbar/limb) | 0.5 | 50 | range (secondary, mode 6 h) | pannu2024lowdose | Discussion [WebFetch summary, quote confirmed with a second prompt] | "Clinical studies demonstrate the onset of neuroparalysis after a krait bite ranges from 0.5 to 50 h (mode 6 h)" | SECONDARY: cites Prasarnpun et al. 2005 Brain 128:2987 (ref [8]), which I could not read (paywalled; abstract has only rat data). The krait species behind the range is unknown. It may come from kularatne1998krait (ventilation 3-50 h). Do not use as a primary onset. |
| Bungarus caeruleus | neuroparalytic symptoms (any) | 3 | 24 | guideline (narrative, uncited) | mandal2023krait | Discussion, "General signs and symptoms of neurotoxic envenomation" (p. 107) | "Neuroparalytic snakebite patients present with typical symptoms within 30 mins-2 h in case of cobra bite and 3-24 h for krait bite; however, ptosis in krait bite has been recorded as late as 36 h after an incident of bite" | Background text, not the study's own data, and no citation on the bullet. Reworded from the STG text (which says 30 min-6 h for cobra and "after 6-12 hours" for krait), so it conflicts with mohfw2017stg. Indian (West Bengal) cohort n=52 with mixed identification (snake brought, or clinical plus neostigmine non-response). |
| Bungarus caeruleus | abdominal_pain | 2 | 4 | guideline (narrative, uncited) | mandal2023krait | Discussion bullet list (p. 107) | "Epigastric pain suggesting submucosal hemorrhage in the stomach (krait bite) [earliest presentation]. When a patient is unaware of the bite, he usually wakes up 2-4 h after the bite, due to severe colicky pain, mainly in the epigastrium." | No citation on this bullet. Low-quality evidence: the window is a narrative statement, not measured. |
| Bungarus caeruleus | abdominal_pain | | | qualitative ("within minutes to few hours") | kularatne1998krait | p. 55, "Clinical Features" | "Abdominal pain is the first symptom that manifests after krait bite, within minutes to few hours, and it might mimic a surgical abdomen." | Prospective, n=42, 29/42 snakes identified by the author. No number. It does put abdominal pain FIRST in the sequence (before ptosis). Table 1: abdominal pain on admission 64%. |
| Bungarus caeruleus | abdominal_pain -> ptosis interval | | | case report (bite time unknown) | kohli2007snake | p. 852, Case Report | "The patient was apparently well till 2:00 AM, when he developed constant, severe and poorly localized abdominal pain." ... presented with "sudden onset abdominal pain for three hours" ... "Twenty minutes after presenting to us, the pain intensified and the patient was also noticed to have bilateral ptosis." | n=1, Delhi, snake not identified (presumed krait). Ptosis about 3.33 h after PAIN onset, not after the bite. Not usable as a since-bite onset. Supports the order: abdominal pain, then ptosis. |
| Bungarus caeruleus | local_swelling / local_pain | | | not found (qualitative only) | kularatne1998krait | p. 55, "Clinical Features" | "Very often the site of bite and fang marks were indistinct and hardly produced a local reaction. But bites in fingers and hand invariably produced significant local reaction with swelling and pain." | No timing. Table 1 "Local reaction" 25% (all patients) on admission. |
| Bungarus caeruleus | respiratory_paralysis (extra; time bite -> ventilation) | 2 | 40 | range | kularatne1998krait | p. 56, "Respiratory paralysis" | "In this study the time lag to initiation of ventilation was found to have a wide range (2 to 40hr) for the whole group and 17(40%) patients needed ventilation within 10 hr after the bite." | CONFLICT inside the paper: the Summary says "17(40%) needed ventilatory support in 10 hr (range 3 to 50 hr), after the bite." Not a requested row. Kept for cross-checking ariaratnam2008krait (0.5-13 h). |
| Bungarus caeruleus | respiratory_paralysis (extra; bite -> ventilation) | | | iqr | pannu2024lowdose | Table 1 [WebFetch summary] | "Time interval between snakebite and initiation of mechanical ventilation (hr), median (IQR)" \| "7.5 (4.5-16)" \| "9.0 (4.75-16.75)" | 10-vial and 20-vial groups. Ventilated-only cohort, not authenticated. Not a requested row. Re-check against the PDF. |
| Naja naja | local_swelling | | | not found | - | - | - | No N. naja source with a swelling onset time could be read. kularatne2009cobra and silva2026cobra are paywalled (abstracts give no times). The STG has only "Rapid early extension of local swelling" with no number (PDF p. 26). |
| Naja naja | local_necrosis | | 120 | upper_bound (PROXY SPECIES, cumulative by day) | faiz2017monocled | Results, local envenoming paragraph | "Localized blistering and necrosis of the skin at or close to the bite site ( Figure 2C ) appeared during day 1 in four patients, thereafter increasing to six by day 2, nine by day 3 to peak at 19 by day 5." Also: "In three patients, there was local blistering with no signs of systemic neurotoxicity, and in one patient the blister first appeared 5 days after admission." | **Naja kaouthia (monocled cobra), Bangladesh, n=70 identified, NOT N. naja.** Earliest = "during day 1" (0-24 h, no finer time). Latest = by day 5 (<=120 h, computed as 5 x 24). Blistering and necrosis are counted together. The STG says necrosis "may start in few minutes" for finger bites (in elapids.md). |
| Naja naja | incoagulable_blood | | | not found | - | - | - | No species-specific timing. Proxy: faiz2017monocled has "two of the 70 patients had incoagulable blood, based on a 20WBCT" (N. kaouthia) with no time. General guideline statements are in section 2. |
| Ptyas mucosa / Lycodon aulicus / Fowlea piscator | local_pain | 0 | | guideline (generic, any snakebite) | who2016guidelines | Section 5.2.1 "Early symptoms and signs" (PDF p. 97, printed p. 93) | "Following the immediate pain of mechanical penetration of the skin by the snake's fangs, and the fear associated with such a terrifying experience as being bitten by a snake, there may be increasing local pain ..." | NOT species-specific: "immediate" pain from the teeth going in applies to any bite. No end time is given. dayasiri2025when (PMC12306283) and shahmy2017prospective (PMC5578683) were read and give no timing for non-venomous bites. thalgaspitiya2020bites full text could not be read (Elsevier blocked). |

## 2. General (non-species) onset statements in guidelines and reviews

| symptom / process | statement (verbatim) | onset_min_h | onset_max_h | onset_basis | source_key | locator |
|---|---|---|---|---|---|---|
| local_pain (any bite) | "Following the immediate pain of mechanical penetration of the skin by the snake's fangs ... there may be increasing local pain (burning, bursting, throbbing) at the site of the bite, local swelling that gradually extends proximally up the bitten limb" | 0 | | guideline | who2016guidelines | 5.2.1, PDF p. 97 (printed p. 93) |
| krait local effects | "However, bites by kraits, sea snakes and Philippine cobras may be virtually painless and may cause negligible local swelling." | | | guideline (qualitative) | who2016guidelines | 5.2.1, PDF p. 97 |
| local envenoming (duration) | "Local envenoming confined to the part of the body that has been bitten. These effects may be transient, resolving in hours or a few days; persistent for weeks; or debilitating" | | | guideline (duration, not onset) | who2016guidelines | Section 5 list item 2, PDF p. 97 (printed p. 93) |
| local_swelling (antivenom criterion) | "Local swelling involving more than half of the bitten limb (in the absence of a tourniquet) within 48 hr of the bite" ... "Rapid extension of swelling (for example beyond the wrist or ankle within a few hours of bites on the hands or feet)" | | 48 | guideline (treatment criterion; upper bound of the window considered) | who2016guidelines | 6.7.x "Indications for antivenom", PDF p. 133 (printed p. 129) |
| local_swelling (age of swelling) | "Swelling, a number of hours old is also not a ground for giving ASV. However, rapid development of swelling indicates bite with envenoming requiring ASV." | | | guideline (qualitative) | mohfw2017stg | "Anti Snake Venom (ASV) therapy" item 4, PDF p. 33 (printed p. 25) |
| incoagulable_blood (consumption coagulopathy) | "Sometimes within 30 minutes of the bite, the levels of clotting factors have been so depleted that the blood will not clot ("consumption coagulopathy")." | 0.5 | | lower_bound-type ("as early as") | who2016guidelines | Section 3.5 / venom composition (procoagulant enzymes), PDF p. 71 (printed p. 67) |
| incoagulable_blood (20WBCT) | "Consumption coagulopathy detectable by 20WBCT, develops as early as within 30 minutes from time of bite but may be delayed." | 0.5 | | guideline ("as early as") | mohfw2017stg | "Vasculotoxic", systemic manifestations, PDF p. 20 (printed p. 13) |
| incoagulable_blood (late) | "...whose antivenom treatment was delayed until their 20WBCTs became positive (i.e. non-clotting) some hours later (Isbister et al., 2013)" | | | guideline (qualitative "some hours later") | who2016guidelines | 6.6.1 20WBCT discussion, PDF p. 128 |
| neurotoxicity, cobra | "Neuroparalytic snakebite patients present with typical symptoms within 30 min- 6 hours in case of Cobra bite" | 0.5 | 6 | guideline | mohfw2017stg | PDF p. 18 (printed p. 11) (already in elapids.md) |
| neurotoxicity, krait/HNPV delayed | "...the Krait and the hump-nosed pit viper are known for delayed appearance of symptoms which can develop after 6-12 hours; however, ptosis in Krait bite have been recorded as late as 36 hours after hospitalization." | 6 | 12 | guideline | mohfw2017stg | PDF p. 18 (already in elapids.md) |
| neurotoxicity sequence | "In chronological order of appearance of symptoms - furrowing of forehead, Ptosis (drooping of eyelids) occurs first (Figure 3), followed by Diplopia (double vision), then Dysarthria (speech difficulty), then Dysphonia (pitch of voice becomes less) followed by Dyspnoea (breathlessness) and Dysphagia (Inability to swallow) occurs. ... Finally, paralysis of intercostal and skeletal muscles occurs in descending manner." | | | guideline (order only) | mohfw2017stg | "Neuroparalytic", PDF p. 18 (printed p. 11) |
| neurotoxicity, mixed species (SL) | "Neurological symptoms were experienced usually within 6 hours after the bite." | | 6 | upper_bound ("usually") [abstract only] | seneviratne2002neurological | Abstract, Results (n=56: Russell's viper 27, krait 19, cobra 3, unidentified 7) |
| respiratory failure, cobra and krait | "Although many clinical signs of neurotoxic envenoming by cobras and kraits are similar, with both genera able to cause respiratory failure within 30 minutes of the bite [57], [58], krait bite envenoming is often associated with a delayed onset and prolonged total period of paralysis." | 0.5 | | lower_bound-type ("as early as") | alirol2010snake | Section on clinical features of neurotoxic envenoming |
| neurotoxicity (literature table) | Table 3 row: "Ariaratnam et al.; 2008; B. caeruleus ; [25] \| 88 \| ... \| ½ h-4 h" (Weakness, onset) | 0.5 | 4 | range (secondary) | ranawaka2013neurotoxicity | Table 3 "Summary table of some key studies with descriptions of neurotoxicity" | Same as ariaratnam2008krait (already used). Kularatne 2002 row: onset "N/A". No cobra (N. naja) row. |
| time to death, elapid | "...many hours usually elapse between bite and death in the case of elapid envenoming, and several days, or even longer, in the case of viper envenoming" | | | guideline (qualitative) | who2016guidelines | 4.6.2, PDF p. 83 |
| observation window (all bites) | "If no symptoms and signs develop after 24 hours the patient can be discharged." | | 24 | guideline (observation period; implied latest onset) | mohfw2017stg | PDF p. 55 |
| non-venomous / dry bite | "Patients who develop no or negligible local swelling and no systemic envenoming are identified by clinical evaluation." | | | guideline (qualitative) | who2016guidelines | 5.1, PDF p. 97 (printed p. 93) |

## 3. BibTeX for new sources

Already in `knowledge/sources.bib` and reused: silva2016krait, pannu2024lowdose, who2016guidelines,
mohfw2017stg, dayasiri2025when, shahmy2017prospective, thalgaspitiya2020bites.

```bibtex
@article{kularatne1998krait,
  author  = {Kularatne, S. A. M.},
  title   = {Epidemiology, clinical features and management of common krait bite: a prospective study},
  journal = {The Ceylon Journal of Medical Science},
  year    = {1998},
  volume  = {41},
  number  = {2},
  pages   = {53--59},
  doi     = {10.4038/cjms.v41i2.4888},
  url     = {https://cjms.sljol.info/articles/10.4038/cjms.v41i2.4888}
}

@article{mandal2023krait,
  author  = {Mandal, Shyamash and Gope, Supriyo and Saha, Nilanjan and Mitra, Subhrajyoti J. and Chowdhury, Tanmay and Chandra, Atanu and Das, Souvik},
  title   = {Clinical profile and outcome of patients of common krait bite with features of neurotoxic envenomation, treated with intravenous calcium gluconate infusion in conjunction with {AVS}, a tertiary care center-based study},
  journal = {Asian Journal of Medical Sciences},
  year    = {2023},
  volume  = {14},
  number  = {9},
  pages   = {103--108},
  doi     = {10.3126/ajms.v14i9.51716},
  url     = {https://pdfs.semanticscholar.org/70cf/4c5a28bbcfe766cd7546a906c924aaa2640d.pdf},
  note    = {End page not verified}
}

@article{faiz2017monocled,
  author  = {Faiz, M. A. and Ahsan, M. F. and Ghose, A. and Rahman, M. R. and Amin, R. and Hossain, M. and Tareq, M. N. U. and Jalil, M. A. and Kuch, U. and Theakston, R. D. G. and Warrell, D. A. and Harris, J. B.},
  title   = {Bites by the Monocled Cobra, Naja kaouthia, in Chittagong Division, Bangladesh: Epidemiology, Clinical Features of Envenoming and Management of 70 Identified Cases},
  journal = {American Journal of Tropical Medicine and Hygiene},
  year    = {2017},
  volume  = {96},
  number  = {4},
  pages   = {876--884},
  doi     = {10.4269/ajtmh.16-0842},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC5392636/}
}

@article{alirol2010snake,
  author  = {Alirol, Emilie and Sharma, Sanjib Kumar and Bawaskar, Himmatrao Saluba and Kuch, Ulrich and Chappuis, Fran{\c{c}}ois},
  title   = {Snake Bite in South Asia: A Review},
  journal = {PLoS Neglected Tropical Diseases},
  year    = {2010},
  volume  = {4},
  number  = {1},
  pages   = {e603},
  doi     = {10.1371/journal.pntd.0000603},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC2811174/}
}

@article{ranawaka2013neurotoxicity,
  author  = {Ranawaka, Udaya K. and Lalloo, David G. and de Silva, H. Janaka},
  title   = {Neurotoxicity in Snakebite---The Limits of Our Knowledge},
  journal = {PLoS Neglected Tropical Diseases},
  year    = {2013},
  volume  = {7},
  number  = {10},
  pages   = {e2302},
  doi     = {10.1371/journal.pntd.0002302},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC3794919/}
}

@article{seneviratne2002neurological,
  author  = {Seneviratne, U. and Dissanayake, S.},
  title   = {Neurological manifestations of snake bite in {Sri Lanka}},
  journal = {Journal of Postgraduate Medicine},
  year    = {2002},
  volume  = {48},
  number  = {4},
  pages   = {275--278},
  note    = {PMID 12571382. Abstract only was read},
  url     = {https://pubmed.ncbi.nlm.nih.gov/12571382/}
}

@article{kohli2007snake,
  author  = {Kohli, Utkarsh and Sreedhar, Vijesh K.},
  title   = {Snake Bite: An Unusual Cause of Acute Abdominal Pain},
  journal = {Indian Pediatrics},
  year    = {2007},
  volume  = {44},
  pages   = {852--853},
  url     = {https://www.indianpediatrics.net/nov2007/852.pdf}
}
```

## 4. Gaps

- **Not found (no since-bite number in any source I could read):** krait local_swelling and local_pain
  onset; krait limb_weakness lower bound (still only <=8 h for complete paralysis); N. naja
  local_swelling onset; N. naja local_necrosis onset (only the STG "few minutes" for finger bites, plus
  an N. kaouthia proxy of day 1 to day 5); N. naja incoagulable_blood onset (only the general
  "as early as 30 min" guideline text); non-venomous local_pain beyond the generic WHO "immediate pain".
- **Krait abdominal_pain:** the only number (2-4 h) is an uncited narrative line in mandal2023krait.
  kularatne1998krait (primary data) says only "within minutes to few hours". The Kularatne 2002 PMJ
  full text (PMC1742360) could not be read: Europe PMC XML gives HTTP 500, the PMC PDF is behind a
  browser check, and BMJ/OUP are paywalled.
- **Krait ophthalmoplegia:** <=12 h (one patient) or <=7 h (derived from the sequence). Neither is a
  measured onset distribution.
- **Conflicts to resolve:** krait neuroparalysis onset is 0.5-4 h (ariaratnam2008krait), "after 6-12 h"
  (mohfw2017stg), "3-24 h" (mandal2023krait, narrative) and 0.5-50 h, mode 6 h (pannu2024lowdose,
  secondary). Within kularatne1998krait, ventilation timing is 3-50 h in the Summary and 2-40 h in the text.
- **Could not access (paywall or blocked):** ariaratnam2008krait pp. 460+ (AJTMH preview only);
  kularatne2009cobra, silva2026cobra (T&F/OUP, ResearchGate 403); bawaskar2004krait (SAGE 403);
  bawaskar2014premonitory; Theakston et al. 1990 TRSTMH 84:301 (5 krait, 2 cobra; abstract has no
  onset times); Warrell 2010 Lancet; Prasarnpun 2005 Brain; Anil et al. 2010 J Infect Public Health
  (Elsevier 403); Bhalla et al. 2014 APJMT 3(2):55-58 (DNS failure; a search snippet says abdominal
  pain appeared "within a few minutes to hours in 88.2%" and features "within 1 to 4 hours", NOT
  verified, not recorded); seneviratne2002neurological full text (LWW 402).
- **Second search (2026-11-06, Phase 2 follow-up):** N. naja local_swelling onset searched again;
  still nothing citable. silva2026cobra (54 authenticated bites, 2017-2025) reports swelling 39/54
  in a search snippet but the full text is not accessible; the only times found are for other
  species (Naja atra Hong Kong "within 4 hours"; N. kaouthia). See onsets_vipers.md section 4 and
  configs/sim_v2_early_local.yaml (assumed [0, 1.5] h window, sensitivity only).
- **Species caveat:** the only cobra local-necrosis timing (faiz2017monocled) is for Naja kaouthia, not N. naja.
