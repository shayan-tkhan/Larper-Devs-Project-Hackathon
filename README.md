# DocuAnchor

Deterministic shipping-document triage and seven-field SI/BL comparison for the Averis x Monash Hackathon 2026 dataset.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Docker Ready](https://img.shields.io/badge/docker-ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Averis x Monash](https://img.shields.io/badge/Hackathon-Averis%20x%20Monash%202026-orange)](https://averis.biz/)

## Contents

- [Current status](#current-status)
- [What is implemented](#what-is-implemented)
- [Architecture](#architecture)
- [Reproducible validation](#reproducible-validation)
- [Screenshots](#screenshots)
- [Run the baseline](#run-the-baseline)
- [Open the reviewer dashboard](#open-the-reviewer-dashboard)
- [Run with Docker](#run-with-docker)
- [Proof links](#proof-links)
- [Known limitations](#known-limitations)
- [Team](#team)

## Current status

This repository contains a local, reproducible baseline pipeline and a Streamlit reviewer UI. **It does not currently call an LLM or external AI API.** Do not describe this version as AI-powered unless you have explicitly wired an LLM provider into the code path.

**Dataset:** the raw `inbox/` and `attachments/` folders are intentionally excluded from this repository for confidentiality and are not committed to version control. To run locally, place the offline data in the expected folders before executing the pipeline.

### Local API key setup

If you want to enable an external model integration later, create a local `.env` file in the project root and add your API key there. Keep this file out of git and never commit it to the repository.

```env
GEMINI_API_KEY=your_api_key_here
```

If you are using a shell instead of a `.env` file, the equivalent is:

```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

The project root should not include a committed `.env` file. If you already have a local key configured in your environment, use that value rather than copying a shared secret into the repo.

## What is implemented

- Classifies 520 inbox records into `BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, and `SPAM`.
- Reads TXT, PDF, DOCX, and XLSX attachments.
- Extracts and normalizes `shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`, `container_count`, and `gross_weight_kg`.
- Reports `MISMATCH` records with exact defect fields.
- Escalates `missing_attachment`, `wrong_doc_type`, `unreadable`, and `missing_value` cases as `NEEDS_REVIEW`, while preserving the original email category.
- Persists results to SQLite (`docuanchor.db`) with attachment bytes and SHA-256 hashes.
- Provides a local Streamlit reviewer dashboard and optional Docker packaging.

## Architecture

```
Inbox (520 records)
      |
      v
Intent classification  --------->  5 categories
      |
      v (BL_COMPARISON only)
Multi-format document read (pypdf / python-docx / openpyxl / txt)
      |
      v
Field extraction (7 fields) + edge-case detection
      |
      v
Canonical normalization + deterministic diff
      |
      v
MATCH / MISMATCH / NEEDS_REVIEW  --->  SQLite + submission.json  --->  Streamlit dashboard
```

Classification and extraction are currently rule-based (regex/keyword matching), not model-based. Comparison and status decisions are fully deterministic code with no AI in the loop at any stage.

## Reproducible validation

Run:

```powershell
python solution.py --self-check
```

Verifies 520 records processed, with the five-category output contract intact. Of 194 `BL_COMPARISON` emails: 31 matched, 26 flagged `MISMATCH`, 137 escalated to `NEEDS_REVIEW` (70 missing an attachment, 49 with a document mismatch, and 18 with extraction problems).

Run the adversarial and throughput checks:

```powershell
python solution.py --benchmark
```

8/8 adversarial parser and routing tests passing. Throughput is machine-dependent — re-run locally and report your own number rather than relying on a figure recorded on different hardware.

**No precision, recall, F1, or benchmark score is claimed.** These are pipeline self-checks against known planted edge cases, not accuracy against a labeled ground-truth set.

## Screenshots

_(Add 2-4 screenshots of the dashboard here: the metrics row, a MISMATCH email with defect fields shown, and the category filter in use.)_

## Run the baseline

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python solution.py --self-check
```

This reads the inbox records, classifies each email, extracts the seven comparison fields, identifies review reasons, and writes `submission.json`.

## Open the reviewer dashboard

```powershell
pip install -r requirements.txt
streamlit run app_ui.py
```

Filter by category, inspect any email and its verification result, re-run the pipeline, refresh the SQLite store, and download the generated submission — all from the sidebar.

## Run with Docker

Docker packages the Python runtime and dependencies consistently across machines. The raw dataset stays outside the image and is provided at build/run time, not committed to it.

```powershell
docker compose up --build
```

Open `http://localhost:8501`. To generate the submission inside the container:

```powershell
docker compose run --rm docuanchor python solution.py --self-check
```

## Proof links

- **Repository:** https://github.com/shayan-tkhan/Larper-Devs-Project-Hackathon _(confirm this matches your actual new repo name/URL before submitting)_
- **Live demo:** https://larper-devs-project-hackathon.streamlit.app/ — **status unverified as of this commit.** Open this link yourself and confirm the dashboard loads with real data before treating this as a verified deployment.
- **Video demo:** _(add link once recorded)_

## Known limitations

- No AI/LLM extraction — field extraction is same-line regex matching, which is fragile against multi-column PDF layouts. This is the largest driver of the 70.6% `NEEDS_REVIEW` rate within `BL_COMPARISON` records.
- `classify_email` uses subject-line text only; the email body is not considered.
- Document-type validation (`wrong_doc_type`) only checks the second attachment; the first is assumed to be the SI without verification.
- No ground-truth accuracy numbers yet — self-checks confirm the pipeline runs correctly, not that its judgments are correct against a labeled reference.

## Team

| Name | GitHub | Role |
|---|---|---|
| _Shayan_ | _shayan-tkhan_ | Pipeline logic, validation |
| _Syed_ | _syed-93_ | Deployment, data infrastructure |
| _Abu huraira_ | _Abuhuraira-PY-T_ | Dashboard, documentation, submission |
