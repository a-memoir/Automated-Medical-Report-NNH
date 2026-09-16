# ProjectNoiSoi — Image Leakage Audit Progress

## Current stage

The Dataset V1.2 image/report mapping and patient-level identity cleaning have been completed. The project is now in the **image-level leakage audit** stage before patient-level train/validation/test splitting and model development.

## Image audit master table

A clean image-level audit table was constructed by joining:

- successful original-image pHash records
- black/no-signal image flags
- final Dataset V1.2 case and patient identity information

Output:

```text
image_audit_master.csv
```

Google Drive location:

```text
/content/drive/MyDrive/NoiSoi_Matching/image_audit_master.csv
```

### Results

- **81,786** original-image pHash inventory rows
- **81,784** successful pHash rows
- **7,607** Dataset V1.2 cases
- **3,072** patient groups
- **76,403** images belonging to Dataset V1.2
- **76,328** normal images
- **75** black/no-signal images
- **0.098%** of mapped Dataset V1.2 images flagged as black/no-signal
- **7,607 / 7,607 cases** contain at least one normal image
- **54 cases** contain at least one black/no-signal image
- **53 patient groups** contain at least one black/no-signal image

The black/no-signal criterion is based on the previously completed image-level screening and is applied conservatively: an image is marked black only when explicitly flagged; missing flag records are not treated as black.

## Why black-screen filtering is necessary

Earlier cross-patient pHash audits produced many apparent pHash-exact matches. Visual inspection showed that the inspected groups consisted of black/no-signal frames rather than meaningful endoscopy-image duplicates.

Therefore, the earlier pHash duplicate counts must **not** be interpreted as confirmed image leakage. The leakage audit will be repeated after excluding black/no-signal images.

## Exact duplicate audit completed before filtering

SHA-256 exact duplicate analysis identified:

- 17 duplicated SHA-256 groups
- 43 images belonging to duplicate groups
- 2 groups spanning more than one case
- 2 groups spanning more than one patient

The two cross-patient groups were visually inspected and consisted of black-screen/no-signal images. They are therefore treated as artifacts for leakage analysis rather than meaningful clinical-image duplication. Original source files are preserved.

## Near-duplicate audit status

An initial pHash near-duplicate audit across all images generated a large number of apparent cross-patient matches, including:

- 2,810 cross-patient pairs at pHash distance 0
- 49,740 pairs at distance 2
- 269,420 pairs at distance 4

Visual inspection of representative pHash-distance-0 groups and 300 sampled pHash-distance-0 pairs showed black-screen/no-signal artifacts throughout the inspected samples.

These results motivated the black-screen filtering step and are retained only as preliminary audit evidence.

## Next step

The next audit will run on the **76,328 normal images only**:

1. Cross-patient pHash distance = 0 audit.
2. Cross-patient pHash distance = 2 audit.
3. Pixel-level verification of candidate pairs.
4. Visual inspection of confirmed candidates where necessary.
5. Separate true duplicate/shared-frame findings from compression, rendering, and other artifacts.
6. Freeze a leakage-safe patient-level split using `patient_group_id` only after the image-level audit is sufficiently resolved.

No source images or clinical PDFs will be deleted during this process. Audit outputs and flags remain on Google Drive and are excluded from the public repository.

## Compute note

This image audit is primarily CPU- and Google Drive I/O-bound. **GPU/A100 is not required** for the current leakage-audit stage.
