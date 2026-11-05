# Evidence extraction: elapids (Naja naja, Bungarus caeruleus)

Status: AI-assisted DRAFT extraction (2026-11-05). Nothing here is verified. Every row must be
checked against the source PDF by a human before it goes into `clinical_table.csv`,
`species.csv` or `context_table.csv` (`verified=false` until then).

How the numbers were read:
- **Full text read** (PMC / Europe PMC full-text XML converted to plain text, or the publisher PDF
  converted with `pdftotext`, then read directly): silva2016krait, wijayasekara2026patterns,
  pannu2024lowdose, who2016guidelines, mohfw2017stg.
- **Partial full text**: ariaratnam2008krait (only pp. 458-459 of the publisher preview PDF;
  Table 2 on a later page was NOT seen).
- **Abstract only** (full text paywalled or blocked): kularatne2002krait, kularatne2009cobra,
  silva2026cobra, bawaskar2014premonitory, bawaskar2004krait. Rows from these are marked
  `[abstract only]` and must be re-checked against the full paper.
- n/N is copied as printed. Where the denominator in the source is *all bites* (including dry
  bites) rather than *envenomed patients*, this is stated in the quote/notes column. Any
  arithmetic I did on printed numbers (adding two columns) is marked "sum of".
- Onset values are only filled where the source gives an explicit time since bite. "by X h"
  statements are recorded as onset_max only, with onset_basis `upper_bound`.
- Authentication level differs: silva2016krait, ariaratnam2008krait, kularatne2009cobra,
  silva2026cobra, wijayasekara2026patterns = snake specimen-identified (or venom EIA);
  kularatne2002krait = specimen in 99/210 only; pannu2024lowdose, bawaskar2014premonitory =
  clinical/witness diagnosis, not authenticated.

## 1. Symptom frequency and onset

### Bungarus caeruleus (common krait)

| species | symptom | frequency (n/N) | onset_min_h | onset_max_h | onset_basis | source_key | locator | verbatim quote |
|---|---|---|---|---|---|---|---|---|
| Bungarus caeruleus | ptosis | 25/25 envenomed (sum of mild 8/8 + severe 17/17) | | | | silva2016krait | Table 2 ("Maximum ptosis observed") | Mild: "• Partial \| - \| 7 (87.5%) \| 5 (29.4%)"; "• Complete \| - \| 1 (12.5%) \| 12 (70.6%)" (columns: no / mild / severe neurotoxicity; mild n=8, severe n=17) |
| Bungarus caeruleus | ptosis | | 0.5 | 4 | range | ariaratnam2008krait | p. 459, Results, "Systemic envenoming" | "Ptosis, the earliest sign of neurotoxicity, was first detected 30 minutes to 4 hours after the bite." |
| Bungarus caeruleus | ptosis | 38/40 (sum of 14/15 + 24/25) | | | | pannu2024lowdose | Table 1 | "Ptosis, n (%) \| 14 (93.3%) \| 24 (96.0%)". Note: all patients were ventilated (inclusion criterion); species by clinical/witness diagnosis; Table 1 header says 20-vial group "n = 30" but text and percentages use n=25. |
| Bungarus caeruleus | ptosis | 89% of 141 (n not given) | | | | bawaskar2014premonitory | Abstract [abstract only] | "On arrival at hospital, 78% cases had dysphasia with pooling of saliva, 89% had heaviness in both eyelids and ptosis" |
| Bungarus caeruleus | ptosis | | 6 | 12 | guideline | mohfw2017stg | p. 12 (PDF p. 18), "Neuroparalytic (Progressive weakness; Elapid envenomation)" | "Many species, particularly the Krait and the hump-nosed pit viper are known for delayed appearance of symptoms which can develop after 6–12 hours; however, ptosis in Krait bite have been recorded as late as 36 hours after hospitalization." (conflicts with ariaratnam2008krait 0.5-4 h; the 36 h is "after hospitalization", not after bite) |
| Bungarus caeruleus | ophthalmoplegia | 18/25 envenomed (sum of mild 1/8 + severe 17/17) | | | | silva2016krait | Table 2 ("Maximum ophthalmoplegia observed") | "• Partial \| - \| 1 (12.5%) \| 3 (17.6%)"; "• Complete \| - \| 0 \| 14 (82.4%)" |
| Bungarus caeruleus | bulbar_palsy | 17/25 envenomed (severe group only; mild group by definition had no bulbar weakness) | | 7 | upper_bound | silva2016krait | Table 2; Discussion para 1 | Table 2: "Difficulty in swallowing \| - \| - \| 17 (100%)". Discussion: "all other patients were intubated due to bulbar weakness and/or respiratory paralysis, which developed within 7h of the bite." |
| Bungarus caeruleus | bulbar_palsy | 33/40 (sum of 11/15 + 22/25) | | | | pannu2024lowdose | Table 1 | "Dysphagia, n (%) \| 11(73.3%) \| 22 (88.0%)" (ventilated-only cohort, not authenticated) |
| Bungarus caeruleus | bulbar_palsy | 78% of 141 (n not given) | | | | bawaskar2014premonitory | Abstract [abstract only] | "78% cases had dysphasia with pooling of saliva" |
| Bungarus caeruleus | respiratory_paralysis | 17/25 envenomed | | 7 | upper_bound | silva2016krait | Table 2; Results ("Seventeen patients developed severe neurotoxicity...") | Table 2: "Intubation and mechanical ventilation \| - \| - \| 17 (100%)". Text: "intubation and mechanical ventilation was required within 7h of the snake bite in all 17 patients." Note: "three were intubated for the antivenom reaction before they developed respiratory muscle paralysis due to envenoming." |
| Bungarus caeruleus | respiratory_paralysis | 56/88 bites (denominator includes 4 dry bites; 56/84 envenomed) | 0.5 | 13 | range | ariaratnam2008krait | p. 459, Results, "Systemic envenoming" | "Fifty-six patients (64%) developed respiratory failure." ... "Respiratory failure developed between 30 minutes and 13 hours after the bite." |
| Bungarus caeruleus | respiratory_paralysis | 101/210 | | | | kularatne2002krait | Abstract [abstract only] | "One hundred and one (48%) patients were severely envenomed and needed mechanical ventilation from 12 hours to 29 days (mode two days)." (12 h-29 d is ventilation duration, not onset) |
| Bungarus caeruleus | limb_weakness | 12/25 envenomed (upper limb, power <5); lower limb 5/25 | | 8 | upper_bound | silva2016krait | Table 2; Results | Table 2: "Reduced upper limb power (Power <5) \| - \| - \| 12 (70.6%)"; "Reduced lower limb power (power <5) \| - \| - \| 5 (29.4%)". Text: "Five patients developed complete limb paralysis with areflexia occurring within 8h of the bite" (onset_max refers to complete paralysis in those 5) |
| Bungarus caeruleus | abdominal_pain | 91% of 88 (n not given; quoted together with vomiting) | | | | ariaratnam2008krait | p. 459, Results | "Abdominal pain, which was non-colicky, often severe, and increased in intensity over several hours and vomiting, was reported by 91% of patients." |
| Bungarus caeruleus | abdominal_pain | 29/40 (sum of 10/15 + 19/25) | | | | pannu2024lowdose | Table 1 | "Abdominal pain, n (%) \| 10 (66.7%) \| 19 (76.0%)" |
| Bungarus caeruleus | abdominal_pain | 85% of 141 (n not given) | | | | bawaskar2014premonitory | Abstract [abstract only] | "Patients awoke in the night due to abdominal colic (85%) and chest pain (72%)." |
| Bungarus caeruleus | abdominal_pain | not given | | | (qualitative: "within hours") | kularatne2002krait | Abstract [abstract only] | "The cardinal symptom was abdominal pain developing within hours of the bite." |
| Bungarus caeruleus | abdominal_pain | | | | guideline (sequence, not time since bite) | mohfw2017stg | p. 17 (PDF p. 23), "Occult snakebite" | "Snakebite victim gets up in the morning with severe epigastric/umbilical pain with vomiting persisting for 3 – 4 hours and followed by typical neuroparalytic symptoms within next 4- 6 hours." |
| Bungarus caeruleus | vomiting | 42% of 141 (n not given) | | | | bawaskar2014premonitory | Abstract [abstract only] | "Patients gave a history of vomiting (42%), sweating (17%) and excessive salivation (35%)." |
| Bungarus caeruleus | vomiting / headache / abdominal_pain (combined) | 18/25 envenomed (sum of mild 5/8 + severe 13/17) | | | | silva2016krait | Table 2; Methods "Data collection" | Table 2: "Non-specific systemic envenoming \| - \| 5 (62.5%) \| 13 (76.5%)". Methods: "non-specific systemic effects were defined as headache, nausea, vomiting or abdominal pain." Cannot be split by symptom. |
| Bungarus caeruleus | local_pain / local_swelling / lymphadenopathy (combined "local envenoming") | 15/25 envenomed (sum of mild 6/8 + severe 9/17); also 5/8 in the no-neurotoxicity ("dry") group | | | | silva2016krait | Table 2; Methods | Table 2: "Local envenoming \| 5 (62.5%) \| 6 (75%) \| 9 (52.9%)". Methods: "Local effects included pain, swelling, paraesthesia or regional lymphadenopathy". Cannot be split by symptom. |
| Bungarus caeruleus | local_swelling | 8/88 bites | | | | ariaratnam2008krait | p. 459, Results, "Dry bites" para | "Slight local swelling was detectable in only eight patients (9%)." |
| Bungarus caeruleus | local_pain | 2/88 bites | | | | ariaratnam2008krait | p. 459, Results | "Local symptoms at the site of the bite were rare: paraesthesiae (numbness) in four cases and pain in two cases." |
| Bungarus caeruleus | local_pain | (qualitative) | | | guideline | who2016guidelines | Section 5 "Summary of symptoms and signs" / 5.2.1 | "increasing local pain at the site of the bite (krait bites usually painless)"; "bites by kraits, sea snakes and Philippine cobras may be virtually painless and may cause negligible local swelling." |
| Bungarus caeruleus | incoagulable_blood | 0/88 | | | | ariaratnam2008krait | p. 459, Results ("Systemic envenoming" and "Laboratory data") | "None showed any evidence of spontaneous bleeding or incoagulable blood." / "All patients had coagulable blood, detected by 20 WBCT." |
| Bungarus caeruleus | systemic_bleeding | 0/88 | | | | ariaratnam2008krait | p. 459, Results | "None showed any evidence of spontaneous bleeding or incoagulable blood." |
| Bungarus caeruleus | neurotoxicity (any; ptosis, ophthalmoplegia, dyspnoea, dysphagia combined) | 84/88 bites | | | | ariaratnam2008krait | p. 459, Results, "Systemic envenoming" | "Neurotoxic signs, such as partial or complete ptosis, external ophthalmoplegia, difficulty in breathing, and dysphagia were observed in 84 patients (95%" |

### Naja naja (spectacled cobra)

| species | symptom | frequency (n/N) | onset_min_h | onset_max_h | onset_basis | source_key | locator | verbatim quote |
|---|---|---|---|---|---|---|---|---|
| Naja naja | neurotoxicity (any; maps to ptosis etc. only after reading full text) | 9/25 bites (= 9/20 envenomed; 5 dry) | | | | kularatne2009cobra | Abstract [abstract only] | "There were 5 dry bites (20%), 20 local reactions (80%), 9 cases of neurotoxicity (36%) and 3 cases of coagulopathy (12%)." |
| Naja naja | neurotoxicity (any) | 10/54 bites | | | | silva2026cobra | Abstract [abstract only] | "Neurotoxicity occurred in 10/54 (19%), including four with respiratory paralysis." |
| Naja naja | ptosis / neuroparalytic symptoms | | 0.5 | 6 | guideline | mohfw2017stg | p. 12 (PDF p. 18), "Neuroparalytic" | "Neuroparalytic snakebite patients present with typical symptoms within 30 min– 6 hours in case of Cobra bite" |
| Naja naja | respiratory_paralysis | 4/25 bites (= 4/20 envenomed) | 2 | 5 | range (time bite -> assisted ventilation, median 2 h) | kularatne2009cobra | Abstract [abstract only] | "Four patients (16%; 95% CI 4.53-36.08) developed respiratory paralysis; their median time from bite to assisted ventilation was 2h (range 2-5h)" |
| Naja naja | respiratory_paralysis | 4/54 bites | | | | silva2026cobra | Abstract [abstract only] | "Neurotoxicity occurred in 10/54 (19%), including four with respiratory paralysis." |
| Naja naja | local envenoming (any; local_pain/local_swelling) | 20/25 bites (= 20/20 envenomed) | | | | kularatne2009cobra | Abstract [abstract only] | "20 local reactions (80%)" |
| Naja naja | local envenoming (any) | 45/54 bites | | | | silva2026cobra | Abstract [abstract only] | "Local envenoming occurred in 45/54 (83%) patients: 30/54 (56%) only developed pain and swelling, while 10/54 (19%) had blistering, hematoma, or necrosis." |
| Naja naja | local_pain + local_swelling (only) | 30/54 bites | | | | silva2026cobra | Abstract [abstract only] | "30/54 (56%) only developed pain and swelling" |
| Naja naja | blistering / local_necrosis (combined with haematoma) | 10/54 bites | | | | silva2026cobra | Abstract [abstract only] | "10/54 (19%) had blistering, hematoma, or necrosis" |
| Naja naja | local_necrosis (severe, skin grafting) | 5/54 bites | | | | silva2026cobra | Abstract [abstract only] | "Severe necrotic wounds requiring skin grafting occurred in 5/54 (9%)." |
| Naja naja | local_necrosis (severe) | 8/25 bites (= 8/20 envenomed) | | | | kularatne2009cobra | Abstract [abstract only] | "Eight patients (32%) had severe local necrosis-five underwent desloughing and skin grafting" |
| Naja naja | incoagulable_blood | 3/25 bites (authors say unverified) | | | | kularatne2009cobra | Abstract [abstract only] | "3 cases of coagulopathy (12%)" ... "Coagulopathy requires verification with robust laboratory tests." |
| Naja naja | local_swelling / blistering / local_necrosis (qualitative) | | | | guideline | mohfw2017stg | p. 20 (PDF p. 26) | "Local swelling, bleeding, blistering, necrosis suggests Cobra bite. Minimum local changes indicate Krait bite." |
| Naja naja | local_necrosis (timing, finger bites) | | | | guideline (qualitative "few minutes") | mohfw2017stg | p. 20 (PDF p. 26), "Clues for severe snake envenomation" | "In Cobra bite on finger, necrosis may start in few minutes." |

## 2. Dry-bite rates

| species | value | frequency (n/N) | source_key | locator | verbatim quote |
|---|---|---|---|---|---|
| Bungarus caeruleus | dry_bite_rate | 8/33 | silva2016krait | Results, "Clinical effects during hospital stay"; Table 2; Discussion | "Eight patients who brought the offending snake and had evidence of a bite with fang marks, did not develop neurotoxic features during their hospital stay." Discussion: "The eight patients who had no detectable venom in blood and had no features of envenoming, were 'dry bites'". Caveat: Table 2 lists "Local envenoming" in 5/8 of this group. |
| Bungarus caeruleus | dry_bite_rate | 4/88 | ariaratnam2008krait | p. 459, Results, "Dry bites" | "Dry bites. Only four patients (4.5%) showed no signs of envenoming at any stage." |
| Bungarus caeruleus | dry_bite_rate | 1/23 | bawaskar2004krait | Abstract [abstract only] | "Of the 14 survivors, 4 required artificial respirations ... One had a dry bite." (23 krait cases total; not all authenticated) |
| Naja naja | dry_bite_rate | 5/25 | kularatne2009cobra | Abstract [abstract only] | "There were 5 dry bites (20%)" |
| Naja naja | dry_bite_rate | not derivable (abstract gives 45/54 with local envenoming and 10/54 with neurotoxicity, but not the number with no envenoming) | silva2026cobra | Abstract [abstract only] | - |
| all venomous (guideline) | dry_bite_rate range | 5-80%, average ~50% | who2016guidelines | Section 4.4 "Circumstances of snakebites", p. 78 | "The incidence of dry bites varies with the species, from 5-80%, average about 50% (Reid et al., 1963a; de Rezende et al., 1998; Silveira and Nishioka, 1995)." |
| all venomous (guideline) | dry_bite_rate range | 10-80% | mohfw2017stg | p. 11 (PDF p. 17), "Dry Bite" | "The percentage of dry bites ranges from 10–80% for various venomous snakes." |

## 3. Context features

| species | feature | value | frequency (n/N) | source_key | locator | verbatim quote |
|---|---|---|---|---|---|---|
| Bungarus caeruleus | time_of_day | night (1900-0600) | 30/33 | silva2016krait | Table 1 | "Bite time (night: 1900–0600 hrs) \| 30 \| 91%" |
| Bungarus caeruleus | asleep | sleeping (floor 22 + bed 3) | 25/33 (sum of 22 + 3) | silva2016krait | Table 1 | "Activity (Sleeping on the floor) \| 22 \| 67%"; "(Sleeping on the bed) \| 3 \| 9%" |
| Bungarus caeruleus | indoor | home | 25/33 (plus 4/33 "hut in the farmland") | silva2016krait | Table 1 | "Place (home) \| 25 \| 76%"; "(hut in the farmland) \| 4 \| 12%" |
| Bungarus caeruleus | time_of_day | 2300-0500 | 100% of 88 | ariaratnam2008krait | Abstract; p. 459 Results "Epidemiologic features" | Abstract: "between 2300 and 0500 hours, 100% (3%)". Text: "All the bites occurred during the hours of darkness" ... "The highest incidence (76 patients, 86%) was between 2300 and 0300 hours." (text also prints "0300–1400 hours for 8 patients (9%)", apparently a typo for 0300-0400) |
| Bungarus caeruleus | asleep | sleeping on the ground | 100% of 88 | ariaratnam2008krait | Abstract; p. 459 | Abstract: "bitten while sleeping on the ground, 100% (1%)". Text: "all were asleep inside mud or clay houses ... except one soldier who was bitten while lying on guard in a bunker." |
| Bungarus caeruleus | indoor | indoors | 100% of 88 | ariaratnam2008krait | Abstract | "indoors, 100% (49%)" |
| Bungarus caeruleus | time_of_day | night (7 pm-6 am) | 75/101 | wijayasekara2026patterns | Results, "Bungarus caeruleus (Indian krait)" | "Of the 101 B. caeruleus bites, 75 (74·3%) occurred at night (7 pm to 6 am)" ... "B. caeruleus peaked from 1 am to 5 am (36, 35·6%)" |
| Bungarus caeruleus | asleep | sleeping | 60/99 | wijayasekara2026patterns | Table 1 ("Activity while the bite occurred", N=99) | "Sleeping \| ... \| 60 (60·6%)" (B. caeruleus column) |
| Bungarus caeruleus | indoor | indoors | 59/96 | wijayasekara2026patterns | Table 1 ("Location of bite", N=96) | "Indoors \| ... \| 59 (61·5%)" (B. caeruleus column) |
| Bungarus caeruleus | time_of_day | 10 PM-6 AM | 38/40 | pannu2024lowdose | Results para 2 | "Thirty-eight snakebites (95%) snakebite occurred between 10 PM. to 6 AM (during the night and early morning)" (not authenticated) |
| Bungarus caeruleus | time_of_day | midnight-05:00 | 140/141 | bawaskar2014premonitory | Abstract [abstract only] | "A total of 140 victims reported between midnight and 05:00." (note: "reported", may mean presented rather than bitten) |
| Bungarus caeruleus | asleep / time_of_day | night, asleep on floor (qualitative) | not given | kularatne2002krait | Abstract [abstract only] | "The bite occurred at night while the victims were asleep on the floor." |
| Bungarus caeruleus | asleep / time_of_day | guideline (qualitative) | - | mohfw2017stg | p. 1 (PDF p. 7), Introduction | "Kraits are active during night hours, often biting a person sleeping on floor bed." |
| Bungarus caeruleus | asleep | guideline (qualitative) | - | who2016guidelines | Section 5.3, Syndrome 4 | "Paralysis with minimal or no local envenoming: Bitten on land while sleeping on the ground with/without abdominal pain = krait" |
| Naja naja | time_of_day | day (9 am-7 pm) | 53/62 | wijayasekara2026patterns | Results, "Naja naja (Indian cobra)" | "Of 62 N. naja bites, 53 (85·5%) occurred during the day (9 am to 7 pm), 37 (59·7%) of these were outdoors" ... "Daytime bites peaked from 12 noon to 6 pm (35/62, 56·5%)." |
| Naja naja | indoor | indoors | 17/59 | wijayasekara2026patterns | Table 1 ("Location of bite", N=59) | "Indoors \| ... \| 17 (28·8%)" (N. naja column) |
| Naja naja | asleep | sleeping | 2/60 | wijayasekara2026patterns | Table 1 ("Activity", N=60) | "Sleeping \| ... \| 2 (3·3%)" (N. naja column) |
| Naja naja | time_of_day | daytime | 22/25 | kularatne2009cobra | Abstract [abstract only] | "In 22 cases (88%) bites occurred in the daytime and in 13 cases (52%) they occurred at the victim's home compound." |
| Naja naja | location | victim's home compound | 13/25 | kularatne2009cobra | Abstract [abstract only] | as above (home compound is not the same as indoors) |
| Naja naja | time_of_day | day | 44/54 | silva2026cobra | Abstract [abstract only] | "Thirty-five (65%) bites involved the foot, and 44 (81%) occurred during the day." |
| Naja naja | time_of_day | guideline (qualitative) | - | mohfw2017stg | p. 1 (PDF p. 7) | "Maximum Viper and Cobra bites occur during the day or early darkness" |

## 4. BibTeX

```bibtex
@article{silva2016krait,
  author  = {Silva, Anjana and Maduwage, Kalana and Sedgwick, Michael and Pilapitiya, Senaka and Weerawansa, Prasanna and Dahanayaka, Niroshana J. and Buckley, Nicholas A. and Johnston, Christopher and Siribaddana, Sisira and Isbister, Geoffrey K.},
  title   = {Neuromuscular Effects of Common Krait (Bungarus caeruleus) Envenoming in Sri Lanka},
  journal = {PLoS Neglected Tropical Diseases},
  year    = {2016},
  volume  = {10},
  number  = {2},
  pages   = {e0004368},
  doi     = {10.1371/journal.pntd.0004368},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC4734751/}
}

@article{ariaratnam2008krait,
  author  = {Ariaratnam, Christeine A. and Sheriff, M. H. Rezvi and Theakston, R. David G. and Warrell, David A.},
  title   = {Distinctive Epidemiologic and Clinical Features of Common Krait (Bungarus caeruleus) Bites in Sri Lanka},
  journal = {American Journal of Tropical Medicine and Hygiene},
  year    = {2008},
  volume  = {79},
  number  = {3},
  pages   = {458--462},
  doi     = {10.4269/ajtmh.2008.79.458},
  url     = {https://www.ajtmh.org/view/journals/tpmd/79/3/article-p458.xml}
}

@article{kularatne2002krait,
  author  = {Kularatne, S. A. M.},
  title   = {Common krait (Bungarus caeruleus) bite in Anuradhapura, Sri Lanka: a prospective clinical study, 1996-98},
  journal = {Postgraduate Medical Journal},
  year    = {2002},
  volume  = {78},
  number  = {919},
  pages   = {276--280},
  doi     = {10.1136/pmj.78.919.276},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC1742360/}
}

@article{bawaskar2014premonitory,
  author  = {Bawaskar, H. S. and Bawaskar, P. H. and Bawaskar, Parag H.},
  title   = {Premonitory signs and symptoms of envenoming by common krait (Bungarus caeruleus)},
  journal = {Tropical Doctor},
  year    = {2014},
  volume  = {44},
  number  = {2},
  pages   = {82--85},
  doi     = {10.1177/0049475514521802},
  url     = {https://doi.org/10.1177/0049475514521802}
}

@article{bawaskar2004krait,
  author  = {Bawaskar, Himmatrao Saluba and Bawaskar, Pramodini Himmatrao},
  title   = {Envenoming by the common krait (Bungarus caeruleus) and Asian cobra (Naja naja): clinical manifestations and their management in a rural setting},
  journal = {Wilderness \& Environmental Medicine},
  year    = {2004},
  volume  = {15},
  number  = {4},
  pages   = {257--266},
  doi     = {10.1580/1080-6032(2004)015[0257:EBTCKB]2.0.CO;2},
  url     = {https://doi.org/10.1580/1080-6032(2004)015[0257:EBTCKB]2.0.CO;2}
}

@article{pannu2024lowdose,
  author  = {Pannu, Ashok Kumar and Chand, Duni and Bhalla, Ashish and Dhibar, Deba Prasad},
  title   = {Efficacy of a low dose of antivenom for severe neuroparalysis in Bungarus caeruleus (common krait) envenomation: a pilot study},
  journal = {Toxicology Research},
  year    = {2024},
  volume  = {13},
  number  = {2},
  pages   = {tfae023},
  doi     = {10.1093/toxres/tfae023},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC10913380/}
}

@article{wijayasekara2026patterns,
  author  = {Wijayasekara, Asela and Silva, Anjana and Weerakoon, Kosala and Waiddyanatha, Subodha and Wedasingha, Supun and Siribaddana, Sisira and Isbister, Geoffrey K.},
  title   = {Snakebite patterns in rural Sri Lanka and their implications for preventive measures},
  journal = {PLoS Neglected Tropical Diseases},
  year    = {2026},
  volume  = {20},
  number  = {3},
  pages   = {e0014092},
  doi     = {10.1371/journal.pntd.0014092},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC12991362/}
}

@article{kularatne2009cobra,
  author  = {Kularatne, S. A. M. and Budagoda, B. D. S. S. and Gawarammana, I. B. and Kularatne, W. K. S.},
  title   = {Epidemiology, clinical profile and management issues of cobra (Naja naja) bites in Sri Lanka: first authenticated case series},
  journal = {Transactions of the Royal Society of Tropical Medicine and Hygiene},
  year    = {2009},
  volume  = {103},
  number  = {9},
  pages   = {924--930},
  doi     = {10.1016/j.trstmh.2009.04.002},
  url     = {https://doi.org/10.1016/j.trstmh.2009.04.002}
}

@article{silva2026cobra,
  author  = {Silva, Anjana and Waiddyanatha, Subodha and Senanayake, Hemal and Sarathchandra, Chamara and Siribaddana, Sisira and Isbister, Geoffrey K.},
  title   = {Neuromuscular and cytotoxic effects of common cobra (Naja naja) bites in rural Sri Lanka},
  journal = {Clinical Toxicology},
  year    = {2026},
  volume  = {64},
  number  = {3},
  pages   = {221--224},
  doi     = {10.1080/15563650.2025.2601140},
  url     = {https://doi.org/10.1080/15563650.2025.2601140}
}

@book{who2016guidelines,
  author    = {{World Health Organization Regional Office for South-East Asia}},
  title     = {Guidelines for the Management of Snakebites},
  edition   = {2nd},
  publisher = {WHO Regional Office for South-East Asia},
  address   = {New Delhi},
  year      = {2016},
  isbn      = {9789290225300},
  note      = {Drafted and revised by David A. Warrell. No DOI; IRIS handle 10665/249547},
  url       = {https://cdn.who.int/media/docs/default-source/searo/india/health-topic-pdf/who-guidance-on-management-of-snakebites.pdf}
}

@techreport{mohfw2017stg,
  author      = {{Ministry of Health and Family Welfare, Government of India}},
  title       = {Standard Treatment Guidelines: Management of Snake Bite},
  institution = {Ministry of Health and Family Welfare, Government of India},
  address     = {New Delhi},
  year        = {2017},
  month       = {aug},
  note        = {No DOI},
  url         = {https://ncdc.mohfw.gov.in/uploads/pdf/Standard-Treatment-Guidelines-for-Management-of-Snake-Bite.pdf}
}
```

## 5. Gaps

- **Cobra, symptom-level frequencies:** no full-text authenticated cobra series could be read
  (kularatne2009cobra and silva2026cobra are paywalled; abstracts only). So there are no
  separate values for ptosis, ophthalmoplegia, bulbar_palsy, limb_weakness, local_pain,
  local_swelling, progressive_swelling, blistering or regional_lymphadenopathy. The abstracts
  only give lumped "neurotoxicity" / "local envenoming" counts.
- **Cobra onset windows:** only the STG guideline (0.5-6 h, neuroparalytic symptoms) and
  bite-to-ventilation time (median 2 h, range 2-5 h, n=4, abstract). Not found: onset of
  local swelling, necrosis or ptosis from a case series.
- **Krait onset windows not found:** ophthalmoplegia, abdominal pain, vomiting (only "within
  hours" and the STG sequence). Bulbar palsy and limb weakness have upper bounds only (<=7 h,
  <=8 h). Krait ptosis onset conflicts between ariaratnam2008krait (0.5-4 h) and mohfw2017stg
  ("after 6-12 hours"; up to 36 h after hospitalisation).
- **Krait symptoms not separable:** headache and vomiting (silva2016krait lumps headache,
  nausea, vomiting and abdominal pain together); local_pain vs local_swelling vs
  regional_lymphadenopathy in silva2016krait (lumped as "local envenoming").
- **Not found for either species:** acute_kidney_injury, shock, headache (as separate items),
  progressive_swelling, regional_lymphadenopathy. Cobra systemic_bleeding was not found.
  Cobra incoagulable_blood is only 3/25, which the authors say needs verifying.
- **Not read in full and worth getting as PDFs:** kularatne2002krait (n=210; the PMC PDF is
  behind a browser check), ariaratnam2008krait Table 2 (p. 460+), kularatne2009cobra,
  silva2026cobra, bawaskar2004krait, bawaskar2014premonitory, and Theakston et al. 1990
  (Trans R Soc Trop Med Hyg 84:301-308, krait and Sri Lankan cobra; not searched in full).
- **Indian (vs Sri Lankan) authenticated series:** the only Indian clinical numbers are from
  non-authenticated cohorts (pannu2024lowdose, which only includes ventilated patients;
  bawaskar2014premonitory, abstract). Bawaskar 2002 (TRSTMH) and 2008 (JAPI) Maharashtra series
  were found but not read beyond the abstracts, and those abstracts give no species-specific
  symptom counts.
- **Denominator caution:** several frequencies use all bites (including dry bites) as the
  denominator (ariaratnam2008krait, kularatne2009cobra, silva2026cobra). Convert to
  envenomed-only denominators only where the number of dry bites is printed.
