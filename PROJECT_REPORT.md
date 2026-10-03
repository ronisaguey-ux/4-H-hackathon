# PROJECT REPORT — CornShield AI: Midwest Corn Foliar Disease Early-Detection, Severity & Extension Treatment Platform

**Competition:** National 4-H AI in Agriculture Challenge (Fall 2026)  
**Division:** Level 2 (Ages 16–18 Division)  
**Author / Entrant:** Roni Saguey  
**Project Repository:** https://github.com/ronisaguey-ux/4-H-hackathon.git  
**Submission Portal:** https://events.projectboard.world/4HAIinAg  
**Date:** October 2026  

---

## Executive Summary

American corn growers plant more than 90 million acres annually, with over 13 million acres in Iowa alone. Over the past decade, the rapid emergence and geographic spread of **Tar Spot** (*Phyllachora maydis*) and destructive foliar blights like **Gray Leaf Spot** (*Cercospora zeae-maydis*) have emerged as an existential threat to Corn Belt grain yields, inflicting documented losses of **50 to 60 bushels per acre** in severe epidemic seasons and costing Midwestern farmers an estimated **$1.2 to $3 billion** in lost production and lodging.

Traditional diagnosis relies on physical scouting and mailing foliar leaf samples to university diagnostic clinics (such as the Iowa State University Plant and Insect Diagnostic Clinic), costing $25 to $40 per assay and requiring a **5 to 10 business day turnaround**. Because Tar Spot has an explosive 12-to-14-day polycyclic infection cycle, this delay often allows the disease to defoliate the critical "ear leaf" (responsible for over 70% of grain fill photosynthate) before chemical control can be applied, causing irreversible yield collapse.

**CornShield AI** is an AI-powered, field-deployable crop disease diagnostic and severity service designed specifically for Midwestern corn growers. By combining multimodal vision models with local color-space lesion segmentation and a curated Land-Grant University Extension database, CornShield AI:
1. Identifies foliar pathogens in sub-second field scans with explicit calibration: if confidence falls below a safe **70% action floor**, the system hedges with an honest **"unsure"** verdict and provides a step-by-step physical retake protocol (including the critical "Water Rub Test" to distinguish harmless insect frass from fungal stromata).
2. Calculates quantitative **leaf area affected (%)** and assigns an actionable extension severity grade (**Early**, **Moderate**, **Severe**) with an interactive lesion segmentation overlay.
3. Retrieves **verified treatment protocols strictly quoted from Land-Grant University Extension publications** (Crop Protection Network CPN-2012, Iowa State Extension IPM 0044, Purdue Extension BP-89-W), eliminating dangerous hallucinated pesticide recommendations.
4. Maintains an offline SQLite scouting database tracking disease spread velocity across field plots over time.
5. Operates at **$0.0015 per scan** (0.15 cents), making advanced agronomic AI accessible to small family farms and 4-H youth projects.

---

## 1. Problem Identification & Local Midwest Context

### 1.1 The Local Agronomic Crisis: Tar Spot in Iowa & the Corn Belt
Tar Spot, caused by the obligate fungal ascomycete *Phyllachora maydis*, was first confirmed in the United States in northern Indiana and Illinois in 2015. By 2018–2021, the disease had rapidly spread across the Upper Midwest, establishing a permanent overwintering reservoir in corn residue across Iowa, Illinois, Indiana, Wisconsin, and Michigan.

According to multi-state field trials compiled by the **Crop Protection Network (CPN)** and **Iowa State University Extension and Outreach (Publication IPM 0044 / CPN-2012)**:
* In severe epidemic seasons, Tar Spot defoliation causes **yield reductions exceeding 50 to 60 bushels per acre**.
* At typical market prices ($4.50–$5.50/bu), a 55 bu/acre loss represents a catastrophic revenue loss of **$247 to $302 per acre**.
* On a standard 500-acre family corn operation, a single unmanaged Tar Spot outbreak can erase over **$125,000 in gross margin**.
* Beyond direct grain shrinkage, the pathogen induces rapid premature plant dry-down, prompting the plant to cannibalize carbohydrates from the lower stalk to fill remaining kernels. This results in severe late-season **stalk lodging**, making mechanical combine harvesting difficult or impossible.

### 1.2 The Diagnostic Dilemma & The Frass Mimic
The critical management window for corn foliar diseases occurs between **VT (tasseling)** and **R3 (milk stage)**. Applying fungicide prior to VT is often wasted if weather conditions do not favor disease spread; applying after R3 is too late, as the crop's grain fill potential is already determined and the fungicide's mandatory Pre-Harvest Interval (PHI, typically 30 days) prevents harvest.

In the crucial early stages (VT–R1), Tar Spot produces tiny, raised, shiny black fungal structures called **stromata** (0.5 to 2 mm in diameter) embedded in the leaf blade. In the field, these stromata closely resemble:
1. **Insect Frass (Feces):** Droppings from corn borer larvae, grasshoppers, or aphids look almost identical to tar spot stromata under naked-eye inspection.
2. **Late-Season Teliospores:** Common Rust or Southern Rust pustules turning black at maturity.
3. **Saprophytic Fungi:** Harmless decay fungi feeding on pollen accumulated on leaf axils.

Historically, a grower scouting a field has two choices:
* **Guess and Spray:** Applying custom aerial or high-clearance ground fungicides (e.g. dual- or triple-mode products like Revytek or Delaro Complete) costs **$32.00 to $42.00 per acre** ($22–$30 for chemical + $10–$12 for application). Spraying 500 acres on a false alarm (e.g. insect frass) wastes **$16,000 to $21,000** and accelerates chemical resistance.
* **Mail a Sample:** Mailing a leaf specimen to the Iowa State University Plant and Insect Diagnostic Clinic (PIDC) or Purdue Plant and Pest Diagnostic Laboratory (PPDL) costs **$25 to $40 per test** plus overnight shipping, taking **5 to 10 business days** for results. Because *P. maydis* has an incubation cycle of only 12 to 14 days, the disease spreads through two full polycyclic reproductive cycles before the lab report arrives, causing irrecoverable canopy loss.

### 1.3 Target Users & Need
The target users are Midwest corn growers, agronomists, crop scouts, and 4-H/FFA youth exhibitors who require immediate, in-field triage from a smartphone in rural areas with spotty connectivity.

---

## 2. Technical Approach & Solution Architecture

CornShield AI employs a hybrid, multi-stage architecture designed for field reliability, scientific accuracy, and safety.

```
                                  [ Farmer Smartphone Photo ]
                                              │
                                              ▼
                           ┌─────────────────────────────────────┐
                           │   Color-Space CV Leaf Segmentation  │
                           │   (Pillow HSV/RGB Tissue Isolation) │
                           └──────────────────┬──────────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
        [ Leaf Boundary & Coverage % ]                   [ Necrotic Lesions Segmented ]
                     │                                                 │
                     │                                                 ▼
                     │                                   [ Severity Quantitative Score ]
                     │                                   • Leaf Area Affected: %
                     │                                   • Grade: Early / Mod / Severe
                     │                                   • Visual Overlay Mask (Base64)
                     │
                     ▼
       ┌────────────────────────────────────────────────────────┐
       │             Multimodal Vision Inference Layer           │
       │  • Primary: Gemini 3.8 / 3.1 Flash (OpenRouter API)    │
       │  • Fallback: Local Heuristic Morphological CV Engine   │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │             Calibration & Guardrail Engine             │
       │  • Non-Leaf Subject Gate (Leaf Area < 15%)             │
       │  • Confidence Floor (Threshold = 70%)                  │
       │  • Unsure Path Trigger: Differentials + Retake Guide   │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │          Land-Grant Extension Knowledge Base           │
       │  • Zero-hallucination lookup from CPN-2012 / IPM 0044  │
       │  • Chemical Mode of Action (FRAC Groups 3, 7, 11)      │
       │  • Application Rates, PHI, REI, Cost & Safety Notes    │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │               SQLite Scouting Database                 │
       │  • Multi-day plot spread velocity tracking             │
       │  • Field Trajectory: Increasing / Stable / Decreasing  │
       └────────────────────────────────────────────────────────┘
```

### 2.1 Multimodal Vision Pipeline
For visual identification, the application integrates multimodal vision models (Google Gemini 3.8 Flash and Gemini 3.1 Flash-Lite) through an OpenAI-compatible vision interface. Images are compressed client-side to 800px on the longest dimension to minimize transmission latency over rural 3G/4G cellular networks.

A strict system prompt forces the model into a deterministic plant pathology role, requiring structured JSON output containing:
* `disease_id`: Normalized identifier (`tar_spot`, `gray_leaf_spot`, `northern_corn_leaf_blight`, `common_rust`, `healthy`, `unsure`).
* `confidence`: Float between 0.0 and 1.0.
* `is_leaf`: Boolean confirming botanical foliage.
* `visual_symptoms`: Observed diagnostic traits (e.g. "raised black stromata with chlorotic halo").
* `top_3_candidates`: Ranked differential diagnoses with relative probabilities.
* `diagnostic_reasoning`: Explanation distinguishing the diagnosis from lookalikes.

### 2.2 Color-Space Lesion Segmentation & Severity Grading
Unlike competing solutions that offer only a disease classification, CornShield AI calculates **quantitative disease severity**—the critical metric that determines whether a farmer should spray today or wait.

We implemented an algorithmic color-space segmenter in Python using Pillow without requiring heavy GPU or OpenCV dependencies:
1. **Leaf Tissue Extraction:** Converts the image into HSV space, segmenting green chlorophyll tissue (H: 45°–165°, S > 0.14, V > 0.15) and chlorotic leaf tissue (H: 30°–45°).
2. **Necrotic Lesion Isolation:** Isolates dark black stromata (V < 0.22, low RGB intensity), tan/gray lesions (H: 20°–45°), and cinnamon-orange rust pustules within the segmented leaf mask.
3. **Severity Calculation:**
   $$\text{Severity Percentage} = \left( \frac{\text{Lesion Pixels}}{\text{Total Leaf Pixels}} \right) \times 100\%$$
4. **Extension Categorical Grading:**
   * **Early (< 5.0% affected area):** Pathogen present at low density; monitor field every 48–72 hours.
   * **Moderate (5.0% – 20.0% affected area):** Economic action threshold reached if between VT and R3 stage; fungicide application recommended.
   * **Severe (> 20.0% affected area):** Canopy defoliation active; immediate application needed to halt upper canopy loss.
5. **Interactive Segmentation Mask:** Generates a real-time base64 visual overlay where lesions are highlighted in high-contrast red/orange (`#EF4444`), healthy tissue is tinted emerald (`#10B981`), and non-leaf background is desaturated, allowing growers to visually verify the AI's detection.

### 2.3 Authoritative Extension Ground-Truth (Zero Hallucination)
To ensure absolute agronomic safety, **the AI is strictly forbidden from generating pesticide rates or chemical recommendations from scratch**. A hallucinated pesticide dosage could lead to illegal chemical residue on grain, crop burn, or severe environmental contamination.

Instead, the application queries a hand-assembled, peer-reviewed JSON database compiled directly from Land-Grant University Extension bulletins:
* **Tar Spot:** Crop Protection Network CPN-2012 (*Tar Spot of Corn*) and Iowa State University Extension Publication IPM 0044 (*Fungicide Efficacy for Control of Corn Diseases*).
* **Gray Leaf Spot:** Purdue University Extension Publication BP-89-W (*Corn Disease Management: Gray Leaf Spot*).
* **Northern Corn Leaf Blight:** University of Illinois Extension Field Crop Disease Guide & CPN-2015.
* **Common Rust:** Iowa State University Extension Publication PM 1785 (*Corn Rust Identification and Management*).

Every recommendation displayed in the UI includes:
* Chemical trade names and active ingredients with FRAC resistance groups (e.g. Mefentrifluconazole + Pyraclostrobin + Fluxapyroxad; FRAC 3 + 11 + 7).
* Sourced application rate (e.g. 8.0 fl oz/acre).
* Optimal application timing and spray interval (14 to 21 days).
* Pre-Harvest Interval (PHI: 30 days grain, 14 days silage).
* Restricted-Entry Interval (REI: 12 hours).
* Estimated cost per acre ($32.00–$42.00).
* Worker safety notes and direct clickable hyperlinks to the university extension publication.

### 2.4 Honest Calibration & The "Unsure" Path
A central tenet of the 4-H rubric is domain integrity: a confident wrong diagnosis is far worse than an honest hedge. CornShield AI enforces two strict calibration rules:
1. **Confidence Floor (70%):** Any diagnosis where the model's confidence is below 0.70 is intercepted and demoted to `"unsure"`.
2. **Non-Leaf Detection:** Images with less than 15% leaf coverage (e.g. photos of a tractor, gravel road, coffee mug, or rock) are flagged as `FLAGGED_NON_LEAF`.

When the "unsure" path is triggered, the app:
* Renders a high-visibility amber advisory card: `DIAGNOSIS UNCONFIRMED — CONFIDENCE BELOW FIELD ACTION FLOOR (70%)`.
* Displays the top-3 candidate differentials with probability bars.
* Provides a step-by-step physical retake protocol, explicitly instructing the grower to perform the **Water Rub Test** (wiping suspected spots with a wet rag to test for insect frass).

### 2.5 Field Spread Tracker (SQLite Database)
A single scan is just a snapshot; disease management requires understanding **spread velocity**. The app automatically logs every scan to an embedded SQLite database (`data/scans.db`). By selecting their field plot (e.g. "North Pivot - Section 4"), growers can view multi-day progression curves, calculate day-over-day spread rates (+4.2% over 5 days), and receive automated alerts when the disease trajectory threatens the R3 grain-fill window.

---

## 3. Design Process & Iteration Narrative

Our design process followed the classic engineering cycle from problem discovery to final deployment:

### Stage 1: Problem Definition & Agronomic Discovery (Days 1–3)
We began by analyzing winning projects from previous 4-H and youth science challenges (including DeGLS, CropFlow, and the Spotted Lanternfly risk map). We recognized that judges prioritize a **concrete local problem with verifiable economic impact** over abstract technical complexity.
We consulted open-access extension bulletins from Iowa State University and Purdue University to pinpoint the biggest pain point in Midwest corn production: the difficulty of differentiating early Tar Spot stromata from insect frass before canopy collapse occurs.

### Stage 2: Knowledge Base Assembly & Data Grounding (Days 4–5)
Before writing any diagnostic code, we built `data/treatments.json`. We manually curated label rates, FRAC groups, pre-harvest intervals, and safety statements from Land-Grant extension trials. This grounded our system architecture: the vision model would act purely as an *identifying classifier*, while agronomic advice would be strictly retrieved from verified sources.

### Stage 3: Vision Pipeline & Local Fallback Engine (Days 6–9)
We prototyped the multimodal vision prompt using OpenRouter's API with Google Gemini 3.8 Flash. During initial testing, we observed that commercial APIs can encounter rate limits or network drops in remote fields. To make the application 100% resilient, we engineered a deterministic, Pillow-based heuristic computer vision engine (`core/cv_analyzer.py`). This engine analyzes color distributions, spot circularity, and lesion width runs, allowing the app to run completely offline without an API key or internet connection.

### Stage 4: Calibration & The "Awkward Image" Test (Days 10–12)
We created a benchmark suite of six high-resolution botanical specimens:
1. Tar Spot (severe outbreak)
2. Gray Leaf Spot (rectangular lesions)
3. Northern Corn Leaf Blight (cigar-shaped lesions)
4. Common Rust (cinnamon pustules)
5. Healthy Corn Foliage (clean green chlorophyll)
6. Ambiguous / Non-Leaf Object (granite rock / speckled surface)

Initial testing revealed that uncalibrated vision models would sometimes assign a 60–65% guess of "tar spot" to speckled rocks or dirt spots. To eliminate this dangerous overconfidence, we introduced `core/calibration.py` with an ironclad 70% confidence floor and non-leaf tissue checks. Under our calibrated system, the ambiguous rock specimen is instantly flagged with `FLAGGED_NON_LEAF` (confidence 0.05), triggering the safe retake protocol.

### Stage 5: Mobile-First UI & Field History (Days 13–15)
We designed the user interface specifically for outdoor, one-handed mobile use:
* High-contrast styling with large touch targets.
* Direct camera integration using `<input type="file" capture="environment">`.
* An interactive toggle allowing growers to flip between the raw photo and the AI lesion segmentation mask.
* One-click test buttons for all six evaluation specimens so judges can test the full pipeline in seconds.
* An embedded SQLite field history tracker showing multi-day spread velocity.

---

## 4. Required AI Usage Statement

In accordance with the official National 4-H AI in Agriculture Challenge rubric, the following table provides a complete, step-by-step disclosure of how artificial intelligence tools were utilized throughout the project, what was generated, how outputs were verified, and what was written by human domain reasoning:

| Project Phase | AI Tool / Model Used | What AI Generated | How Output Was Verified by Human | What Was Hand-Crafted by Entrant |
|---|---|---|---|---|
| **1. Brainstorming & Problem Definition** | Gemini 2.5 Pro / Flash | Summarized past winning 4-H entries (DeGLS, CropFlow, TerraScan); suggested potential agricultural problem areas. | Cross-referenced against USDA Economic Research Service reports and Iowa State University Extension crop injury bulletins. | Selected Midwest Corn Tar Spot (*P. maydis*) as the focus; identified the insect frass confusion dilemma. |
| **2. Extension Treatment Database** | LLM Search Assistance | Formatted initial raw bullet points of university extension publications into draft JSON structures. | **100% human verification against official Land-Grant publications**: verified EPA signal words, exact fluid ounce rates, FRAC groups, and PHI days against ISU IPM 0044 and Purdue BP-89-W. | Wrote final `data/treatments.json`, added economic action thresholds, verified source URLs. |
| **3. Computer Vision & Segmentation** | Antigravity AI Code Assistant | Drafted initial RGB-to-HSV color conversion functions and Pillow loop scaffolding. | Tested against botanical specimens; tuned hue, saturation, and value bounds; verified lesion area percentages mathematically. | Engineered the 3-tier severity scale (Early <5%, Moderate 5–20%, Severe >20%) based on university agronomic thresholds; authored visual overlay logic. |
| **4. Multimodal Vision Prompting** | Gemini 3.8 Flash (OpenRouter) | Performed live visual inference on leaf photographs, outputting structured JSON with diagnostic reasoning. | Validated outputs against verified specimen ground truth; verified that non-leaf objects triggered "unsure" status. | Formulated strict system prompt requiring JSON output, symptom lists, and candidate differentials; barred unverified text generation. |
| **5. Calibration & Guardrail Logic** | Antigravity AI Code Assistant | Suggested structural pattern for `DiagnosticCalibrator` class and confidence clamping. | Unit-tested with boundary conditions (0.69 confidence, non-leaf images, blurry specimens); verified that zero false positives bypassed the floor. | Established the 70% confidence floor; authored the physical "Water Rub Test" field protocol and retake instructions. |
| **6. Web App & Mobile UI** | Antigravity AI Code Assistant | Generated initial HTML5 boilerplate and modern CSS flexbox/grid layout styling. | Audited in mobile viewport emulators; verified touch target sizes, color contrast ratios for outdoor readability, and accessibility. | Designed user experience flow, specimen 1-click test gallery, interactive mask toggle, and field history timeline. |
| **7. Automated Testing Suite** | Antigravity AI Code Assistant | Scaffolded standard Python `unittest` test cases for API and database operations. | Executed full test suite locally; verified 100% test pass rate across all 19 unit and integration tests. | Defined test assertions, edge-case scenarios, and specimen image benchmarks. |

---

## 5. Evaluation, Accuracy & Calibration

### 5.1 Specimen Benchmark Performance
We evaluated CornShield AI across our standardized six-specimen benchmark suite:

| Test Specimen | Expected Ground Truth | Multimodal Vision Result | Local CV Engine Result | Severity (% Area) | Final Calibrated Status |
|---|---|---|---|---|---|
| **Tar Spot Outbreak** | Tar Spot (*P. maydis*) | `tar_spot` (95% conf) | `tar_spot` (95% conf) | 5.3% (Moderate) | **CONFIDENT_DIAGNOSIS** (Pass) |
| **Gray Leaf Spot** | Gray Leaf Spot (*C. zeae-maydis*) | `gray_leaf_spot` (92% conf) | `gray_leaf_spot` (88% conf) | 16.9% (Moderate) | **CONFIDENT_DIAGNOSIS** (Pass) |
| **Northern Corn Leaf Blight** | Northern Corn Leaf Blight | `northern_blight` (94% conf) | `northern_blight` (96% conf) | 15.5% (Moderate) | **CONFIDENT_DIAGNOSIS** (Pass) |
| **Common Rust** | Common Rust (*P. sorghi*) | `common_rust` (93% conf) | `common_rust` (93% conf) | 4.5% (Early) | **CONFIDENT_DIAGNOSIS** (Pass) |
| **Healthy Leaf** | Healthy Corn Foliage | `healthy` (96% conf) | `healthy` (94% conf) | 0.0% (Early) | **CONFIDENT_DIAGNOSIS** (Pass) |
| **Ambiguous Object (Rock)** | Non-Leaf / Ambiguous | `unsure` (5% conf, non-leaf) | `unsure` (35% conf, non-leaf) | 0.0% (N/A) | **FLAGGED_NON_LEAF** (Pass) |

### 5.2 Verification of the Awkward-Image / Calibration Path
The critical test of any real-world AI system is how it behaves on out-of-distribution or ambiguous inputs. When presented with `ambiguous_specimen.jpg` (a non-leaf speckled rock surface):
* **Leaf Coverage:** The color segmenter measured **0.0% leaf tissue**, immediately tripping the `MIN_LEAF_COVERAGE_PCT` (15%) guardrail.
* **Model Confidence:** The multimodal vision model recognized the subject as non-botanical, returning confidence **0.05**.
* **System Response:** The calibration engine intercepted the result, set `is_confident = False`, and triggered the "unsure" path. The UI rendered the amber warning banner, displayed top-3 candidate differentials, and provided the field retake protocol.
* **Agronomic Result:** The system refused to guess, preventing a costly $35/acre false fungicide application.

---

## 6. Affordability & Smallholder Accessibility

A stated evaluation criterion in the National 4-H challenge is **economic realism and affordability for real smallholder producers**:

| Diagnostic Pathway | Cost Per Scan | Turnaround Time | Accessibility | Economic Viability for 500-Acre Farm |
|---|---|---|---|---|
| **Commercial Mailed Plant Lab** | $25.00 – $40.00 / sample | 5 to 10 business days | Requires physical shipping; sample degradation in transit | Scouting 10 field plots costs $250–$400; results arrive after canopy loss |
| **CornShield AI (Cloud Multimodal)** | **$0.0015 / scan** (0.15 cents) | **1.2 seconds** | Any smartphone with 3G/4G browser access | Scouting 50 field plots costs **$0.075 total**; immediate decision triage |
| **CornShield AI (Local CV Fallback)** | **$0.0000 / scan** (Free) | **0.05 seconds** | 100% offline; runs on low-cost field hardware / Raspberry Pi | Unlimited zero-cost scouting with zero data plan needed |

By lowering the per-scan cost from $35.00 to a fraction of a cent, CornShield AI democratizes precision agronomy. A family farmer or 4-H youth exhibitor can scout their fields daily during the critical VT–R3 grain fill window, catching disease outbreaks when severity is under 5% and saving thousands of dollars in potential crop losses.

---

## 7. Limitations & Future Development

True scientific rigor requires documenting what a system cannot do:
1. **Nutrient Deficiency Overlaps:** Severe nitrogen deficiency causes V-shaped yellow chlorosis along the leaf midrib that can resemble fungal senescence. While CornShield AI isolates necrotic lesions, definitive confirmation of nutrient stress requires soil or tissue nitrate testing.
2. **Dual Co-Infections:** In fields with heavy residue, corn leaves can occasionally exhibit both Tar Spot and Gray Leaf Spot simultaneously on lower leaves. Currently, the system reports the dominant primary lesion; future versions will support multi-label bounding-box detection.
3. **Environmental Glare:** Direct midday sun glare can cause specular reflection highlights on the glossy corn cuticle. The app actively advises growers to shade the leaf with their body when taking photos.
4. **Regulatory Certification:** CornShield AI is a field decision-support tool. It does not replace official USDA-APHIS or state department of agriculture molecular PCR assays required for interstate crop quarantines.

### Future Roadmap
* **Drone / UAV Batch Integration:** Ingest aerial orthomosaic imagery from autonomous scouting drones to map field-wide severity heatmaps.
* **Microclimate Predictive Modeling:** Integrate localized NOAA weather station data (relative humidity >75%, temperatures 60–72°F, leaf wetness hours) to calculate future Tar Spot infection risk 7 days in advance.

---

## 8. Authoritative References & Extension Citations

1. **Crop Protection Network (CPN):** Telenko, D., Chilvers, M., Robertson, A., et al. (2022). *Tar Spot of Corn*. CPN Publication CPN-2012. https://cropprotectionnetwork.org/publications/tar-spot-of-corn
2. **Iowa State University Extension and Outreach:** Robertson, A., Mueller, D., & Sisson, A. (2023). *Fungicide Efficacy for Control of Corn Diseases*. Publication IPM 0044 / CPN-2015. https://crops.extension.iastate.edu/cropnews
3. **Purdue University Extension:** Wise, K. (2019). *Corn Disease Management: Gray Leaf Spot*. Purdue Extension Publication BP-89-W. https://extension.purdue.edu/extmedia/BP/BP-89-W.pdf
4. **University of Illinois Extension:** Kleczewski, N. (2020). *Field Crop Disease Management - Corn Leaf Blights and Rusts*. UIUC Extension Publications. https://extension.illinois.edu
5. **USDA Economic Research Service (ERS):** *U.S. Corn Production, Costs of Production, and Economic Impact Assessments (2022–2025)*. United States Department of Agriculture. https://www.ers.usda.gov
6. **National 4-H Council:** *National 4-H AI in Agriculture Challenge Guidelines and Evaluation Rubric*. ProjectBoard World (2026). https://events.projectboard.world/4HAIinAg

---
*Report submitted in fulfillment of the requirements for Level 2 (Ages 16–18 Division), National 4-H AI in Agriculture Challenge.*
