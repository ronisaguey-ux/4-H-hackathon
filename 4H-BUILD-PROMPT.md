# BUILD BRIEF — National 4-H AI in Agriculture Challenge (Fall 2026)

**For:** the building agent. **From:** research already done. **Target:** a winning entry, not a demo.

Read this whole file before writing any code. Section 0 is what makes it win. Section 2 is the exact
submission. Section 6 is the definition of done.

---

## 0. THE ONE THING TO UNDERSTAND FIRST

**Four recent first- and second-place entries all had the same shape, and none of them was
technically hard:**

| place | entry | what it actually is |
|---|---|---|
| 1st (16–18 division) | **DeGLS** | photograph a corn leaf → AI names the disease, its severity, and the treatment |
| 1st (13–15 division) | TerraScan | a soil-mapping robot (genuinely hard — do not attempt) |
| 2nd (16–18 division) | CropFlow | soil + weather data → predicted yield and a recommendation |
| 2nd | Spotted Lanternfly risk map | a geographic risk-prediction map + a public website, **built with Claude** |

**The bar is: a specific, local problem; a working thing a real farmer or community can actually
use; and an honest writeup of the process.** It is explicitly *not* a research contribution and it
is *not* judged on technical sophistication.

Two consequences that decide the design:

1. **Build the leaf-diagnosis entry (the DeGLS shape), but better.** It won the 16–18 division, which
   is the division our entrant is in. It is a vision model plus a small web app. We already have a
   working vision pipeline from another project, so the hard engineering is already done.
2. **Farming the report matters as much as the code.** The rubric weights problem identification and
   the quality of the writeup, and it *requires a statement describing how AI was used at each step*.
   A brilliant app with a lazy writeup loses to a decent app with an excellent one.

**Do not build a robot. Do not build a research paper. Do not build a concept mockup — a mockup is
explicitly disqualifying.**

---

## 1. WHAT THE COMPETITION IS

- **Organiser:** National 4-H, extended by a Google AI grant. Co-administered through ProjectBoard.
- **Who can enter:** US youth **ages 13–18**, two divisions — **Level 1 (13–15)** and **Level 2
  (16–18)**, age taken as of the deadline (**2026-11-15**). **No 4-H membership requirement** —
  eligibility is age/grade-based and entry is free. Our entrant is in **Level 2**.
- **Individual or small team** (2–3 members is typical); several recent winners were solo.
- **Open:** 2026-10-01. **Deadline: 2026-11-15.** Winners announced during **Computer Science
  Education Week** (second week of December).
- **Prizes, per division:** 1st **$500** · 2nd **$400** · 3rd **$300**. The listing advertises
  winning "up to $1,000" in the national contest — confirm the current table on the portal.
- **Register / submit:** <https://events.projectboard.world/4HAIinAg>
  (details page: `/4HAIinAg/details`; past projects: `/4HAI`). **The official instructions, FAQ and
  **judging rubric** are downloadable from that site — pull them before building and follow the
  rubric exactly.**
- **Prompt:** *"How can AI help solve problems in agriculture?"* Suggested themes: crop yields and
  sustainability · automating farm operations · optimising supply chains.

### Judging
National-level 4-H reviewers. Documented criteria: **problem identification**, **the AI-based
solution**, and **the quality of the project report/submission**. A closely-related 4-H rubric lists
**innovation/originality, creativity, completeness of the solution, and AI integration**, and
requires a **written statement of the whole process — brainstorming through final design — and
exactly how AI was used at each step.**

**⇒ Assume the report is graded as heavily as the app. Build both.**

---

## 2. WHAT TO BUILD

**An AI crop-disease diagnosis service, usable from a phone in a field.**

### 2.1 The product (what a judge will actually do)
A farmer photographs a leaf. Within a few seconds the app returns:

1. **The likely disease** (name + a confidence figure), or an explicit *"not a recognised disease —
   here are the closest matches"* rather than a confident wrong answer.
2. **Severity** — a rough percentage of leaf area affected, and a plain-language grade
   (early / moderate / severe). This is what determines whether the farmer acts today or this week,
   and almost every competing entry will omit it.
3. **Treatment** — a recommended action with **cost and safety notes**, sourced from a real
   agricultural extension publication (cite it in the UI), not invented by the model.
4. **A short history** — previous scans for that field, so a farmer can see whether it is spreading.
   A cheap SQLite table; it makes the app feel like a tool rather than a demo.

**Do not let the model write the treatment from scratch.** A hallucinated pesticide dose is both
wrong and dangerous, and a judge who knows farming will catch it. Retrieve the treatment text from
a fixed, cited table (see §2.3) and have the model only *select* and *phrase* it.

### 2.2 The problem, stated locally (this is the "problem identification" score)
Pick **one crop, one region, and one disease** and lead the writeup with it. Do not write "crops
suffer from disease worldwide." Write, for example, that a specific disease costs growers in a
specific state a specific share of yield, and that diagnosis normally requires mailing a sample to a
lab and waiting days. **Verify that claim with a real extension-service or USDA source and cite it.**
A specific, sourced, local problem is the single cheapest way to raise this score.

### 2.3 The AI stack — keep it boring and real
- **Model:** a vision-language model for identification. Our existing vision pipeline is the starting
  point — reuse it rather than building new inference. If a hosted model is used, put the key in an
  environment variable and **never commit it**.
- **Treatment knowledge:** a small local JSON table — `{disease, treatment, rate, interval,
  preharvest_interval, source_url, source_title}` — assembled by hand from **university extension
  publications** (land-grant university extension services publish exactly this, free and citable).
  The model picks the row; the text is quoted from the source.
- **Calibration:** the model must be able to say *"unsure."* Add a confidence floor. Below it, return
  the top-3 candidates and instruct the user to send a photo from a different angle. **A wrong
  confident diagnosis is worse than an honest hedge**, and it is the easiest failure for a judge to
  find.
- **Segmentation (severity):** a rough affected-area estimate is enough. Do not train a segmentation
  model. A simple colour-threshold estimate on the leaf region is honest if the writeup says what it
  is and what it is not.

### 2.4 The app
- **One page, mobile-first.** Camera button → result card. It must work on a phone because the whole
  premise is "in a field."
- Include a **"how this works / what it can't do"** panel. Naming the limits is a credibility signal
  a judge will reward, and it costs nothing.
- Ship a **live demo URL if at all possible.** If it cannot be hosted, the setup instructions in the
  repo must let a judge run it in one command — *"a design mockup or non-functional demo does not
  meet the requirement"* is the explicit rule in the sibling ruleset.

---

## 3. THE SUBMISSION DELIVERABLES

The portal's own instructions and rubric are authoritative — download them and follow them exactly.
Based on the sibling 4-H format, expect to need all of:

1. **A project report** — problem, approach, design process (brainstorm → final), **and a step-by-step
   account of how AI was used at each step.** This last section is required; write it deliberately,
   not as an afterthought. It is also a chance to be honest and specific: say which parts the model
   did, which parts were hand-written, and how outputs were verified.
2. **A video, ~3–5 minutes** — the problem, a live demo (a real photo → a real diagnosis on screen),
   the limitations, and what you would do next. **Film the live app, not slides.** A working demo on
   camera is the strongest single artifact in this competition.
3. **The code repository**, public, with a README that runs in one command and **no secrets in it**.
4. **Any required registration fields** on the portal.

---

## 4. WHAT WINS, CONCRETELY (a checklist to hit)

- [ ] A **named, local, sourced** problem — not a global generality.
- [ ] A **live, working** diagnosis from a photograph, demonstrated on camera.
- [ ] **Severity**, because nearly every competing entry skips it.
- [ ] **Treatment with a citation**, because it shows domain care.
- [ ] An explicit **"unsure"** path — hedged honestly.
- [ ] A **limitations section** that names what the tool cannot do.
- [ ] A **required AI-usage statement** that is specific and honest.
- [ ] An **affordability** sentence: what it costs to run per scan, and why a smallholder could use it.
  (Recent winners were framed around realistic, affordable approaches — this is a stated criterion.)

---

## 5. THINGS THAT WILL COST THE ENTRY

- **A mockup instead of a working thing.** Explicitly disqualifying.
- **Invented treatment advice.** Dangerous, and a domain-aware judge will spot it. Quote the source.
- **A confident wrong diagnosis.** Hedge below the confidence floor.
- **A generic problem statement.** "Agriculture faces many challenges" scores nothing.
- **Skipping the AI-usage statement or the process narrative.** Both are required by the rubric.
- **Committing an API key.** The repo is public.
- **Missing the deadline: 2026-11-15.** Confirm the exact time on the portal — many portals close at
  a local midnight, and a late submission is simply not judged.
- **Entering the wrong division.** Age is taken as of the deadline; the entrant is in **Level 2
  (16–18)**.

---

## 6. DEFINITION OF DONE

The entry is complete when all of the following are **true and demonstrated**, not asserted:

1. A public repo exists with a one-command run and **zero secrets in its history**.
2. The app diagnoses a real leaf photograph end-to-end and displays disease + confidence + severity +
   a **cited** treatment.
3. A deliberately ambiguous or non-leaf image produces the **"unsure"** path, not a confident guess.
4. The treatment text in the app traces to a **real extension publication**, cited in the UI.
5. The report contains the problem, the process narrative, **and the AI-usage statement**.
6. The video shows the **live app** diagnosing a real photo.
7. Everything required has been submitted on the portal **before 2026-11-15**, in **Level 2**.

**Report back with:** the repo URL, the live demo URL (or the one-command run output), the portal
submission confirmation, and the answer to §6.3 — the awkward-image behaviour is the one judges
probe and it is the easiest to get wrong.
