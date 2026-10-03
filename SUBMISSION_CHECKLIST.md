# SUBMISSION VERIFICATION CHECKLIST — National 4-H AI in Ag Challenge

**Project:** CornShield AI — Midwest Corn Foliar Disease Early-Detection & Severity Engine  
**Division:** Level 2 (Ages 16–18 Division)  
**Target Deadline:** 2026-11-15  
**Submission Portal:** https://events.projectboard.world/4HAIinAg  

---

## Section 4: What Wins, Concretely (Checklist Audit)

- [x] **A named, local, sourced problem — not a global generality:**
  - *Addressed:* Tar Spot (*Phyllachora maydis*) and Gray Leaf Spot (*Cercospora zeae-maydis*) in Iowa and the Midwest Corn Belt.
  - *Sourced citations:* Crop Protection Network (CPN-2012), Iowa State University Extension Publication IPM 0044, Purdue University Extension Publication BP-89-W, USDA ERS. Documented 50–60 bu/acre yield loss and $1.5B+ regional loss.
- [x] **A live, working diagnosis from a photograph, demonstrated on camera:**
  - *Addressed:* Full working Flask app (`app.py`), mobile-first frontend (`templates/index.html`, `static/js/app.js`), supports camera capture, image upload, and 1-click test gallery.
- [x] **Severity, because nearly every competing entry skips it:**
  - *Addressed:* Pillow color-space lesion segmentation calculates quantitative leaf area affected percentage (`severity_pct`) and maps to Extension economic thresholds (`Early < 5%`, `Moderate 5–20%`, `Severe > 20%`), complete with interactive visual overlay mask (`#resultImageMask`).
- [x] **Treatment with a citation, because it shows domain care:**
  - *Addressed:* Zero-hallucination hand-assembled `data/treatments.json` quoting Land-Grant University Extension bulletins with active ingredients, FRAC groups, application rates, spray intervals, pre-harvest intervals (PHI), re-entry intervals (REI), and direct clickable links.
- [x] **An explicit "unsure" path — hedged honestly:**
  - *Addressed:* `core/calibration.py` enforces a 70% confidence floor and non-leaf detector. Out-of-distribution inputs (such as `ambiguous_specimen.jpg`) produce the amber unconfirmed warning banner, top-3 differential breakdown, and the physical "Water Rub Test" field protocol.
- [x] **A limitations section that names what the tool cannot do:**
  - *Addressed:* Prominently featured in the UI and Section 7 of `PROJECT_REPORT.md`: nutritional deficiency overlaps (Nitrogen V-yellowing), dual infections, wet cuticle glare, and regulatory USDA-APHIS quarantine boundaries.
- [x] **A required AI-usage statement that is specific and honest:**
  - *Addressed:* Detailed in Section 4 of `PROJECT_REPORT.md` breaking down brainstorming, database curation, CV segmentation, vision prompt engineering, calibration, web UI, and automated test suite.
- [x] **An affordability sentence: what it costs to run per scan, and why a smallholder could use it:**
  - *Addressed:* Documented in UI, Report (§6), and Video Script: **$0.0015 per scan** (0.15 cents) on Gemini Flash multimodal vision or **$0.00** offline with the local CV engine, compared to $25–$40 for mailed clinic samples.

---

## Section 5: Anti-Penalty Safeguards

- [x] **No Mockup:** A 100% working Python/Flask application with full computer vision and multimodal vision backends.
- [x] **No Invented Treatments:** Treatments are strictly pulled from verified Land-Grant extension tables; the AI is barred from inventing pesticide dosages.
- [x] **No Confident Wrong Diagnoses:** Calibrated 70% confidence floor and non-leaf detector prevent hallucinated guesses.
- [x] **No Generic Problem:** Grounded in Iowa/Midwest corn, Tar Spot, and specific bushel-per-acre losses.
- [x] **Complete AI Statement:** Detailed stage-by-stage disclosure included in project report.
- [x] **Zero Secrets in Git History:** `.gitignore` strictly ignores `.env`, `*.env`, `data/scans.db`, `uploads/`, and temporary build artifacts. No secrets committed.
- [x] **Correct Division:** Level 2 (Ages 16–18 Division).

---

## Section 6: Definition of Done

1. [x] **Public repository exists with a one-command run and zero secrets in history.**
   - Script: `./run.sh`
   - Git remote: `https://github.com/ronisaguey-ux/4-H-hackathon.git`
2. [x] **The app diagnoses a real leaf photograph end-to-end and displays disease + confidence + severity + cited treatment.**
   - Verified across Tar Spot, Gray Leaf Spot, Northern Corn Leaf Blight, Common Rust, and Healthy corn leaves.
3. [x] **A deliberately ambiguous or non-leaf image produces the 'unsure' path, not a confident guess.**
   - Verified with `ambiguous_specimen.jpg`: produces `FLAGGED_NON_LEAF`, confidence 0.05 / 0.35, triggers amber warning and retake guide.
4. [x] **Treatment text in the app traces to a real extension publication, cited in the UI.**
   - Traced to Crop Protection Network CPN-2012, ISU Extension IPM 0044, Purdue BP-89-W.
5. [x] **The report contains the problem, the process narrative, and the AI-usage statement.**
   - Authored in `PROJECT_REPORT.md` (all 8 sections complete).
6. [x] **The video script demonstrates the live app diagnosing a real photo and awkward image.**
   - Authored in `VIDEO_SCRIPT.md` with timestamps and live UI cues.
7. [x] **Ready for portal submission before 2026-11-15 in Level 2.**
