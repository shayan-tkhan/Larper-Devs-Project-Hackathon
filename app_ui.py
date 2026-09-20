#!/usr/bin/env python3
"""DocuAnchor interactive reviewer dashboard."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import streamlit as st

from database import import_dataset


ROOT = Path(__file__).parent
SUBMISSION_PATH = ROOT / "submission.json"
INBOX_PATH = ROOT / "inbox"
DATABASE_PATH = ROOT / "docuanchor.db"

st.set_page_config(
    page_title="DocuAnchor | Shipping Document Verification",
    page_icon="D",
    layout="wide",
)


@st.cache_data
def load_submission() -> dict:
    if not SUBMISSION_PATH.exists():
        return {}
    return json.loads(SUBMISSION_PATH.read_text(encoding="utf-8"))


def run_pipeline() -> tuple[bool, str]:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "solution.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = completed.stdout or completed.stderr or "Pipeline finished without output."
    return completed.returncode == 0, output


def run_benchmark() -> tuple[bool, str]:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "solution.py"), "--benchmark"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = completed.stdout or completed.stderr or "Benchmark finished without output."
    return completed.returncode == 0, output


def refresh_database() -> dict:
    return import_dataset(ROOT, DATABASE_PATH)


st.title("DocuAnchor")
st.caption("Deterministic shipping-document triage, verification, and human review")

with st.sidebar:
    st.header("Pipeline Controls")
    if st.button("Re-run solution.py", type="primary", use_container_width=True):
        with st.spinner("Processing the 520-email inbox..."):
            succeeded, output = run_pipeline()
        load_submission.clear()
        if succeeded:
            database_summary = refresh_database()
            st.success("Pipeline finished")
            st.caption(
                f"SQLite refreshed: {database_summary['emails']} emails, "
                f"{database_summary['attachments']} attachments"
            )
        else:
            st.error("Pipeline failed")
        st.code(output[-1200:])
    if st.button("Run benchmark", use_container_width=True):
        with st.spinner("Running parser stress tests and throughput measurement..."):
            succeeded, output = run_benchmark()
        if succeeded:
            st.success("Benchmark passed")
        else:
            st.error("Benchmark failed")
        st.code(output[-1200:])
    if st.button("Import dataset into SQLite", use_container_width=True):
        with st.spinner("Importing emails and attachments into SQLite..."):
            database_summary = refresh_database()
        st.success(
            f"SQLite refreshed: {database_summary['emails']} emails, "
            f"{database_summary['attachments']} attachments"
        )

submission = load_submission()
if not INBOX_PATH.exists():
    st.error("Cannot find the inbox/ folder beside app_ui.py.")
    st.stop()

email_files = sorted(INBOX_PATH.glob("email_*.json"))
if not email_files:
    st.error("No email JSON files were found in inbox/.")
    st.stop()

total = len(submission)
ok_count = sum(
    item.get("category") == "BL_COMPARISON" and item.get("status") == "OK"
    for item in submission.values()
)
mismatch_count = sum(item.get("status") == "MISMATCH" for item in submission.values())
review_count = sum(item.get("status") == "NEEDS_REVIEW" for item in submission.values())
comparison_count = sum(item.get("category") == "BL_COMPARISON" for item in submission.values())
not_compared_count = total - comparison_count

metrics = st.columns(6)
metrics[0].metric("Emails", total)
metrics[1].metric("BL comparisons", comparison_count)
metrics[2].metric("Matched", ok_count)
metrics[3].metric("Mismatches", mismatch_count)
metrics[4].metric("Needs review", review_count)
metrics[5].metric("Not compared", not_compared_count)
st.divider()

filter_category = st.selectbox(
    "Category",
    ["ALL", "BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"],
)
filtered_files = [
    path
    for path in email_files
    if filter_category == "ALL"
    or submission.get(path.stem, {}).get("category") == filter_category
]
if not filtered_files:
    st.info("No emails match this category.")
    st.stop()

selected_file = st.selectbox(
    f"Email ({len(filtered_files)} matching)",
    filtered_files,
    format_func=lambda path: path.stem,
)
email = json.loads(selected_file.read_text(encoding="utf-8"))
email_id = email.get("email_id", selected_file.stem)
result = submission.get(email_id, {})
status = result.get("status", "NOT_PROCESSED")

status_color = {"OK": "green", "MISMATCH": "red", "NEEDS_REVIEW": "orange"}.get(status, "gray")
st.markdown(f"### {email_id}  |  :{status_color}[{status}]")

left, right = st.columns(2)
with left:
    st.subheader("Email")
    st.text_input("Subject", email.get("subject", ""), disabled=True)
    st.text_input("From", email.get("from", ""), disabled=True)
    st.text_area("Body", email.get("body", ""), height=220, disabled=True)
    st.subheader("Attachments")
    attachments = email.get("attachments", [])
    if attachments:
        for attachment in attachments:
            st.write(f"- `{attachment}`")
    else:
        st.write("No attachments")

with right:
    st.subheader("Verification output")
    st.json(result)
    if result.get("defect_fields"):
        st.error("Mismatched fields: " + ", ".join(result["defect_fields"]))
    elif result.get("review_reason"):
        st.warning("Human review reason: " + result["review_reason"])
    elif status == "OK":
        st.success("All compared fields match.")

st.divider()
if SUBMISSION_PATH.exists():
    st.download_button(
        "Download submission.json",
        data=SUBMISSION_PATH.read_bytes(),
        file_name="submission.json",
        mime="application/json",
    )