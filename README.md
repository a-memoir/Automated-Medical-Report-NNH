# Automated Medical Report — ENT Endoscopy

An ongoing research project for **automated medical report generation from ENT (Ear, Nose and Throat) endoscopy images**.

The long-term goal is to build a system that takes endoscopy images together with relevant patient/context information and generates a structured Vietnamese medical report. The project is currently focused on **dataset preparation and reliable image-to-report mapping** before model development.

> **Status:** Dataset V1.2 baseline completed. Model development has not started yet.

## Project goal

The planned system will eventually follow this general workflow:

```text
ENT endoscopy images
        +
patient / examination context
        ↓
image understanding
        ↓
clinical finding extraction
        ↓
structured medical report generation
```

The target report is expected to contain structured sections such as:

- Ear findings
- Nose / nasal cavity findings
- Nasopharynx findings
- Oropharynx findings
- Laryngopharynx / laryngeal findings
- Conclusion
- Differential diagnosis, when applicable
- Recommendations

The exact model architecture will be selected only after the underlying image/report pairs have been reliably constructed.

## Current dataset

The working dataset comes from ENT clinical records collected over multiple years. The full inventory contains:

- **21,257 PDF medical records**
- **81,786 original endoscopy images**
- **8,150 image folders / cases**

The current high-confidence mapped baseline contains:

- **7,607 cases**
- **76,405 original images**
- **7,607 selected PDFs**

The original images and medical PDFs are stored externally on Google Drive and are **not included in this repository**.

## Completed data pipeline

### 1. Original image indexing — completed

The original endoscopy image collection was indexed without moving or modifying the source files.

Each image has metadata including its path, case/folder identifier, timestamp and date.

Checkpoint:

```text
image_index.csv
```

### 2. PDF indexing — completed

All 21,257 PDF records were indexed. PDF dates were derived primarily from the directory structure rather than trusting potentially malformed filenames.

Result:

- 21,241 PDFs with a usable date
- 16 PDFs with unresolved dates

Checkpoint:

```text
pdf_index.csv
```

### 3. Date-based candidate generation — completed

Each image case was paired with PDF candidates from the same examination date. Cases containing more than one image date were handled using all observed dates.

Result:

- 8,150 image cases
- 8,127 cases with at least one date-based PDF candidate
- 23 cases without a date-based candidate
- 133,309 case × PDF candidate pairs
- 8,063 unique candidate PDFs

Checkpoint:

```text
case_candidates.csv
```

### 4. Original-image perceptual hashing — completed

Perceptual hashes (pHash) were computed for the original images so that high-resolution source images could be compared with lower-resolution images embedded in PDF reports.

Result:

- 81,784 images hashed successfully
- 2 source files appear to be corrupted / invalid JPEG binaries

Checkpoint:

```text
original_image_phash.csv
```

The two corrupted files are retained as errors rather than reconstructed or altered.

### 5. PDF thumbnail extraction and pHash — completed

Embedded endoscopy images were extracted from the PDF reports and their pHashes were cached for matching.

Result:

- 111,482 PDF thumbnail rows
- 111,476 successful thumbnails
- 21,257 PDFs represented
- 6 PDFs had no usable images
- 0 extraction errors
- 0 PDF-level errors

Checkpoint:

```text
pdf_thumbnail_phash.csv
```

### 6. PDF ↔ image matching — completed

PDF thumbnail pHashes were compared only against original images belonging to the corresponding image case, avoiding an impractical global all-to-all comparison.

Result:

- 133,309 case × PDF candidate rows evaluated
- 8,150 cases processed
- Matching results saved to `matching_results.csv`

The matching pipeline uses multiple signals rather than blindly trusting the nearest neighbor, including pHash distance, score margin, unique-match ratio and candidate ranking.

### 7. Confidence mapping — completed

A first operational confidence layer was created from the matching signals.

Result:

- **7,610 HIGH**
- **394 MEDIUM**
- **123 REVIEW**

These are **confidence categories, not measured accuracy**, because independent ground-truth labels were not available for the full dataset.

A conservative HIGH subset of **7,607 cases** was subsequently used for structured report extraction and Dataset V1/V1.1/V1.2 construction.

### 8. Structured report parsing — completed

PDF text extraction and structured parsing were performed for the 7,607 HIGH cases.

The parser extracts metadata and report sections including:

- patient name
- birth year
- sex
- address
- reason for endoscopy
- ear
- nasal cavity
- nasopharynx
- laryngopharynx / larynx
- oropharynx
- conclusion
- differential diagnosis
- recommendation

Parser validation identified and corrected support for an English-language report and a Vietnamese parsing edge case.

### 9. Dataset V1.2 — completed

Dataset V1.2 combines the trusted metadata from the original structured parser with the corrected section parser while preserving the original image ↔ case ↔ PDF mapping.

Final baseline:

- **7,607 cases**
- **76,405 images**
- **7,607 selected PDFs**
- **0 duplicate image paths**
- **0 shared PDFs between cases**
- **0 missing PDF files**
- **0 missing image files**
- **0 image-count mismatches**

Report quality audit:

- 7,605 cases flagged as OK
- 1 case with no parsed anatomical description
- 1 case with an empty conclusion in the source report
- 99.04% of cases contain a stated reason for endoscopy
- 99.99% contain a non-empty conclusion

Dataset files:

```text
dataset_v1_2_cases.csv
dataset_v1_2_images.csv
dataset_v1_2_quality_audit.csv
```

## Current next steps

The dataset is now ready for the next validation stage before model development:

1. Check for duplicate / near-duplicate images across different cases.
2. Freeze the case-level dataset split.
3. Create train / validation / test splits **by case_id**, not by individual image.
4. Check for train/test leakage.
5. Establish a baseline multimodal model.
6. Evaluate report generation and factual consistency.

## Repository structure

```text
Automated-Medical-Report-NNH/
├── README.md
├── .gitignore
├── requirements.txt
├── scripts/
│   ├── map_images_to_reports.py
│   └── map_drive_folders.py
├── docs/
│   └── ProjectNoiSoi_Matching_Progress.md
└── image_report_mapping_local.ipynb
```

The older mapping scripts/notebook are retained for reference while the checkpointed production pipeline is being developed.

## Data policy

This repository contains **code and project documentation only**.

Patient PDFs, endoscopy images, generated thumbnails, matching CSVs, checkpoints, credentials and other clinical data must remain outside the public Git repository.

The production pipeline is designed to operate against the dataset stored on Google Drive while keeping the repository reproducible and free of patient data.

## Important note

This is a research/development project. Automated outputs are not intended to replace clinician judgment or serve as a standalone clinical decision system.
