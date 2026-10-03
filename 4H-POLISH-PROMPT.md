# POLISH BRIEF — CornShield AI (National 4-H AI in Agriculture Challenge, Fall 2026)

**Repo:** `github.com/ronisaguey-ux/4-H-hackathon` @ `265ee0f`
**For:** the building agent. **Target:** close the defects an independent review found, then submit.

Read §1 first — it is what an independent reviewer actually measured, not what the repo claims.

---

## 0. REVIEW VERDICT

**The build is real and the hard parts work.** A fresh clone was installed and driven by an
independent harness:

- 33 files, correct structure, one-command `./run.sh`, 19/19 tests **pass**. ✓
- **The tests are real, not vacuous** — with `CONFIDENCE_FLOOR` and `MIN_LEAF_COVERAGE_PCT` both set
  to `0.0`, the suite **fails 3 tests**. A suite that cannot fail measures nothing; this one can. ✓
- **The "unsure" path genuinely works.** The `ambiguous` specimen returns
  `calibration_status=FLAGGED_NON_LEAF`, `confidence=0.05`, `pathogen=Indeterminate`, empty
  `retake_instructions`-filled protocol, and ranked candidates — it refuses to guess. ✓
- **The offline engine works and is reachable** (`local_cv_engine`): 4 of 5 disease specimens
  correct, and it correctly hedges the non-leaf. ✓
- **Zero secrets in the entire git history**; `.gitignore` is correct. ✓
- Severity %, cited extension treatments, and field history — the differentiators named in the
  original brief — are all present and wired. ✓

**But there are five defects, and the two HIGH ones would be found by a judge.**

---

## 1. DEFECTS, RANKED — this is the work list

### D1 — **[HIGH] The app silently reads OTHER PROJECTS' secrets, and is therefore not portable**

`config.py:41-46`, inside `_find_api_key`:

```python
    candidate_envs = [
        Path("/home/roni/Roni_workspace/helpotron/.env"),
        Path("/home/roni/Roni_workspace/t2b/.env"),
    ]
```

This was **measured, not inferred**: with no `OPENROUTER_API_KEY` in the environment and no `.env` in
the clone, the app still took the cloud path (`inference_engine: cloud_vision_google/gemini-3.8-flash`)
because it found a key inside `helpotron/.env`. Two consequences:

1. **It reads another project's credentials without being asked to.** A judge who inspects the code
   sees a hardcoded path into a private workspace.
2. **The result is not reproducible on any other machine.** Whether a diagnosis runs on the cloud
   model or the local engine depends on whether unrelated projects happen to be on disk. The same
   photo can produce different answers on two machines — which undermines the whole "100 %
   offline" claim and any benchmark in the report.

**Fix:** delete the `candidate_envs` block entirely. Resolution order should be exactly what
`.env.example` documents: (1) the real environment variable, (2) a `.env` in the project root.
Nothing else. If a key is absent, run the local engine — that is the documented and honest path.
Then **re-measure and report every number in `PROJECT_REPORT.md` under the no-key path**, because
that is the path a judge will actually run.

### D2 — **[HIGH] A confident WRONG diagnosis — the exact failure the brief said is worst**

Measured on the repo's **own** `gray_leaf_spot_specimen.jpg`, through the offline engine:

```
gray_leaf_spot_specimen.jpg -> northern_corn_leaf_blight   conf=0.96
```

**0.96 confidence on the wrong disease.** The 70 % floor guards *confidence*, not *correctness* —
so the guardrail cannot catch this, and the UI will present northern leaf blight with high certainty
to a grower. This is more damaging than an "unsure", because it is actionable and wrong.

If the cloud path is also wrong on this specimen (it returned below-floor, i.e. a hedge), then the
offline engine is the weaker one and it is the one a judge without keys will see.

**Fix, in order of preference:**
1. **Separate the confusable pair explicitly.** Gray leaf spot (rectangular, vein-bounded, gray-tan)
   and northern leaf blight (long elliptical, cigar-shaped, tan) are the classic confusion. Add a
   discriminator for lesion **shape and orientation** (aspect ratio and alignment to the leaf veins),
   not just colour. `cv_analyzer.py` already computes a lesion mask — use its geometry.
2. If the pair still cannot be separated reliably, **cap confidence when the top-2 candidates are
   both in the confusable set** (e.g. force the hedge path when the margin between them is small).
   An honest "these two, here is how to tell them apart in the field" is a *stronger* submission than
   a confident error.
3. Whatever you do, **the specimen must be named in the test** (§D4) so this cannot regress silently.

### D3 — **[MED] On the cloud path, 3 of 5 disease specimens return "Unsure" (0.5)**

Measured with a key present: `tar_spot` → Tar Spot 0.95 ✓ and `healthy` → Healthy 0.94 ✓, but
`gray_leaf_spot`, `common_rust` and `northern_blight` all return **Unsure, confidence 0.50**.
The measured behaviour is therefore **2 of 5 confirmed** on the keyed path.

This matters for the video: if it shows three hedge screens in a row, a judge reads "it does not
work" rather than "it is calibrated". Decide deliberately:

- Either **raise the field-action floor's usefulness** — a hedge that names the top-2 candidates with
  probabilities *and* the discriminator is a good screen, so lean into it and show it proudly; or
- **Improve recall on those three** (image quality/flash/background is likely the cause — the
  specimens are 640×480 stock photos), by preprocessing (white balance, background masking) before
  classification.

**Do not lower the 70 % floor to make the demo look better.** The floor is the honest part of this
entry.

### D4 — **[MED] The test suite never checks that the RIGHT disease is returned**

19 tests pass while D2 exists, because the tests assert the *mechanics* (floor enforced, non-leaf
gated, DB row written) and never assert a **per-specimen expected diagnosis**. So the suite cannot
catch the one bug that matters most.

**Fix — add a truth-table test, one row per specimen:**

```python
# tests/test_specimen_accuracy.py
# Each specimen has an expected diagnosis and a tolerance.
CASES = [
    ("tar_spot_specimen",        "tar_spot",  "confident"),
    ("common_rust_specimen",     "common_rust", "confident"),
    ("northern_blight_specimen", "northern_corn_leaf_blight", "confident"),
    ("healthy_leaf_specimen",    "healthy",   "confident"),
    ("gray_leaf_spot_specimen",  "gray_leaf_spot", "confident_or_hedge"),  # see D2
    ("ambiguous_specimen",       "unsure",    "must_hedge"),
]
```

Run it **in the offline engine** (that is the reproducible path, D1). **The test must fail today on
the gray-leaf-spot row** — that is how you know it is a real test. Then either fix the classifier
until it passes, or move that row to `confident_or_hedge` **and say in the report why**, with the
measured margin. Never silently widen a tolerance to make a test green.

Also add a **non-vacuity check** to the suite: assert that the confidence floor test fails when the
floor is set to 0.0. (This review proved it does; lock that in.)

### D5 — **[LOW] The engine label can be wrong**

`inference_engine` reported `cloud_vision_google/gemini-3.8-flash` on a run whose key came from the
scraped path (D1). After D1 this resolves itself, but **make the label tell the truth about where an
answer came from** — a judge reading `local_cv_engine` versus `cloud_vision_*` must be able to trust
it, because the report's benchmark table will cite it.

---

## 2. THE SUBMISSION — WHAT IS LEFT

The code is close. The submission is where this is won or lost, and the rubric weights the report and
the AI-usage statement heavily.

- [ ] **`PROJECT_REPORT.md`** — re-run every number after D1 and D2 change behaviour. **No figure in
      the report may come from a run with a scraped key.** State the engine used for each benchmark.
- [ ] **The AI-usage statement** — be specific and honest: which parts a model wrote, which parts were
      hand-written, and **how each model output was verified**. Naming that an independent review
      caught two defects and they were fixed is a strength, not a weakness; it demonstrates exactly
      the process narrative the rubric asks for.
- [ ] **The limitations section** — keep and extend it. Name D2's confusion pair as a known limitation
      with the field discriminator. A judge rewards named limits.
- [ ] **The video** — record the **offline** app (no key), because that is what a judge can reproduce.
      Show: a real leaf → a confident diagnosis with severity; the ambiguous rock → the honest hedge
      with the retake protocol; and the confusable pair → the field discriminator. Three screens, and
      the middle one is the one that wins.
- [ ] **The citation check** — every treatment in `treatments.json` must trace to a real extension
      publication that resolves. Print the citation in the UI where the treatment is shown.
- [ ] **Portal submission** — confirm the exact closing time for **2026-11-15** on
      `events.projectboard.world/4HAIinAg`, and submit in **Level 2 (16–18)**.
- [ ] **One-command run from a clean clone on a machine with no keys** — the final check. If it prints
      anything about a missing key or falls back unexpectedly, D1 is not finished.

---

## 3. DEFINITION OF DONE

1. `config.py` resolves keys **only** from the environment and a project-local `.env`; no absolute
   path into another project exists anywhere in the repo.
2. `tests/test_specimen_accuracy.py` exists, runs offline, and **its gray-leaf-spot row was seen to
   FAIL before it was made to pass** (or was moved to the hedge expectation with the measured margin
   recorded in the report).
3. The suite asserts non-vacuity: with the floor at 0.0 the relevant tests fail.
4. `gray_leaf_spot_specimen.jpg` no longer returns a **confident wrong** diagnosis. It returns either
   the right disease, or an honest hedge that names the two candidates and how to tell them apart.
5. Every number in `PROJECT_REPORT.md` is re-measured under the no-key path and the engine is named
   for each.
6. The video shows the live offline app diagnosing a real leaf **and** hedging on the ambiguous object.
7. Submitted on the portal before the deadline, Level 2.

**Report back with:** the commit, the new test's output (including the gray-leaf-spot row), the
before/after for D2's confidence, and confirmation that a clean clone on a machine with no keys runs
the offline engine. **An accurate "this specimen cannot be separated reliably, here is how I handle
it" is worth more than a tuned score.**
