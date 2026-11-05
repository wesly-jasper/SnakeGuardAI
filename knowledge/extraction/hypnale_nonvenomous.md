# Extraction: hump-nosed pit viper (Hypnale hypnale) and non-venomous lookalikes

Status: AI-assisted DRAFT extraction (2026-11-05). Every number still needs human verification
against the PDF (`verified=false`). Nothing here has been entered in `clinical_table.csv`.

How the text was read:
- Full text read by me: ariaratnam2008frequent (PDF from University of Colombo repository, text extracted
  locally; Table 3 columns were misaligned by pdftotext, so rows were re-matched using PyMuPDF word
  coordinates, y-position of label = y-position of value), rathnayaka2022epidemiological, abraham2025single,
  sajeethkumar2018clinical, dayasiri2025when, shahmy2017prospective (Europe PMC full-text XML),
  sirur2026hump (medRxiv HTML + Table 1/2 images), who2016guidelines (PDF), mohfw2017stg (PDF).
- ABSTRACT ONLY (full text paywalled or blocked, HTTP 403): maduwage2013epidemiology, witharana2021hump,
  thalgaspitiya2020bites. Rows from these are marked "[abstract only]".
- sirur2026hump is a medRxiv PREPRINT (not peer reviewed). Rows are marked "[preprint]".
- Denominators: "all bites" = all proven bites incl. dry bites; "envenomed" = dry bites excluded by design.
- Percentages are copied as printed. Where the printed % does not match n/N, this is flagged; I did not correct it.
- Onset conversion follows docs/phase1_plan.md: range -> range; median + IQR -> IQR; guideline text -> stated window.

## 1. Symptom frequencies and onset

### 1a. Hypnale hypnale

| species | symptom | frequency (n/N) | onset_min_h | onset_max_h | onset_basis | source_key | locator | verbatim quote |
|---|---|---|---|---|---|---|---|---|
| Hypnale hypnale | local_pain | 270/302 (89%), all bites | | | not reported | ariaratnam2008frequent | Sec 3.5.1 "Dry bites"; Table 3 row "Local pain" | "there was local swelling (276; 91%), pain (270; 89%)" |
| Hypnale hypnale | local_pain | 30/32 (94%), children >3 y able to report pain (N=40 bites) | | | not reported | rathnayaka2022epidemiological | Results, Clinical features; Table 2 | "Pain assessment was difficult in children below the age of 3 years ... pain assessment was done in 32"; abstract: "local pain (n = 30; 94%)" |
| Hypnale hypnale | local_pain | 19/41, printed as 44.1%, all confirmed bites (19/41 = 46.3%; printed % does not match) | 0.66 | 1.5 | IQR of time to any local sign (median 70 min, IQR 39.5-90 min; range 25-414 min) | abraham2025single | Results, "Local signs" | "followed by pain (n = 19, 44.1%)"; "After a bite for the local signs to manifest, the average time was 87.4 ± 75.3 min (n = 39, median = 70, IQR: 39.5–90, R: 25–414" |
| Hypnale hypnale | local_pain | 209/224 (93.3%), envenomed only (dry bites excluded) | | | not reported | sajeethkumar2018clinical | Table 2, column HNPV (n=224) | "Local pain \| 516 (96%) \| 209 (93.3%)" |
| Hypnale spp. (93/114 H. hypnale) | local_pain | 114/114, all bites [abstract only] | | | not reported | maduwage2013epidemiology | Abstract | "Pain and fang marks were present in all patients" |
| Hypnale hypnale | local_swelling | 276/302 (91%), all bites | | | not reported | ariaratnam2008frequent | Sec 3.5.1; Table 3 row "Swelling" | "Local envenoming was observed in 276 patients (91%): there was local swelling (276; 91%)" |
| Hypnale hypnale | local_swelling | 38/40 (95%), all bites (children) | | | not reported | rathnayaka2022epidemiological | Abstract; Table 2 row "Swelling" | "swelling (n = 38;95%)" |
| Hypnale hypnale | local_swelling | 34/41, printed as 79.0% (34/41 = 82.9%; printed % does not match) | 0.66 | 1.5 | IQR of time to any local sign (median 70 min, IQR 39.5-90 min) | abraham2025single | Results, "Local signs" | "edema or swelling at the bite site (n = 34, 79.0%)" |
| Hypnale hypnale | local_swelling | 204/224 (91%), envenomed only | | | not reported | sajeethkumar2018clinical | Table 2, HNPV column | "Local swelling \| 509 (94.6%) \| 204 (91%)" |
| Hypnale spp. (93/114 H. hypnale) | local_swelling | 101/114, all bites [abstract only] | | | not reported | maduwage2013epidemiology | Abstract | "101 had local swelling" |
| Hypnale spp. (Deniyaya; 39 of 52 identified dead specimens were H. zara) | local_swelling | 69/83 (83.1%) [abstract only; genus, mostly H. zara] | | | not reported | witharana2021hump | Abstract | "sixty nine (83.1%) had local swelling" |
| Hypnale spp. (93/114 H. hypnale) | progressive_swelling | 16/114 (14%) [abstract only] | | | not reported | maduwage2013epidemiology | Abstract | "only 16 (14%) developed extensive local swelling that spread proximally and involved more than half of the bitten limb" |
| Hypnale hypnale | progressive_swelling | 18/40 moderate (>half limb) + 17/40 severe (whole limb); the sum 35/40 is MY derivation, not printed | | | not reported | rathnayaka2022epidemiological | Methods (grading); Table 2 rows Swelling Mild/Moderate/Severe = 3 (7.5) / 18 (45) / 17 (42.5) | "extension to more than half of the limb was graded moderate; and extension to whole limb was graded severe" |
| Hypnale hypnale (n=13 subset) | progressive_swelling | 7.7% of 13 H. hypnale (n not printed) [abstract only] | | | not reported | witharana2021hump | Abstract | "H. hypnale bites had 7.7% each extensive limb swelling and coagulopathy and 23.1% haemorrhagic blisters" |
| Hypnale hypnale | blistering | 186/302 (62%), all bites | | | not reported | ariaratnam2008frequent | Sec 3.5.1; Table 3 row "Blistering" | "bruising (145; 48%) and blistering (186; 62%)" |
| Hypnale hypnale | blistering | 11/40 (27.5%), all bites (children) | | | not reported | rathnayaka2022epidemiological | Abstract; Table 2 | "blistering (n = 11;27.5%)" |
| Hypnale hypnale (n=13 subset) | blistering | 23.1% of 13 (haemorrhagic blisters; n not printed) [abstract only] | | | not reported | witharana2021hump | Abstract | "23.1% haemorrhagic blisters" |
| Hypnale hypnale | local_necrosis | 48/302 (16%), all bites | | | not reported | ariaratnam2008frequent | Sec 3.5.1; Table 3 row "Necrosis" = 48 (16) | "Forty-eight patients (16%) developed local necrosis" |
| Hypnale hypnale | local_necrosis | 11/40 (27.5%), all bites (children) | | | not reported | rathnayaka2022epidemiological | Abstract; Table 2 | "necrosis at the site of bite (n = 11; 27.5%)" |
| Hypnale hypnale | local_necrosis | 81/224 (36.16%), envenomed only; COMBINED category (cellulitis + necrosis + gangrene), not necrosis alone | | | not reported | sajeethkumar2018clinical | Table 2, HNPV column | "Local cellulitis, necrosis, and gangrene \| 105 (19.5%) \| 81 (36.16%)" |
| Hypnale hypnale | regional_lymphadenopathy | 8/40 (20%), all bites (children) | | | not reported | rathnayaka2022epidemiological | Abstract; Table 2 | "regional lymph node enlargement (n = 8;20%)" |
| Hypnale hypnale | regional_lymphadenopathy | 101/224 (45%), envenomed only | | | not reported | sajeethkumar2018clinical | Table 2, HNPV column | "Regional lymphadenopathy \| 121 (41%) \| 101 (45%)" |
| Hypnale spp. (Deniyaya, mostly H. zara) | regional_lymphadenopathy | 7/83 (8.4%) [abstract only; genus] | | | not reported | witharana2021hump | Abstract | "seven (8.4%) regional lymphadenopathy" |
| Hypnale hypnale | incoagulable_blood | 117/302 (39%), all bites | 0.25 | 48 | range of first detection | ariaratnam2008frequent | Sec 3.5.2; Table 3 row "Coagulopathy (incoagulable blood (20WBCT))" = 117 (39) | "In 117 patients (39%) blood incoagulability was first detected between 15 min and 48 h after the bite, and in 116 of them this was present on admission to hospital" |
| Hypnale hypnale | incoagulable_blood | 4/40 (10%) VICC, all bites (children); positive 20WBCT only 2/40 (Table 3) | | | not reported | rathnayaka2022epidemiological | Results, Clinical features; Table 3 row "Positive 20 min WBCT" = 2 (5) | "Systemic manifestations were observed in 4 (10%) who had VICC" |
| Hypnale hypnale | incoagulable_blood | 8/41 (19.5%), all confirmed bites | | | median only: 7.5 h (mean 11.3 h). Printed IQR "0.22–0.76" and range "1.2–3" are inconsistent with a 7.5 h median (look like days); NOT used | abraham2025single | Results, "Coagulopathy and its resolution" | "The mean time to detect coagulopathy was 11.3 ± 10.1 (n = 8, median = 7.5, IQR: 0.22–0.76, R: 1.2–3) h." |
| Hypnale hypnale | incoagulable_blood | 216/224 (96.4%), envenomed only. CAUTION: "coagulopathy" = prolonged PT, not 20WBCT; far higher than every other series | | | not reported | sajeethkumar2018clinical | Table 2, HNPV column; Results | "Coagulopathy \| 528 (98.1%) \| 216 (96.4%)"; "Prolongation of prothrombin time was observed ... in 96.4% with HNPV bite" |
| Hypnale hypnale | incoagulable_blood | 24/46 (52.2%) "local & systemic" = coagulopathy by INR or TEG, all bites [preprint] | | | not reported | sirur2026hump | Table 2 row "Local & Systemic signs of envenomation"; Results text | "24 patients had both local signs ... and systemic envenomation in the form of coagulopathy, evidenced either by derangement in INR value or by TEG" |
| Hypnale spp. (93/114 H. hypnale) | incoagulable_blood | 4/114 abnormal 20WBCT [abstract only] | | | not reported | maduwage2013epidemiology | Abstract | "four patients had an abnormal 20 min whole blood clotting test" |
| Hypnale hypnale (n=13 subset) | incoagulable_blood | 7.7% of 13 (n not printed) [abstract only] | | | not reported | witharana2021hump | Abstract | "H. hypnale bites had 7.7% each extensive limb swelling and coagulopathy" |
| Hypnale hypnale | systemic_bleeding | 55/302 (18%), all bites | | | not reported | ariaratnam2008frequent | Sec 3.5.2; Table 3 row "Spontaneous systemic haemorrhage: total" = 55 (18) | "Spontaneous systemic bleeding in the form of gingival bleeding, haematuria and haematemesis was observed in 55 patients (18%)" |
| Hypnale hypnale | systemic_bleeding | 131/224 (58.4%), envenomed only | | | not reported | sajeethkumar2018clinical | Table 2, HNPV column | "Systemic bleeding manifestations \| 314 (58.3%) \| 131 (58.4%)" |
| Hypnale hypnale | acute_kidney_injury | 30/302 (10%), all bites | | | not reported | ariaratnam2008frequent | Sec 3.5.2; Table 3 row "Acute renal failure" = 30 (10) | "Thirty patients (10%) developed acute renal failure requiring dialysis" |
| Hypnale hypnale | acute_kidney_injury | 0/40, all bites (children) | | | not applicable | rathnayaka2022epidemiological | Discussion | "However, AKI was not observed in present study." |
| Hypnale hypnale | acute_kidney_injury | 2/41 (4.8%), all confirmed bites | | | not reported | abraham2025single | Results, "Systemic signs" | "8 (19.5%) developed coagulopathy and 2 (4.8%) developed renal failure" |
| Hypnale hypnale | acute_kidney_injury | 44/224 (19.6%), envenomed only | | | not reported | sajeethkumar2018clinical | Table 2, HNPV column | "AKI \| 189 (35.1%) \| 44 (19.6%)" |
| Hypnale hypnale | acute_kidney_injury | 10/46 (21.7%), all bites [preprint] | | | not reported | sirur2026hump | Table 2 "Complications" | "Acute Kidney injury (HD) 10 (21.7%)" |
| Hypnale spp. (93/114 H. hypnale) | acute_kidney_injury | 1/114 [abstract only] | | | not reported | maduwage2013epidemiology | Abstract | "one patient developed an acute kidney injury that required haemodialysis" |
| Hypnale hypnale | shock | 2/46 (4.35%) on arrival, all bites [preprint] | | | not reported | sirur2026hump | Table 2 "Clinical presentation" | "Shock on arrival 2 (4.35%)" |
| Hypnale hypnale | ptosis | 0/302, all bites | | | not applicable | ariaratnam2008frequent | Sec 3.5.2 | "Neurological manifestations were not observed in any patient." |
| Hypnale hypnale | ophthalmoplegia | 0/302, all bites | | | not applicable | ariaratnam2008frequent | Sec 3.5.2 | "Neurological manifestations were not observed in any patient." |
| Hypnale hypnale | bulbar_palsy | 0/302, all bites | | | not applicable | ariaratnam2008frequent | Sec 3.5.2 | "Neurological manifestations were not observed in any patient." |
| Hypnale hypnale | respiratory_paralysis | 0/302, all bites | | | not applicable | ariaratnam2008frequent | Sec 3.5.2 | "Neurological manifestations were not observed in any patient." |
| Hypnale hypnale | limb_weakness | 0/302, all bites | | | not applicable | ariaratnam2008frequent | Sec 3.5.2 | "Neurological manifestations were not observed in any patient." |
| Hypnale spp. (Deniyaya, mostly H. zara) | ptosis / any neurotoxic sign | 0/83 [abstract only; genus] | | | not applicable | witharana2021hump | Abstract | "Neurotoxicity was not noted." |
| Hypnale hypnale | abdominal_pain | 45/302 (15%), all bites | | | not reported | ariaratnam2008frequent | Table 3 row "Abdominal pain" = 45 (15) (row matched by word coordinates, see header) | Table 3: "Abdominal pain ... 45 (15)" |
| Hypnale hypnale | abdominal_pain | 2/40 (5%), all bites (children) | | | not reported | rathnayaka2022epidemiological | Results, Clinical features | "Three (7.5%) were found to have non-specific envenoming features including abdominal pain in 2 (5%) and headache in 1 (2.5%)." |
| Hypnale hypnale | vomiting | 60/302 (20%) "Nausea and vomiting", all bites | | | not reported | ariaratnam2008frequent | Table 3 row "Nausea and vomiting" = 60 (20) (matched by word coordinates) | Table 3: "Nausea and vomiting ... 60 (20)" |
| Hypnale hypnale | vomiting | 91/224 (40.6%), envenomed only | | | not reported | sajeethkumar2018clinical | Table 2, HNPV column | "Vomiting \| 393 (73%) \| 91 (40.6%)" |
| Hypnale hypnale | headache | 1/40 (2.5%), all bites (children) | | | not reported | rathnayaka2022epidemiological | Results, Clinical features | "headache in 1 (2.5%)" |

Not found for H. hypnale: shock in any peer-reviewed series read; headache in adult series with a
frequency; onset windows for any symptom except "any local sign" (abraham2025single) and
incoagulable blood (ariaratnam2008frequent; abraham2025single median only).

Extra figures seen but not in the vocabulary: Ariaratnam 2008 Table 3 also lists Local bleeding 125 (41),
Bruising 145 (48), Gum bleeding 25 (8), Haematuria 18 (6), Haematemesis 12 (4), Giddiness 22 (7),
"Non-specific symptoms" total 65 (22). Sajeeth Kumar Table 2: "Bleeding from the bite site 206 (91.9%)".

### 1b. Non-venomous lookalikes (Ptyas mucosa, Lycodon aulicus, Fowlea piscator)

No species-specific symptom frequency was found for any of the three species. The only numbers
available are pooled across "snakes of lesser medical importance" or across unidentified bites.

| species | symptom | frequency (n/N) | onset_min_h | onset_max_h | onset_basis | source_key | locator | verbatim quote |
|---|---|---|---|---|---|---|---|---|
| pooled non-venomous / lesser medical importance (12 colubrid spp. + others; incl. 12 L. aulicus) | local_pain + local_swelling (reported together) | 5/76 [abstract only] | | | not reported | thalgaspitiya2020bites | Abstract | "None of the patients developed systemic envenoming and five developed mild local pain and swelling." |
| pooled non-venomous / lesser medical importance | any systemic sign | 0/76 [abstract only] | | | not applicable | thalgaspitiya2020bites | Abstract | "None of the patients developed systemic envenoming" |
| pooled non-venomous / mildly venomous, children (59 rat snake, 56 water snake, 10 wolf snake, ...); species ID by caregiver in 59.6% | any complication | 0/183 complications directly related to the bite; 12/183 (6.6%) antibiotics for secondary infection (not in vocabulary) | | | not applicable | dayasiri2025when | Results, "Complications and outcome of the hospitalisation" | "All children were discharged home without any complications directly related to the snakebite. Twelve children (6.6%) received antibiotics as for a secondary bacterial infection of the bite site." |
| unidentified bites (NOT proven non-venomous) | local_pain only | 189/1208 unidentified bites; plus 315/1208 "dry bites" (no symptoms) | | | not reported | shahmy2017prospective | Discussion, para on identification | "Snakes were not identified in more than 50% (1208) of bites. Among them 315 are dry bites and 189 cases had only pain at the site of bite. Probably, all these cases are non-venomous bite" |
| non-venomous bites (guideline, no species) | local_swelling (from tight ligature, not venom) | guideline text, no frequency | | | guideline text | mohfw2017stg | p. 11 (PDF p. 17), "Asymptomatic (i.e., non Venom related symptoms)" | "However, local swelling can be present in these patients due to tight ligature." |
| non-venomous bites (guideline, no species) | anxiety features (not in vocabulary) | guideline text, no frequency | | | guideline text | mohfw2017stg | p. 11 (PDF p. 17) | "Palpitations, sweating, tremulousness, tachycardia, tachypnoea, elevated blood pressure, cold extremities and paraesthesia" |
| non-venomous bites (guideline, no species) | none | guideline text | | | guideline text | who2016guidelines | p. 93 (PDF p. 95), Sec 5 | "No physical effects other than the fang/ tooth puncture. This is explained by bites by non-venomous snakes, animals other than snakes ... or \"dry bites\" by venomous snakes in which no venom was injected." |
| Fowlea (Xenochrophis) piscator | (no symptom data) | not found | | | | who2016guidelines | p. 83 (PDF p. 85), India | "Bites by non-venomous species such as checkered keelback/Asiatic water snake (Xenochrophis piscator) are common and may cause confusion among medical staff and lead to inappropriate" (sentence continues on next page; not read) |

Observation window (guideline text, relevant to censoring non-venomous/dry patients in the simulator):
- mohfw2017stg, p. 49 (PDF p. 55), Discharge: "If no symptoms and signs develop after 24 hours the patient can be discharged."
- mohfw2017stg, p. 10 (PDF p. 16): "Admit all victims of snakebite confirmed or suspected and keep under observation for 24 hours."

## 2. Dry-bite / no-envenoming rates

| species | feature | value (n/N) | onset_min_h | onset_max_h | onset_basis | source_key | locator | verbatim quote |
|---|---|---|---|---|---|---|---|---|
| Hypnale hypnale | dry_bite_rate | 26/302 (9%), all proven bites | | | | ariaratnam2008frequent | Sec 3.5.1 "Dry bites"; Table 3 "Not envenomed 26 (9)" | "Twenty-six patients (9%) showed no evidence of envenoming at any stage despite proven bites by hump-nosed pit vipers." |
| Hypnale hypnale | dry_bite_rate | 2/40 (5%), children; 14/40 snakes identified only by admitting medical officers | | | | rathnayaka2022epidemiological | Results, Clinical features | "There were 2 (5%) patients with dry bites who did not show any envenoming features in spite of having fang punctures at the site of bite" |
| Hypnale hypnale | dry_bite_rate | 2/41 (4.8%), expert-confirmed specimens/photos | | | | abraham2025single | Results, "Local signs" | "There were two (4.8%) dry bites." |
| Hypnale hypnale | dry_bite_rate | 3/46 (6.5%) [preprint] | | | | sirur2026hump | Table 2 "No signs of envenomation"; Results | "3 patients did not have any signs of envenomation." |
| venomous snakes in general | dry_bite_rate | 5-80% by species, average about 50% (guideline text) | | | guideline text | who2016guidelines | p. 79 (PDF p. 81), Sec 4.2 | "The incidence of dry bites varies with the species, from 5-80%, average about 50%" |
| Russell's viper / cobra / saw-scaled viper (context for other files) | dry_bite_rate | ~50% / 30% / 5-10% (guideline text) | | | guideline text | who2016guidelines | p. 69 (PDF p. 71), Sec 3.4.2 | "About 50% of bites by Malayan pit vipers and Russell's vipers, 30% of bites by cobras and 5-10% of bites by saw-scaled vipers do not result in any symptoms or signs of envenoming." |
| venomous snakes in general | dry_bite_rate | 10-80% (Indian guideline text) | | | guideline text | mohfw2017stg | p. 11 (PDF p. 17), "Dry Bite" | "The percentage of dry bites ranges from 10–80% for various venomous snakes." |
| all suspected bites (India) | proportion non-venomous | 70% (flow-chart label, no source given in figure) | | | guideline text | mohfw2017stg | p. 6 (PDF p. 12) flow chart; p. 7 | "Nonvenomous (70%) / venomous (30%)"; "Reassure the patient as around 70% of all snakebites are from non-venomous species." |

Not found: a dry-bite rate for Hypnale in Maduwage 2013 or Witharana 2021 abstracts (full texts not accessed).
Not applicable for non-venomous species.

## 3. Context features

| species | feature | value (n/N) | onset_min_h | onset_max_h | onset_basis | source_key | locator | verbatim quote |
|---|---|---|---|---|---|---|---|---|
| Hypnale hypnale | time 00:00-06:00 | 17/302 (6%) | | | | ariaratnam2008frequent | Sec 3.3 "Time of the bites" | "00:00--06:00 h, 17 (6%); 06:00--12:00 h, 48 (16%); 12:00--18:00 h, 86 (28%); and 18:00--00:00 h, 151 (50%)" |
| Hypnale hypnale | time 06:00-12:00 | 48/302 (16%) | | | | ariaratnam2008frequent | Sec 3.3 | (same quote) |
| Hypnale hypnale | time 12:00-18:00 | 86/302 (28%) | | | | ariaratnam2008frequent | Sec 3.3 | (same quote) |
| Hypnale hypnale | time 18:00-00:00 | 151/302 (50%) | | | | ariaratnam2008frequent | Sec 3.3 | (same quote) |
| Hypnale hypnale | asleep | 4/302 (1%) | | | | ariaratnam2008frequent | Sec 3.4 | "Only four (1%) were bitten while sleeping." |
| Hypnale hypnale | indoors (inside house) | 6/302 (2%) | | | | ariaratnam2008frequent | Sec 3.4 | "Only six bites (2%) occurred within the patient's house." |
| Hypnale hypnale | outdoors: compound / road-footpath / paddy | 146/302 (48%) / 90/302 (30%) / 33/302 (11%) | | | | ariaratnam2008frequent | Sec 3.4 | "One hundred and forty-six bites (48%) occurred within the patient's compound, 90 (30%) on roads or footpaths and 33 (11%) in paddy fields." |
| Hypnale hypnale | day (06:00-17:59) / night (18:00-05:59) | 21/40 (52.5%) / 19/40 (47.5%), children | | | | rathnayaka2022epidemiological | Table 1 "Time of bite"; Results | "Most children (n = 21;52.5%) were bitten at day-time (06:00–17:59)"; Table 1: "Night-time bites (18:00–05:59) ... 19 (47.5)", sub-rows 18:00-23:59 16 (40), 00:00-05:59 3 (7.5). Note Table 1 prints the day window as "00:06–17:59" (typo vs text). |
| Hypnale hypnale | indoors (inside home) / home garden | 9/40 (22.5%) / 20/40 (50%), children | | | | rathnayaka2022epidemiological | Table 1 "Place of bites" | "Home garden Inside home ... 20 (50)9 (22.5)" |
| Hypnale hypnale | asleep | 1/40 (single narrative case; count is mine from the text) | | | | rathnayaka2022epidemiological | Results, Epidemiological features | "A 7-year-old girl (Serial No.21) was bitten by H. zara ... while she was sleeping on a bed." NOTE: this snake was H. zara, not H. hypnale. |
| Hypnale hypnale | time 00:00-07:00 / 07:00-12:00 / 12:00-19:00 / 19:00-00:00 | 5/46 (10.9%) / 13/46 (printed 32.6%; 13/46 = 28.3%, mismatch) / 16/46 (34.8%) / 10/46 (21.7%) [preprint] | | | | sirur2026hump | Table 1 "Time of bite" | Table 1: "00:00 – 07:00 5 (10.9%) ... 07:00 – 12:00 13 (32.6%) ... 12:00 – 19:00 16 (34.8%) ... 19:00 – 00:00 10 (21.7%)" |
| Hypnale hypnale | circumstance "At Residence" | 7 (printed 15.9%; implies N=44, not 46) [preprint] | | | | sirur2026hump | Table 1 "Circumstances of Bite" | "At Residence 7 (15.9%)" (indoor vs outdoor not stated) |
| Hypnale spp. (93/114 H. hypnale) | daytime | "most", no number [abstract only] | | | | maduwage2013epidemiology | Abstract | "Most bites occurred on the lower limbs in the daytime." |
| Hypnale spp. (Deniyaya, mostly H. zara) | daytime | 80/83 (96.4%) [abstract only; genus] | | | | witharana2021hump | Abstract | "Eighty (96.4%) were daytime bites." |
| pooled non-venomous, children (rat snake 59, water snake 56, wolf snake 10, ...) | morning / midday / evening / night | 38/183 (20.8%) / 47/183 (25.7%) / 54/183 (29.5%) / 44/183 (24.0%) | | | | dayasiri2025when | Results, "Circumstances of the snakebites" | "38 cases (20.8%) occurred in the morning, 47 cases (25.7%) at midday, 54 cases (29.5%) in the evening and 44 cases (24.0%) at night." (clock hours not defined) |
| pooled non-venomous, children | indoors (inside the home) | 55/183 (30.1%) | | | | dayasiri2025when | Results, "Location of snakebites" | "A total of 55 bites (30.1%) occurred inside the home, while 60 bites (32.8%) took place in the home garden." |
| pooled non-venomous, children | resting or sleeping | 2/183 (1.1%) | | | | dayasiri2025when | Results, "Circumstances of the snakebites" | "Resting or sleeping incidents were reported in two cases (1.1%)." |
| pooled lesser medical importance (authenticated, 76 bites) | indoors or home garden | 86% (n not printed) [abstract only] | | | | thalgaspitiya2020bites | Abstract | "Most patients (86%) were bitten indoors or at home gardens." |
| pooled lesser medical importance (authenticated, 76 bites) | time 18:00-00:00 | "more than half" (no number) [abstract only] | | | | thalgaspitiya2020bites | Abstract | "More than half of them were bitten between 1800 and 0000 h." |

Not found: species-level context data for P. mucosa, L. aulicus or F. piscator.

## 4. BibTeX

```bibtex
@article{ariaratnam2008frequent,
  author  = {Ariaratnam, C. A. and Thuraisingam, V. and Kularatne, S. A. M. and Sheriff, M. H. R. and Theakston, R. D. G. and de Silva, A. and Warrell, D. A.},
  title   = {Frequent and potentially fatal envenoming by hump-nosed pit vipers ({Hypnale hypnale} and {H. nepa}) in {Sri Lanka}: lack of effective antivenom},
  journal = {Transactions of the Royal Society of Tropical Medicine and Hygiene},
  year    = {2008},
  volume  = {102},
  number  = {11},
  pages   = {1120--1126},
  doi     = {10.1016/j.trstmh.2008.03.023},
  url     = {https://archive.cmb.ac.lk/server/api/core/bitstreams/032fb0ad-b035-44a5-8895-1ab64e2a7a98/content}
}

@article{rathnayaka2022epidemiological,
  author  = {Rathnayaka, R. M. M. K. Namal and Ranathunga, P. E. Anusha Nishanthi and Kularatne, S. A. M.},
  title   = {Epidemiological and clinical features of hump-nosed pit viper ({Hypnale hypnale} and {Hypnale zara}) envenoming in children},
  journal = {PLoS Neglected Tropical Diseases},
  year    = {2022},
  volume  = {16},
  number  = {12},
  pages   = {e0011013},
  doi     = {10.1371/journal.pntd.0011013},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC9822102/}
}

@article{abraham2025single,
  author  = {Abraham, Siju V. and Paul, Sarah and Paul, Martin V. and Davis, Clint and Rafi, Aboobacker Mohamed and Suseel, Appu and Mathew, Deo and Kassyap, C. K. and Chathappan, Rajeev Punchalil},
  title   = {A Single-Center Review of Cases to Understand the {Indian} Polyvalent Antivenom Use in Hump-Nosed Pit Viper Bites in {South India}},
  journal = {Journal of Emergencies, Trauma, and Shock},
  year    = {2025},
  volume  = {18},
  number  = {1},
  pages   = {15--21},
  doi     = {10.4103/jets.jets_74_24},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC12020926/}
}

@article{sajeethkumar2018clinical,
  author  = {Sajeeth Kumar, K. G. and Narayanan, Santhosh and Udayabhaskaran, V. and Thulaseedharan, N. K.},
  title   = {Clinical and epidemiologic profile and predictors of outcome of poisonous snake bites -- an analysis of 1,500 cases from a tertiary care center in {Malabar}, {North Kerala}, {India}},
  journal = {International Journal of General Medicine},
  year    = {2018},
  volume  = {11},
  pages   = {209--216},
  doi     = {10.2147/IJGM.S136153},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC5993036/}
}

@misc{sirur2026hump,
  author       = {Sirur, Freston Marc and Lath, Vrinda and Lingappa, Devika Jabagodu and Ramya and Kulkarni, Nirmal U and Kamath, Asha and Wagle, Usha},
  title        = {Hump nosed pit viper envenoming in {Coastal Karnataka}- unravelling the centuries of deadly camouflage},
  year         = {2026},
  howpublished = {medRxiv preprint (not peer reviewed), posted 2026-03-06},
  doi          = {10.64898/2026.03.05.26347697},
  url          = {https://www.medrxiv.org/content/10.64898/2026.03.05.26347697v1.full}
}

@article{maduwage2013epidemiology,
  author  = {Maduwage, K. and Isbister, G. K. and Silva, A. and Bowatta, S. and Mendis, S. and Gawarammana, I.},
  title   = {Epidemiology and clinical effects of hump-nosed pit viper ({Genus: Hypnale}) envenoming in {Sri Lanka}},
  journal = {Toxicon},
  year    = {2013},
  volume  = {61},
  pages   = {11--15},
  doi     = {10.1016/j.toxicon.2012.10.013},
  url     = {https://europepmc.org/article/MED/23127899},
  note    = {Abstract only was read}
}

@article{witharana2021hump,
  author  = {Witharana, E. W. R. A. and Gnanathasan, A. and Dissanayake, A. S. and Wijesinghe, S. K. J. and Kadahetti, S. C. L. and Rajapaksha, R. M. J. K.},
  title   = {Hump-nosed pit viper ({Hypnale hypnale} and {Hypnale zara}) envenoming in {Deniyaya}, {Sri Lanka}: Epidemiological and clinical features from a prospective observational study},
  journal = {Toxicon},
  year    = {2021},
  volume  = {189},
  pages   = {19--23},
  doi     = {10.1016/j.toxicon.2020.10.026},
  url     = {https://europepmc.org/article/MED/33144122},
  note    = {Abstract only was read}
}

@article{thalgaspitiya2020bites,
  author  = {Thalgaspitiya, S. and Isbister, G. and Ukuwela, K. and Sarathchandra, C. and Senanayake, H. and Lokunarangoda, N. and Siribaddana, S. and Silva, A.},
  title   = {Bites by snakes of lesser medical importance in a cohort of snakebite patients from rural {Sri Lanka}},
  journal = {Toxicon},
  year    = {2020},
  volume  = {187},
  pages   = {105--110},
  doi     = {10.1016/j.toxicon.2020.08.025},
  url     = {https://europepmc.org/article/MED/32891665},
  note    = {Abstract only was read}
}

@article{dayasiri2025when,
  author  = {Dayasiri, Kavinda and Ranasinghe, Achila and Suraweera, Nayani and Burhan, Priyanga},
  title   = {When the bite is not the threat: non-venomous snakebites and their impact on rural child health},
  journal = {BMJ Paediatrics Open},
  year    = {2025},
  volume  = {9},
  number  = {1},
  pages   = {e003583},
  doi     = {10.1136/bmjpo-2025-003583},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC12306283/}
}

@article{shahmy2017prospective,
  author  = {Shahmy, Seyed and Kularatne, Senanayake A. M. and Rathnayake, Shantha S. and Dawson, Andrew H.},
  title   = {A prospective cohort study of the effectiveness of the primary hospital management of all snakebites in {Kurunegala} district of {Sri Lanka}},
  journal = {PLoS Neglected Tropical Diseases},
  year    = {2017},
  volume  = {11},
  number  = {8},
  pages   = {e0005847},
  doi     = {10.1371/journal.pntd.0005847},
  url     = {https://pmc.ncbi.nlm.nih.gov/articles/PMC5578683/}
}

@book{who2016guidelines,
  author    = {Warrell, David A. and {World Health Organization Regional Office for South-East Asia}},
  title     = {Guidelines for the management of snakebites},
  edition   = {2nd},
  publisher = {World Health Organization Regional Office for South-East Asia},
  address   = {New Delhi},
  year      = {2016},
  isbn      = {9789290225300},
  doi       = {none},
  url       = {https://iris.who.int/handle/10665/249547},
  note      = {Read from copy at https://biomedicalsciences.unimelb.edu.au/__data/assets/pdf_file/0008/2774186/SEARO-Guidelines-for-the-Management-of-Snakebites-2016-2nd-Edition.pdf; printed page = PDF page - 2}
}

@techreport{mohfw2017stg,
  author      = {{Ministry of Health and Family Welfare, Government of India}},
  title       = {Standard Treatment Guidelines: Management of Snake Bite},
  institution = {Ministry of Health and Family Welfare, Government of India (National Health Mission)},
  year        = {2017},
  month       = aug,
  doi         = {none},
  url         = {https://ncdc.mohfw.gov.in/uploads/pdf/Standard-Treatment-Guidelines-for-Management-of-Snake-Bite.pdf},
  note        = {Printed page = PDF page - 6}
}
```

## 5. Gaps and caveats

- Non-venomous species: no peer-reviewed source with symptom frequencies, onset or context for
  Ptyas mucosa, Lycodon aulicus or Fowlea piscator individually. Only pooled "lesser medical importance"
  data (thalgaspitiya2020bites, abstract only, authenticated; dayasiri2025when, children, ID mostly by
  caregiver) and unidentified-bite data (shahmy2017prospective). Thalgaspitiya full text (Toxicon, paywalled)
  may hold per-species rows (12 L. aulicus bites) and should be obtained.
- Ariaratnam et al. 2009 (AJTMH 81:725, doi 10.4269/ajtmh.2009.09-0225) could not be read (HTTP 403);
  its abstract says "Of 860 snakes ... 762 (89%) were venomous" (so about 98 were not; my subtraction), so the full text may contain symptoms after
  proven non-venomous bites. Not used for any number here.
- Paywalled Hypnale series read as abstract only: Maduwage 2013, Witharana 2021. Not read at all:
  Joseph et al. 2007 (Kerala, n=5, qualitative), Wijewantha & Sellahewa 2010 (1543 cases), Sellahewa 1994,
  Kularatne 2011, Rathnayaka 2021 (H. zara, not target species).
- Onset windows: only "any local sign" (median 70 min, IQR 39.5-90 min) and incoagulable blood
  (15 min-48 h range; median 7.5 h in a small series) were found. No onset data for AKI, bleeding,
  necrosis, blistering, lymphadenopathy, vomiting or abdominal pain.
- Data-quality flags: abraham2025single printed percentages for swelling/pain do not match n/41, and its
  coagulopathy-onset IQR/range are inconsistent with the median; sajeethkumar2018clinical reports 96.4%
  "coagulopathy" (prolonged PT) in envenomed HNPV bites, far above other series (4-39%); sirur2026hump is
  a preprint with one % that does not match n/N; ariaratnam2008frequent Table 3 needed coordinate-based
  re-alignment, so its rows should be checked by eye against the PDF.
- Denominators differ (all bites vs envenomed only vs children only); do not pool without adjusting.
- Shock: only 2/46 "shock on arrival" in a preprint. Headache: only 1/40 in children.
- mohfw2017stg (p. 12, PDF p. 18) says, in the neuroparalytic section, "Many species, particularly the
  Krait and the humpnosed pit viper are known for delayed appearance of symptoms which can develop after
  6–12 hours". This conflicts with the absence of neurotoxicity in all Hypnale series above; I did not use it.
- Time-of-day categories differ between sources (4 x 6 h blocks; day/night split at 06:00/18:00;
  morning/midday/evening/night with no clock hours); a mapping decision is needed before use.
