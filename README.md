# Automated Medical Report — ENT Endoscopy

An ongoing research project for **automated medical report generation from ENT (Ear, Nose and Throat) endoscopy images**.

The long-term goal is to build a system that takes endoscopy images together with relevant patient/context information and generates a structured Vietnamese medical report. The project is currently focused on **dataset preparation and image-to-report mapping** before model development.

> **Status:** Dataset mapping pipeline in progress. Model development has not started yet.

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

The working dataset comes from ENT clinical records collected over multiple years. The current inventory contains approximately:

- **21,257 PDF medical records**
- **81,786 original endoscopy images**
- **8,150 image folders / cases**

The original images and medical PDFs are stored externally on Google Drive and are **not included in this repository**.

## Current progress

### 1. Original image indexing — completed

The original endoscopy image collection has been indexed without moving or modifying the source files.

Each image has metadata including its path, case/folder identifier, timestamp and date.

Checkpoint:

```text
image_index.csv
```

### 2. PDF indexing — completed

All 21,257 PDF records have been indexed. PDF dates are derived primarily from the directory structure rather than trusting potentially malformed filenames.

Current working result:

- 21,241 PDFs with a usable date
- 16 PDFs with unresolved dates

Checkpoint:

```text
pdf_index.csv
```

### 3. Date-based candidate generation — completed

Each image case is paired with PDF candidates from the same examination date. Cases containing more than one image date are handled using all observed dates rather than assuming the first date is always correct.

Current working result:

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

Perceptual hashes (pHash) have been computed for the original images so that the high-resolution source images can be compared with the lower-resolution images embedded in the PDF reports.

Current result:

- 81,784 images hashed successfully
- 2 source files appear to be corrupted / invalid JPEG binaries

Checkpoint:

```text
original_image_phash.csv
```

The two corrupted files are retained as errors rather than reconstructed or altered.

### 5. PDF ↔ image matching — in progress

The next stage is to extract the endoscopy thumbnails embedded in the PDFs, compute their pHashes, and compare them only against original images belonging to the relevant case.

The planned matching pipeline is:

```text
case
 ↓
date-based PDF candidates
 ↓
extract PDF embedded images
 ↓
pHash PDF thumbnails
 ↓
compare against original-image pHashes
 ↓
aggregate candidate scores
 ↓
rank candidates
 ↓
HIGH / MEDIUM / REVIEW
```

A small pilot has already shown that pHash can identify visually identical PDF thumbnails and original frames, including cases where resizing/compression produces small non-zero distances. The pilot also exposed an important failure mode: a nearest-neighbor match can still be wrong when a PDF does not belong to the case. Therefore the production pipeline will use multiple signals such as distance, margin, unique-match ratio and candidate ranking rather than blindly assigning the nearest image.

## Repository structure

```text
Automated-Medical-Report-NNH/
├── README.md
├── .gitignore
├── scripts/
│   ├── map_images_to_reports.py
│   └── map_drive_folders.py
├── docs/
│   └── ProjectNoiSoi_Matching_Progress.md
└── image_report_mapping_local.ipynb
```

The older mapping scripts/notebook are retained for reference while the new checkpointed production pipeline is being developed.

## Data policy

This repository contains **code and project documentation only**.

Patient PDFs, endoscopy images, generated thumbnails, matching CSVs, checkpoints, credentials and other clinical data must remain outside the public Git repository.

The production pipeline is designed to operate against the dataset stored on Google Drive while keeping the repository reproducible and free of patient data.

## Planned roadmap

- [x] Index original endoscopy images
- [x] Index PDF reports
- [x] Generate date-based PDF candidates
- [x] Compute original-image pHash cache
- [ ] Extract and cache PDF thumbnail pHashes
- [ ] Complete image ↔ PDF matching
- [ ] Audit high-confidence and review cases
- [ ] Build the final image/report dataset
- [ ] Parse structured clinical report sections
- [ ] Establish train/validation/test splits
- [ ] Develop baseline report-generation models
- [ ] Evaluate clinical text generation and factual consistency
- [ ] Develop and evaluate the final multimodal medical report generation system

## Important note

This is a research/development project. Automated outputs are not intended to replace clinician judgment or serve as a standalone clinical decision system.
