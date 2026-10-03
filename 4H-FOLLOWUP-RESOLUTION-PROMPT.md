# CornShield follow-up — one measured defect before submission

Independent review of `4-H-hackathon` at `f293120`. Everything else checks out: 21/21 tests pass and
the truth-table test is genuinely non-vacuous (forcing the discriminator to always return gray leaf
spot makes it fail), the confidence floor and non-leaf gate work, treatments trace to real extension
publications, and the offline path runs with no key.

One real defect remains, and it is the kind that loses a placement because it produces a confident
wrong answer.

## The defect: the geometry discriminator is not scale-invariant

Reproduce it. For each specimen, resize the image and re-run the offline analyzer:

```
northern_blight_specimen.jpg   original    -> northern_corn_leaf_blight  0.96   OK
northern_blight_specimen.jpg   resized 50% -> gray_leaf_spot             0.96   WRONG
northern_blight_specimen.jpg   resized 25% -> gray_leaf_spot             0.96   WRONG
```

Every other perturbation was fine: brightness, contrast, rotation, JPEG compression, and resizing
the gray-leaf-spot specimen. Only this one flips, and it flips to the confusable pair's other member
at 0.96 confidence.

### Root cause

`core/cv_analyzer.py` classifies on run lengths measured in **absolute pixels**:

```
narrow_runs = [r for r in lesion_run_lengths if r <= 42]
if pct_narrow_runs >= 65.0 and avg_run_width <= 38.0:      # gray leaf spot
elif pct_narrow_runs <= 42.0 and avg_run_width >= 42.0:    # northern blight
```

`resize_for_analysis` only shrinks images larger than `max_dimension` (600 px); it never enlarges.
So a 300x200 image keeps its native scale and its lesions measure ~half as many pixels wide, which
pushes northern blight's broad runs under the 42 px cutoff and into the gray-leaf-spot branch.

Note the practical consequence, because it bounds urgency: a **real phone photo** is 3000-4000 px and
is downscaled to 600, which lands in the calibrated regime, so the live camera path is currently
fine. The defect bites *already-small* images — a downloaded test image, a crop, a downscaled upload,
a screenshot. That is exactly what a judge or a county agent will feed it, and it is why this is worth
fixing rather than noting.

## The fix

Make the classifier scale-invariant. Two options; the first is preferred.

**Option A (preferred): normalize every image to a fixed analysis size.** In `resize_for_analysis`,
resize so the longest side is **exactly** `max_dimension` whether the source is larger or smaller,
using `Image.Resampling.LANCZOS` for the enlarge direction. Geometry is then always measured at the
same pixel scale, so the existing thresholds become meaningful instead of accidentally calibrated.
The 15% leaf-coverage gate and the severity percentage are ratios and are unaffected.

**Option B: make the thresholds relative.** Express the run-length cutoffs as fractions of the
image's short side (or of the leaf mask's width) rather than constants, and re-derive the cut points
from the measurements rather than keeping 42 and 38.

Either way, **state the chosen threshold values and how they were derived** in the code comment, so
the next person can see they are calibrated rather than guessed.

Do not simply raise the floor to keep the current two images passing. That trades one scale for
another and the bug returns at the next resolution.

## The guard: a resolution sweep that fails today

Add to `tests/test_specimen_accuracy.py` a sweep over scales for every specimen:

```
for scale in (1.0, 0.75, 0.5, 0.35, 0.25, 0.15):
    resized = specimen.resize((w*scale, h*scale))
    assert diagnosis(resized) == expected
```

Plus an upsample case (scale 1.5) so the enlarge path is covered too.

Two requirements on this test:

1. **Confirm it FAILS before the fix.** It must fail on northern blight at 0.5 and 0.25 on the
   current code. A guard that passes before the fix is not guarding anything.
2. **Once it passes, break the fix deliberately** (revert the thresholds to absolute pixels) and
   confirm the test fails again. That is the non-vacuity check, and it is the standard the existing
   confidence-floor test already meets.

If a particular scale turns out to be genuinely unclassifiable, do not weaken the assertion silently.
Record the scale, the result, and the reason in the report, and mark that case as an expected hedge
rather than a pass.

## After the fix

1. **Re-measure the whole benchmark table** in `PROJECT_REPORT.md` at the standard photograph size,
   under the no-key path, and update every number. Do not carry over the old figures.
2. **Add the limitation honestly.** One line in the report: the discriminator is calibrated on two
   specimens, and the resolution sweep covers scale only, not lighting, angle, or background. Naming
   this reads as rigor to a judge; hiding it and being caught does not.
3. Keep everything else unchanged. This is a targeted fix, not a rewrite.

## Definition of done

1. The resolution sweep passes for all six specimens across at least six scales, including the
   northern-blight cases that fail today.
2. The sweep was **seen to fail before the fix** and **seen to fail when the fix is reverted**.
3. `PROJECT_REPORT.md`'s benchmark table is re-measured under the offline path, not carried over.
4. The report states what the calibration is based on and what the sweep does and does not cover.
5. All previous tests still pass (21/21 plus the new sweep).

**Report back with:** the sweep's output before and after, the reverted-fix failure, and the updated
benchmark table. A short, exact change with a test that can fail is worth more than a large one
without.
