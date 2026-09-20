# averis-hackathon-2026-

## DocuAnchor AI

Deterministic shipping-document triage and seven-field SI/BL comparison for the Averis x Monash Hackathon dataset.

**Current implementation status:** the repository contains a local, reproducible baseline and Streamlit reviewer UI. It does **not** currently call an LLM or external AI API, and it does **not** include a deployed public URL. Do not describe this version as AI-powered or cloud-hosted until those integrations are implemented and verified.

## What is implemented

- Classifies 520 inbox records into `BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, and `SPAM`.
- Reads TXT, PDF, DOCX, and XLSX attachments.
- Extracts and normalizes `shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`, `container_count`, and `gross_weight_kg`.
- Reports `MISMATCH` records with exact defect fields.
- Escalates `missing_attachment`, `wrong_doc_type`, `unreadable`, and `missing_value` cases as `NEEDS_REVIEW` while preserving the original email category.
- Provides a local Streamlit inspection dashboard and optional Docker packaging.

## Reproducible validation

Run:

```powershell
python solution.py --self-check
```

The current dataset run verifies 520 records, 137 human-review statuses, 26 mismatches, and the five-category output contract. These are pipeline checks, not ground-truth accuracy scores; a scorer or labeled reference set is required to claim precision, recall, F1, or a benchmark score.

Run the reproducible stress and throughput checks:

```powershell
python solution.py --benchmark
```

Observed local benchmark: 520 records in 2.3169 seconds (224.44 records/second), with 8/8 adversarial parser and routing tests passing. Throughput varies by machine. No Macro-F1, precision, recall, or weighted competition score is claimed because this repository does not contain a labeled ground-truth reference file.

## Proof links

The repository must be made public, or the final submission must use the correct public repository URL, before sharing it with judges. The currently configured Git remote is:

```text
https://github.com/shayan-tkhan/averis-hackathon-2026-
```

No public Cloud Run URL is included because no verified deployment exists in this repository.

## Run the baseline

Create a virtual environment and install the document readers:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Generate the deterministic submission from the local dataset:

```powershell
python solution.py --self-check
```

This reads the 520 inbox records, classifies each email, extracts the seven comparison fields, identifies document-review reasons, and writes `submission.json`. The raw `inbox/`, `attachments/`, and generated submission are ignored by Git.

## Open the reviewer dashboard

Install the dashboard dependency and launch it from the repository root:

```powershell
pip install -r requirements.txt
streamlit run app_ui.py
```

The dashboard lets you filter the inbox by category, inspect each email and its verification result, re-run `solution.py`, and download the generated submission.

The dashboard metrics distinguish verified BL matches from emails that were not comparison requests. Use the sidebar's SQLite import action to refresh `docuanchor.db`, which stores email metadata, pipeline results, attachment bytes, and SHA-256 hashes locally.

## Run with Docker

Docker is optional for local scoring. It packages the Python runtime and dependencies consistently for teammates and cloud deployment. The raw dataset remains outside the image and is mounted by Compose:

```powershell
docker compose up --build
```

Open `http://localhost:8501`. To generate the submission inside the container:

```powershell
docker compose run --rm docuanchor python solution.py --self-check
```