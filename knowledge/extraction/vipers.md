# Evidence extraction: true vipers (Russell's viper, saw-scaled viper)

Draft, AI-assisted extraction (Phase 1). **Every row is unverified** until a human checks it
against the source PDF (`verified=false` in the CSVs). Symptom names follow
`knowledge/symptoms.csv`.

How the numbers were read:
- **Full text read** (PMC / Europe PMC XML or publisher HTML): kularatne2014revisiting,
  silva2016myotoxicity, gnanathasan2012sawscaled, lath2024strikes, who2016guidelines (PDF from WHO IRIS),
  mohfw2016stg (PDF, Quick Reference Guide July 2016).
- **Read through WebFetch** (publisher HTML summarised by a small model; quotes asked for verbatim
  and re-checked with a second prompt): gopalakrishnan2025antivenom.
- **Abstract only** (full text not accessible): kularatne2003russell (Europe PMC abstract),
  kochar2007rediscovery (Europe PMC abstract), silva2016neurotoxicity (abstract on the University of
  New England research portal, via WebFetch).

Denominator conventions (check before use in `clinical_table.csv`, which wants frequencies among
*envenomed* patients):
- kularatne2014revisiting: N = 55 specimen-proven bites, of whom 53 were envenomed (2 dry). The table
  reports n/55, which is what is given below. Only proven cases are used, not the 154 suspected.
- silva2016myotoxicity / silva2016neurotoxicity: N = 245 confirmed bites (snake identification and/or
  venom immunoassay), 244 with local envenoming.
- gnanathasan2012sawscaled: N = 48 bites with the snake brought in. The number of envenomed patients is
  not stated.
- gopalakrishnan2025antivenom: N = 105 with envenoming (53 confirmed by dead snake or photo, 52
  "syndromic", which *required* VICC). VICC frequency is therefore inflated by design.
- kularatne2003russell: 336 cases, 310 envenomed. The abstract does not say whether the percentages
  use 336 or 310 as the denominator.

Taxonomy caution: gopalakrishnan2025antivenom and kochar2007rediscovery describe *Echis carinatus
sochureki* (Rajasthan), which these authors say is more severe than *E. c. carinatus*. The Sri Lankan
saw-scaled viper (gnanathasan2012sawscaled) is notably mild. Sri Lankan / South Indian Russell's
vipers cause neurotoxicity that other populations do not. Pooling across regions will change the
simulated syndrome mix.

## 1. Symptom frequencies and onset windows

Onset hours are converted from minutes where needed (e.g. 35 min = 0.58 h). Blank = not found.

| species | symptom | frequency (n/N) | onset_min_h | onset_max_h | onset_basis | source_key | locator | verbatim quote | notes |
|---|---|---|---|---|---|---|---|---|---|
| Daboia russelii | local_pain | 53/55 | | | | kularatne2014revisiting | Table 2, proven cases | "Pain 53 (96)" | proven cases (n, 55) |
| Daboia russelii | local_swelling | 49/55 | | | | kularatne2014revisiting | Table 2, proven cases | "Swelling 49 (89)" | |
| Daboia russelii | local_swelling | 92% (N 336 or 310, unclear) | | | | kularatne2003russell | Abstract | "Envenoming manifested in 310 (92%) of patients as follows: local swelling 92%" | abstract only; snake authentication not stated in the abstract |
| Daboia russelii | local_swelling | 244/245 (any local envenoming) | | | | silva2016neurotoxicity | Abstract | "All but one had local envenoming" | abstract only; "local envenoming" not split into pain or swelling |
| Daboia russelii | blistering | 1/55 | | | | kularatne2014revisiting | Table 2, proven cases | "Blistering 1 (2)" | |
| Daboia russelii | local_necrosis | 1/55 | | | | kularatne2014revisiting | Table 2, proven cases | "Necrosis 1 (2)" | |
| Daboia russelii | local_necrosis | 8.9% (N unclear) | | | | kularatne2003russell | Abstract | "local necrosis 8.9%" | abstract only |
| Daboia russelii | incoagulable_blood | 38/55 | 0.58 | 16.0 | range | kularatne2014revisiting | Table 2, proven cases | "Incoagulable blood (20 WBCT) 38 (69) ... Time duration from bite to coagulopathy (Minutes, range within parenthesis) 167.5 (35–960)" | median 167.5 min (2.8 h); range 35 to 960 min |
| Daboia russelii | incoagulable_blood | 77% (N unclear) | 0.5 | 12 | range | kularatne2003russell | Abstract | "coagulopathy 77% ... Coagulopathy appeared within 30 minutes to 12 hours after the bite" | abstract only |
| Daboia russelii | incoagulable_blood | 166/245 | | | | silva2016myotoxicity | Table 1 | "Number of patients with coagulopathy 166 (68%)" | full text; same cohort as silva2016neurotoxicity |
| Daboia russelii | systemic_bleeding | not totalled; gum 2/55, GI 1/55, haematuria 1/55, epistaxis 0/55 | | | | kularatne2014revisiting | Table 2, proven cases | "Gum bleeding 2 (4) ... Epistaxis 0 ... Gastrointestinal bleeding 1 (2) ... Haematuria 1 (2)" | patients may have more than one site, so do not sum |
| Daboia russelii | acute_kidney_injury | 5/55 | | | | kularatne2014revisiting | Table 2, proven cases | "Renal dysfunction Total 5 (9)" | defined by Table 1 score (urea > 13 mmol/l and above) |
| Daboia russelii | acute_kidney_injury | 18% (N unclear) | | | | kularatne2003russell | Abstract | "nephrotoxicity 18%" | abstract only |
| Daboia russelii | acute_kidney_injury | 19/245 (oliguria) | | | | silva2016neurotoxicity | Abstract | "oliguria in 19 (8%)" | abstract only; oliguria used as an AKI proxy |
| Daboia russelii | shock | 1/55 | | | | kularatne2014revisiting | Table 2, proven cases | "Cardiovascular dysfunction Total 1 (2)" | Table 1 defines it as "Systolic blood pressure <90 mmHg and signs of early circulatory collapse" and above; mapping to `shock` needs review |
| Daboia russelii | ptosis | 30/55 | | | | kularatne2014revisiting | Table 2, proven cases | "Ptosis 30 (55)" | |
| Daboia russelii | ptosis | 130/245 | | 8 | range (upper bound) | silva2016neurotoxicity; silva2016myotoxicity | silva2016neurotoxicity Abstract; silva2016myotoxicity Table 1 | "Neurotoxicity was characterised by ptosis (100%), blurred vision (93%), and ophthalmoplegia (90%)"; "Neurotoxicity developed within 8h post-bite in all patients."; "Number of patients with neurotoxicity 130 (53%)" | ptosis in 100% of the 130 neurotoxic patients gives 130/245 (derived); onset bound applies to neurotoxicity overall |
| Daboia russelii | ophthalmoplegia | 30/55 | | | | kularatne2014revisiting | Table 2, proven cases | "Ophthalmoplegia 30 (55)" | |
| Daboia russelii | ophthalmoplegia | 90% of 130 neurotoxic (out of 245) | | 8 | range (upper bound) | silva2016neurotoxicity | Abstract | "ophthalmoplegia (90%)"; "Neurotoxicity developed within 8h post-bite in all patients." | abstract only; the count (about 117) is derived, not stated |
| Daboia russelii | ptosis / ophthalmoplegia (neurotoxicity, combined) | 78% (N unclear) | | | | kularatne2003russell | Abstract | "neurotoxicity 78%" | abstract only; signs not split |
| Daboia russelii | bulbar_palsy | 0/245 | | | | silva2016neurotoxicity | Abstract | "No bulbar, respiratory or limb muscle weakness occurred." | abstract only |
| Daboia russelii | respiratory_paralysis | 0/55 | | | | kularatne2014revisiting | Table 2, proven cases | "Respiratory paralysis 0" | |
| Daboia russelii | respiratory_paralysis | 0/245 | | | | silva2016neurotoxicity | Abstract | "No bulbar, respiratory or limb muscle weakness occurred." | abstract only |
| Daboia russelii | respiratory_paralysis | 8/336 (ventilated) | | | | kularatne2003russell | Abstract | "eight patients needed mechanical ventilation" | abstract only; denominator is the 336 cases |
| Daboia russelii | limb_weakness | 14/55 (neck muscle weakness) | | | | kularatne2014revisiting | Table 2, proven cases | "Neck muscle weakness 14 (25)" | neck weakness, not limb weakness: mapping to vocab needs review |
| Daboia russelii | limb_weakness | 0/245 | | | | silva2016neurotoxicity | Abstract | "No bulbar, respiratory or limb muscle weakness occurred." | abstract only |
| Daboia russelii | abdominal_pain | 34/55 (31/38 systemic, 3/17 non-systemic) | 0.08 | 4.0 | range | kularatne2014revisiting | Results, "Abdominal pain"; Table 7 | "Abdominal pain was observed in 31 (79.5%) of the proven Russell's viper bite victims with systemic envenoming and in only 3 (25%) of those who had only local envenoming. The pain had developed 5 to 240 minutes (mean 71 minutes) after the bite" | Table 7 totals: 34 with pain out of 55. Note 31/38 = 81.6%, not 79.5% as printed; flag for the reviewer |
| Daboia russelii | vomiting | not found | | | | | | | |
| Daboia russelii | headache | not found | | | | | | | |
| Daboia russelii | progressive_swelling | not found | | | | | | | kularatne2014revisiting scores "Swelling involving more than half the limb" (Table 1) but gives no count |
| Daboia russelii | regional_lymphadenopathy | not found | | | | | | | |
| Echis carinatus (Sri Lanka) | local_pain | 46/48 | | | | gnanathasan2012sawscaled | Table 2 | "Local pain 46 (96%)" | |
| Echis carinatus (Sri Lanka) | local_swelling | 31/48 | | | | gnanathasan2012sawscaled | Results, Clinical manifestations; Table 2 | "Local symptoms at the site of the bite were seen in 65% of patients. These included local swelling and bleeding." / "Swelling 31 (65%)" | |
| Echis carinatus (Sri Lanka) | incoagulable_blood | 34/48 | | | | gnanathasan2012sawscaled | Results, Clinical manifestations | "Incoagulable blood as assessed by the 20WBCT was seen in 34 (71%) of patients." | |
| Echis carinatus (Sri Lanka) | systemic_bleeding | 14/48 | | | | gnanathasan2012sawscaled | Results, Clinical manifestations | "Spontaneous bleeding was observed in 14 (29%) patients with hematuria and hematemesis seen in 5 patients each (10%), gingival bleeding in 3 (6%), and hemoptysis in one patient." | the HTML Table 2 rows look misaligned against this text; the text was used |
| Echis carinatus (Sri Lanka) | vomiting | 4/48 (nausea and vomiting) | | | | gnanathasan2012sawscaled | Results, Clinical manifestations | "Nausea and vomiting was reported by 4 (8%) patients" | |
| Echis carinatus (Sri Lanka) | abdominal_pain | 1/48 | | | | gnanathasan2012sawscaled | Results, Clinical manifestations | "one (2%) had severe abdominal pain" | |
| Echis carinatus (Sri Lanka) | ptosis / other neurotoxic signs | 0/48 (stated qualitatively) | | | | gnanathasan2012sawscaled | Conclusion | "the only evidence for systemic envenoming was coagulopathy and spontaneous bleeding" | no explicit count of neurotoxic signs |
| Echis carinatus (Sri Lanka) | acute_kidney_injury | not found | | | | gnanathasan2012sawscaled | Treatment and outcome | "hospital observation for suspected nephrotoxicity" | no count given |
| Echis carinatus sochureki (Rajasthan) | local_swelling (incl. blistering) | 99/105 | | | | gopalakrishnan2025antivenom | Results, local envenomation | "Signs of local envenomation with swelling or blebs were observed in 99 patients (94.3%; Figure 4B)" | swelling and blebs not separated |
| Echis carinatus sochureki (Rajasthan) | incoagulable_blood | 103/105 (VICC) | | | | gopalakrishnan2025antivenom | Abstract, Results | "Of 210 patients screened, 105 had E. c. sochureki envenoming, 103 venom-induced consumption coagulopathy" | the syndromic half needed VICC to be included; WBCT20 positive at presentation 87/105 ("Eighty-seven patients (82.8%) had a positive WBCT20 at presentation"; Table 2 reportedly prints 83.8%) |
| Echis carinatus sochureki (Rajasthan) | systemic_bleeding | 55/105 | | | | gopalakrishnan2025antivenom | Abstract, Results | "55 (52.3%) systemic bleeding" | also local bleeding 36/105 ("36 (34.3%) local bleeding"); gross haematuria n=35 |
| Echis carinatus sochureki (Rajasthan) | acute_kidney_injury | 19/105 | | | | gopalakrishnan2025antivenom | Results | "Nineteen patients developed AKI, 17 needed renal replacement therapy (haemodialysis) and 11 displayed evidence of TMA" | contradicts mohfw2016stg, which says AKI is "not seen with Saw scale viper" |
| Echis carinatus sochureki (Rajasthan) | shock | 3/105 | | | | gopalakrishnan2025antivenom | Results | "Three patients developed hypovolemic shock due to bleeding." | 2 more had septic shock (excluded) |
| Echis carinatus sochureki (Rajasthan) | incoagulable_blood | 12/12 | | | | kochar2007rediscovery | Abstract | "All 12 victims had evidence of systemic envenoming, including abnormal 20-minute whole blood clotting tests (with systemic bleeding in 7)." | abstract only; snakes "definitively identified by an experienced herpetologist" |
| Echis carinatus sochureki (Rajasthan) | systemic_bleeding | 7/12 | | | | kochar2007rediscovery | Abstract | "(with systemic bleeding in 7)" | abstract only |
| Echis carinatus (Karnataka) | local_swelling | 5/5 | | | | lath2024strikes | Discussion | "Whereas all patients had local envenomation and laboratory proven VICC, two presented with bleeding from the oral cavity, one had hematemesis and one haematuria." | n = 5; very small |
| Echis carinatus (Karnataka) | incoagulable_blood | 5/5 | | | | lath2024strikes | Discussion | (same sentence as above) | |
| Echis carinatus (Karnataka) | systemic_bleeding | at least 2/5 | | | | lath2024strikes | Discussion | (same sentence as above) | sites overlap, so the total is unclear |
| Echis carinatus (Karnataka) | acute_kidney_injury | 2/5 | | | | lath2024strikes | Discussion | "Only two patients had mild acute kidney injury" | |
| Viperidae (general guideline) | incoagulable_blood | | 0.5 | | guideline | who2016guidelines | Section 3 (venoms), printed p. 68 (PDF p. 71) | "Sometimes within 30 minutes of the bite, the levels of clotting factors have been so depleted that the blood will not clot" | not species-specific; applies to procoagulant venoms |
| Daboia russelii | syndrome description (several symptoms) | | | | guideline | who2016guidelines | Syndrome list, printed p. 92 and p. 102 | "SYNDROME 2: Local envenoming (swelling etc) with bleeding/clotting disturbances, shock or acute kidney injury = Russell's viper ... with ptosis, external ophthalmoplegia, facial paralysis etc. and dark brown urine = Russell's viper, Sri Lanka and South India" | qualitative only |
| Echis carinatus | syndrome description | | | | guideline | who2016guidelines | Section 4 (India), printed p. 84 | "haemotoxicity without acute kidney injury (Echis carinatus); haemotoxicity and neurotoxicity with or without renal failure (Daboia russelii)" | qualitative only; Tamil Nadu syndrome-species studies |
| Echis carinatus | acute_kidney_injury | guideline: absent | | | guideline | mohfw2016stg | Flow chart "Signs and symptoms", PDF p. 7 | "Acute kidney injury (not seen with Saw scale viper)" | conflicts with gopalakrishnan2025antivenom (E. c. sochureki) |
| Daboia russelii | ptosis (regional) | guideline | | | guideline | mohfw2016stg | Flow chart note, PDF p. 7 | "Russell's viper envenoming in Tamil Nadu and some other areas commonly causes paralysis" | qualitative only |
| Daboia russelii; Echis carinatus | local swelling / blistering / necrosis (relative) | guideline | | | guideline | mohfw2016stg | 4.2.4 Vasculotoxic, PDF p. 14 | "Local manifestations - These are more prominent in Russel's viper bite followed by Saw scaled viper and least in Pit viper bite." | qualitative only |

## 2. Dry-bite rates

| species | quantity | value (n/N) | source_key | locator | verbatim quote | notes |
|---|---|---|---|---|---|---|
| Daboia russelii | dry bite rate | 2/55 (4%) | kularatne2014revisiting | Results, Clinical features | "Fifty-three (96%) of the proven Russell's viper bite patients had local or systemic envenoming, giving a dry bite rate of 4%" | hospital series (bias towards envenomed patients) |
| Daboia russelii | not envenomed | 26/336 (derived) | kularatne2003russell | Abstract | "Envenoming manifested in 310 (92%) of patients" | abstract only; 26 is derived (336 minus 310), not called "dry bites" in the abstract |
| Daboia russelii | no local envenoming | 1/245 | silva2016neurotoxicity | Abstract | "All but one had local envenoming" | confirmation partly by venom immunoassay, so likely biased towards envenomed bites |
| Daboia russelii | dry bite rate (guideline) | about 50% | who2016guidelines | Section 3.4.2, printed p. 69 (PDF p. 72) | "About 50% of bites by Malayan pit vipers and Russell's vipers, 30% of bites by cobras and 5-10% of bites by saw-scaled vipers do not result in any symptoms or signs of envenoming." | conflicts strongly with the Sri Lankan hospital series (4%) |
| Echis carinatus | dry bite rate (guideline) | 5-10% | who2016guidelines | Section 3.4.2, printed p. 69 (PDF p. 72) | (same sentence as above) | |
| Echis carinatus | dry bite rate | not found | gnanathasan2012sawscaled | Results | "The remaining 17 patients (35%) had no signs or symptoms of local envenoming." | the number with neither local nor systemic envenoming is not stated, so no dry-bite rate can be derived |
| All venomous (India) | dry bite rate (guideline) | 10-80% | mohfw2016stg | 4.2.2 Dry Bite, PDF p. 12 | "The percentage of dry bites ranges from 10-80% for various venomous snakes." | not species-specific |

## 3. Context features

| species | feature | value | probability (n/N) | source_key | locator | verbatim quote | notes |
|---|---|---|---|---|---|---|---|
| Daboia russelii | time of day | 12:00-21:00 | 67% (n not given; N = 55 proven) | kularatne2014revisiting | Results, Demographic and epidemiological data | "In the above two groups, 67% and 61% of all bites had occurred during the period 12.00–21.00 hours, respectively." | first figure = proven, second = suspected |
| Daboia russelii | time of day | dusk or dawn | not quantified | kularatne2003russell | Abstract | "Biting occurred mainly in paddy fields 41%, and on footpaths 29% at dusk or dawn." | abstract only |
| Daboia russelii | place (outdoor) | chena 53%, paddy 5.5%, in/around residential compound 20%, roadside 20% | % of 55 proven | kularatne2014revisiting | Results, Demographic and epidemiological data | "Bites had occurred in chenas (53% and 66%), paddy fields (5.5% and 13%), in and around residential compounds (20% and 11%) and by the roadside (20% and 9%) among the proven and suspected Russell's viper bite patients." | "residential compound" is not necessarily indoors; indoor/outdoor split not given |
| Daboia russelii | place (outdoor) | paddy fields 41%, footpaths 29% | % (N unclear) | kularatne2003russell | Abstract | (same sentence as above) | abstract only |
| Echis carinatus (Sri Lanka) | time of day | night | 33/48 | gnanathasan2012sawscaled | Table 1; Results | "Most (69%) bites occurred during the night." / "Time of bite Day 15 31 Night 33 69" | |
| Echis carinatus (Sri Lanka) | indoor/outdoor | outdoor | 48/48 | gnanathasan2012sawscaled | Results, Demographic and epidemiological data | "Forty-two (88%) bites were on the lower limbs and all were outdoor bites." | place: compound 26/48, footpath/roadside 11/48, paddy 3/48, bunker 4/48, forest 4/48 (Table 1) |
| Vipers and cobra (India, guideline) | time of day | day or early darkness | not quantified | mohfw2016stg | 1. Introduction, PDF p. 4 | "Maximum Viper and Cobra bites occur during the day or early darkness, while watering the plantation or walking bare foot in grown grass or soybean crops." | qualitative only |
| Daboia russelii; Echis carinatus | asleep at time of bite | not found | | | | | no source read reports this for either species |
| Echis carinatus | indoor/outdoor, time of day (India) | not found | | | | | gopalakrishnan2025antivenom reports only season ("Most bites occurred in September and October"), not time of day |

## 4. BibTeX

```bibtex
@article{kularatne2003russell,
  author  = {Kularatne, S. A. M.},
  title   = {Epidemiology and clinical picture of the {Russell's} viper ({Daboia russelii russelii}) bite in {Anuradhapura}, {Sri Lanka}: a prospective study of 336 patients},
  journal = {Southeast Asian Journal of Tropical Medicine and Public Health},
  year    = {2003},
  volume  = {34},
  number  = {4},
  pages   = {855--862},
  note    = {PMID 15115100. No DOI found. Only the abstract was read},
  url     = {https://europepmc.org/article/MED/15115100}
}

@article{kularatne2014revisiting,
  author  = {Kularatne, Senanayake A. M. and Silva, Anjana and Weerakoon, Kosala and Maduwage, Kalana and Walathara, Chamara and Paranagama, Ranjith and Mendis, Suresh},
  title   = {Revisiting {Russell's} viper ({Daboia russelii}) bite in {Sri Lanka}: is abdominal pain an early feature of systemic envenoming?},
  journal = {PLoS ONE},
  year    = {2014},
  volume  = {9},
  number  = {2},
  pages   = {e90198},
  doi     = {10.1371/journal.pone.0090198},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC3936006/}
}

@article{silva2016myotoxicity,
  author  = {Silva, Anjana and Johnston, Christopher and Kuruppu, Sanjaya and Kneisz, Daniela and Maduwage, Kalana and Kleifeld, Oded and Smith, A. Ian and Siribaddana, Sisira and Buckley, Nicholas A. and Hodgson, Wayne C. and Isbister, Geoffrey K.},
  title   = {Clinical and pharmacological investigation of myotoxicity in {Sri Lankan} {Russell's} viper ({Daboia russelii}) envenoming},
  journal = {PLoS Neglected Tropical Diseases},
  year    = {2016},
  volume  = {10},
  number  = {12},
  pages   = {e0005172},
  doi     = {10.1371/journal.pntd.0005172},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC5135039/}
}

@article{silva2016neurotoxicity,
  author  = {Silva, Anjana and Maduwage, Kalana and Sedgwick, Michael and Pilapitiya, Senaka and Weerawansa, Prasanna and Dahanayaka, Niroshana J. and Buckley, Nicholas A. and Siribaddana, Sisira and Isbister, Geoffrey K.},
  title   = {Neurotoxicity in {Russell's} viper ({Daboia russelii}) envenoming in {Sri Lanka}: a clinical and neurophysiological study},
  journal = {Clinical Toxicology},
  year    = {2016},
  volume  = {54},
  number  = {5},
  pages   = {411--419},
  doi     = {10.3109/15563650.2016.1143556},
  note    = {Only the abstract was read},
  url     = {https://researchers.une.edu.au/en/publications/neurotoxicity-in-russells-viper-daboia-russelii-envenoming-in-sri/}
}

@article{gnanathasan2012sawscaled,
  author  = {Gnanathasan, Ariaranee and Rodrigo, Chaturaka and Peranantharajah, Thambipillai and Coonghe, Anthonia},
  title   = {Saw-scaled viper bites in {Sri Lanka}: is it a different subspecies? {Clinical} evidence from an authenticated case series},
  journal = {American Journal of Tropical Medicine and Hygiene},
  year    = {2012},
  volume  = {86},
  number  = {2},
  pages   = {254--257},
  doi     = {10.4269/ajtmh.2012.11-0447},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC3269276/}
}

@article{kochar2007rediscovery,
  author  = {Kochar, D. K. and Tanwar, P. D. and Norris, R. L. and Sabir, M. and Nayak, K. C. and Agrawal, T. D. and Purohit, V. P. and Kochar, A. and Simpson, I. D.},
  title   = {Rediscovery of severe saw-scaled viper ({Echis sochureki}) envenoming in the {Thar} desert region of {Rajasthan}, {India}},
  journal = {Wilderness \& Environmental Medicine},
  year    = {2007},
  volume  = {18},
  number  = {2},
  pages   = {75--85},
  doi     = {10.1580/06-WEME-OR-078R.1},
  note    = {Only the abstract was read},
  url     = {https://journals.sagepub.com/doi/full/10.1580/06-WEME-OR-078R.1}
}

@article{gopalakrishnan2025antivenom,
  author  = {Gopalakrishnan, Maya and Kumar, Akhilesh and Tanwar, Divya and Bhat KS, Samarth and Choudhary, Bharat and Garg, Mahendra K.},
  title   = {Antivenom ineffectiveness in {Echis carinatus sochureki} envenoming: a five-year, single-centre experience from {India}},
  journal = {Transactions of the Royal Society of Tropical Medicine and Hygiene},
  year    = {2025},
  volume  = {119},
  number  = {8},
  pages   = {943},
  doi     = {10.1093/trstmh/trae111},
  note    = {End page not confirmed. A correction was published: doi 10.1093/trstmh/traf133. Read via WebFetch of the publisher HTML},
  url     = {https://academic.oup.com/trstmh/article/119/8/943/7931508}
}

@article{lath2024strikes,
  author  = {Lath, Vrinda and Shekhawat, Dimple and Sirur, Freston Marc},
  title   = {Strikes and stripes of the saw-scaled viper in the {Western Ghats}: a case series},
  journal = {Toxicology Reports},
  year    = {2024},
  volume  = {13},
  pages   = {101721},
  doi     = {10.1016/j.toxrep.2024.101721},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC11408150/}
}

@book{who2016guidelines,
  author    = {{World Health Organization Regional Office for South-East Asia}},
  title     = {Guidelines for the Management of Snakebites},
  edition   = {2nd},
  publisher = {WHO Regional Office for South-East Asia},
  address   = {New Delhi},
  year      = {2016},
  isbn      = {9789290225300},
  note      = {Drafted by D. A. Warrell. Page numbers cited are printed page numbers (printed = PDF page minus 3)},
  url       = {https://iris.who.int/handle/10665/249547}
}

@misc{mohfw2016stg,
  author       = {{Ministry of Health and Family Welfare, Government of India}},
  title        = {Standard Treatment Guidelines: Management of Snake Bite. {Quick Reference Guide}, July 2016 (final version)},
  year         = {2016},
  howpublished = {Ministry of Health and Family Welfare, Government of India},
  note         = {No DOI. Page numbers cited are PDF page numbers},
  url          = {https://clinicalestablishments.mohfw.gov.in/sites/default/files/standard-treatment-guidelines/5341.pdf}
}
```

## 5. Gaps

- **Onset windows are thin.** Only three were found: coagulopathy (Russell's viper: 0.58-16 h range from the
  2014 paper; 0.5-12 h from the 2003 abstract), abdominal pain (0.08-4 h), and neurotoxicity (all
  within 8 h). There is nothing species-specific for local swelling, bleeding, AKI, shock or vomiting
  for either species, and no onset data at all for the saw-scaled viper.
- **Kularatne 2003 full text** (336 cases) could not be retrieved (thaiscience.info redirects;
  no PMC copy). Its percentages have an unclear denominator. **Phillips 1988 (QJM)**, **Ariaratnam
  2009 (AJTMH, 860 identified snakes)** and **Kochar 2007** are paywalled; only abstracts were seen.
  No numbers were taken from the Ariaratnam 2009 abstract.
- **No authenticated Indian Russell's viper series** with symptom frequencies was found in open access.
  All Russell's viper numbers are Sri Lankan, so South Indian neurotoxic phenotypes are only covered
  by guideline text.
- **Not found for either species:** headache, regional_lymphadenopathy, progressive_swelling (with
  counts), and vomiting for Russell's viper. Saw-scaled viper AKI is conflicting: 0 per the Indian
  STG versus 19/105 for *E. c. sochureki*.
- **Dry-bite rates conflict.** WHO gives about 50% for Russell's viper, but authenticated hospital
  series give 4% (2/55), and hospital series are biased towards envenomed patients. There is no
  primary dry-bite rate for the saw-scaled viper; WHO gives 5-10%.
- **Context:** no source reports the proportion asleep or bitten indoors for either viper.
  Russell's viper time of day is given only as a 12:00-21:00 window (67%), and Indian saw-scaled viper
  time of day was not found.
- **Reviewer checks needed:** kularatne2014revisiting prints "31 (79.5%)" for 31/38 (= 81.6%).
  gnanathasan2012sawscaled Table 2 HTML rows appear misaligned. gopalakrishnan2025antivenom prints
  82.8% in the text and reportedly 83.8% in Table 2 for 87/105.
