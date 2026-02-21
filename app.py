import io
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

import requests
import streamlit as st
from pypdf import PdfReader

# ──────────────────────────────────────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="JobRadar", page_icon="🎯", layout="wide")

# ── Secrets / API Key ─────────────────────────────────────────────────────────
# Add this in Streamlit Cloud → Manage app → Settings → Secrets:
# RAPIDAPI_KEY="xxxx"
try:
    RAPIDAPI_KEY = st.secrets["RAPIDAPI_KEY"]
except Exception:
    st.error("Missing RAPIDAPI_KEY. Add it in Streamlit Cloud → Manage app → Settings → Secrets.")
    st.stop()

# ── Session State ─────────────────────────────────────────────────────────────
if "resume_text" not in st.session_state:
    st.session_state["resume_text"] = ""
if "job_results" not in st.session_state:
    st.session_state["job_results"] = []  # list[dict]
if "saved_jobs" not in st.session_state:
    st.session_state["saved_jobs"] = {}   # dict[job_id] -> job dict
if "match_cache" not in st.session_state:
    st.session_state["match_cache"] = {}  # dict[job_id] -> match dict


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def extract_text_from_pdf(uploaded_file) -> str:
    """Extract selectable text from a PDF (no API). Returns empty string if none."""
    try:
        pdf_bytes = uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts = []
        for p in reader.pages:
            parts.append(p.extract_text() or "")
        return _clean("\n".join(parts))
    except Exception:
        return ""

def normalize_company(name: str) -> str:
    name = (name or "").lower()
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\b(inc|llc|ltd|corp|corporation|co|company|plc)\b", " ", name)
    return _clean(name)

def company_soft_match(target: str, employer: str) -> bool:
    """Loose match: token overlap between target company and employer name."""
    t = normalize_company(target)
    e = normalize_company(employer)
    if not t:
        return True
    if t in e:
        return True
    tset = set(t.split())
    eset = set(e.split())
    return len(tset & eset) >= max(1, min(2, len(tset)))

@st.cache_data(ttl=900, show_spinner=False)
def jsearch(query: str, location: str, date_posted: str, employment_type: str, limit: int) -> List[Dict[str, Any]]:
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    params = {
        "query": query,
        "location": location or "United States",
        "num_pages": "1",
    }
    # Optional filters (supported by JSearch in many plans; harmless if ignored)
    if date_posted and date_posted != "any":
        params["date_posted"] = date_posted  # e.g., "today", "3days", "week", "month"
    if employment_type and employment_type != "any":
        params["employment_types"] = employment_type  # e.g., "FULLTIME"
    r = requests.get(url, headers=headers, params=params, timeout=30)
    data = r.json()
    jobs = data.get("data", []) or []
    return jobs[:limit]

def build_query(company: str, keywords: str) -> str:
    keywords = _clean(keywords)
    company = _clean(company)
    if company and keywords:
        return f"{keywords} {company}"
    return company or keywords

def job_id(job: Dict[str, Any]) -> str:
    return str(job.get("job_id") or job.get("id") or job.get("job_apply_link") or job.get("job_title") or time.time())

def job_apply(job: Dict[str, Any]) -> str:
    return job.get("job_apply_link") or job.get("job_google_link") or job.get("job_offer_expiration_datetime_utc") or ""

def job_company(job: Dict[str, Any]) -> str:
    return job.get("employer_name") or job.get("job_publisher") or ""

def job_location(job: Dict[str, Any]) -> str:
    return _clean(" ".join(filter(None, [job.get("job_city"), job.get("job_state"), job.get("job_country")])))

def job_desc(job: Dict[str, Any]) -> str:
    return job.get("job_description") or ""

def match_score(resume_text: str, jd_text: str) -> Tuple[int, List[str], List[str]]:
    """Lightweight keyword-based scorer (no API)."""
    resume = (resume_text or "").lower()
    jd = (jd_text or "").lower()
    if not resume or not jd:
        return 0, [], []

    groups = {
        "SQL": [r"\bsql\b", r"\bpostgres\b", r"\bsnowflake\b", r"\bbigquery\b"],
        "Python": [r"\bpython\b", r"\bpandas\b", r"\bnumpy\b", r"\bsklearn\b"],
        "People Analytics": [r"people analytics", r"workforce analytics", r"hr analytics", r"talent analytics"],
        "Experimentation": [r"a/b", r"experiment", r"causal", r"uplift", r"hypothesis"],
        "Pipelines/ETL": [r"etl", r"airflow", r"dbt", r"orchestrat", r"pipeline"],
        "Dashboards": [r"tableau", r"power bi", r"looker", r"dashboard"],
        "Stats/ML": [r"regression", r"classification", r"forecast", r"clustering", r"\bml\b"],
    }

    highlights, gaps = [], []
    score = 0
    for label, pats in groups.items():
        in_jd = any(re.search(p, jd) for p in pats)
        in_resume = any(re.search(p, resume) for p in pats)
        if in_jd and in_resume:
            score += 14
            highlights.append(label)
        elif in_jd and not in_resume:
            gaps.append(label)

    # simple overlap bonus
    jd_words = set(re.findall(r"[a-zA-Z]{4,}", jd))
    res_words = set(re.findall(r"[a-zA-Z]{4,}", resume))
    if jd_words:
        overlap = len(jd_words & res_words) / len(jd_words)
        score += int(min(20, overlap * 40))

    return min(100, score), highlights[:6], gaps[:6]


# ──────────────────────────────────────────────────────────────────────────────
# UI (NO SIDEBAR)
# ──────────────────────────────────────────────────────────────────────────────
st.title("🎯 JobRadar")
st.caption("Real live jobs • Fresh postings • Resume match scoring • Save jobs to apply later")

col1, col2 = st.columns([1, 1], gap="large")
with col1:
    companies_raw = st.text_input("Company (optional, comma-separated)", placeholder="Roblox, Google, Stripe, Meta")
with col2:
    keywords = st.text_input("Job title / keywords", placeholder="People Analytics, People Science, Data Scientist")

location = st.text_input("Location (optional)", value="United States", placeholder="United States, Remote, California")

cA, cB, cC = st.columns(3)
with cA:
    date_posted_ui = st.selectbox("Date posted", ["Any", "Today", "Last 3 days", "Last week", "Last month"], index=1)
with cB:
    emp_ui = st.selectbox("Employment type", ["Any", "Full-time", "Part-time", "Contract", "Internship"], index=0)
with cC:
    limit = st.slider("Results per search", min_value=5, max_value=50, value=10, step=5)

date_posted_map = {"Any": "any", "Today": "today", "Last 3 days": "3days", "Last week": "week", "Last month": "month"}
emp_map = {"Any": "any", "Full-time": "FULLTIME", "Part-time": "PARTTIME", "Contract": "CONTRACTOR", "Internship": "INTERN"}

date_posted = date_posted_map[date_posted_ui]
employment_type = emp_map[emp_ui]

with st.expander("📄 Upload resume for match scoring (optional)"):
    up = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"])
    pasted = st.text_area("Or paste resume text", height=160, placeholder="Paste resume text here…")

    if up is not None:
        if up.name.lower().endswith(".pdf"):
            t = extract_text_from_pdf(up)
            if t:
                st.session_state["resume_text"] = t
                st.success(f"Resume PDF parsed — {len(t)} characters")
            else:
                st.warning("Couldn’t extract text (maybe scanned image). Paste resume text instead.")
        else:
            txt = up.getvalue().decode("utf-8", errors="ignore")
            st.session_state["resume_text"] = _clean(txt)
            st.success(f"Resume TXT loaded — {len(st.session_state['resume_text'])} characters")

    if pasted.strip():
        st.session_state["resume_text"] = _clean(pasted)
        st.success(f"Resume text saved — {len(st.session_state['resume_text'])} characters")

btn1, btn2 = st.columns([1, 1])
with btn1:
    search_clicked = st.button("⚡ Find Jobs", use_container_width=True)
with btn2:
    clear_clicked = st.button("🧹 Clear Results", use_container_width=True)

if clear_clicked:
    st.session_state["job_results"] = []
    st.session_state["match_cache"] = {}
    st.success("Cleared results.")

# Validation: allow company OR keywords
if search_clicked:
    if not companies_raw.strip() and not keywords.strip():
        st.error("⚠️ Please enter a company OR job title/keywords.")
        st.stop()

    companies = [c.strip() for c in companies_raw.split(",") if c.strip()] or [None]

    all_jobs: List[Dict[str, Any]] = []
    progress = st.progress(0.0, text="🔍 Starting search…")
    for i, company in enumerate(companies):
        label = company if company else keywords
        progress.progress(i / len(companies), text=f"🔍 Searching {label}… ({i+1}/{len(companies)})")
        query = build_query(company or "", keywords)

        jobs = jsearch(query=query, location=location, date_posted=date_posted, employment_type=employment_type, limit=limit)

        # If company specified, prefer employer soft matches; but keep some results even if soft match fails
        if company:
            matched = [j for j in jobs if company_soft_match(company, job_company(j))]
            if matched:
                jobs = matched

        all_jobs.extend(jobs)

    progress.progress(1.0, text="✅ Done")
    # Deduplicate by id/apply link/title
    seen = set()
    deduped = []
    for j in all_jobs:
        key = (j.get("job_id") or j.get("job_apply_link") or "") + "|" + (j.get("job_title") or "")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)

    st.session_state["job_results"] = deduped
    st.success(f"Found {len(deduped)} jobs")

# Saved jobs panel (top of page, not sidebar)
with st.expander(f"⭐ Saved jobs ({len(st.session_state['saved_jobs'])})", expanded=False):
    if not st.session_state["saved_jobs"]:
        st.info("No saved jobs yet.")
    else:
        for jid, j in list(st.session_state["saved_jobs"].items()):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**{j.get('job_title','')}** — {job_company(j)}  \n{job_location(j)}")
                link = job_apply(j)
                if link:
                    st.markdown(f"[Apply link]({link})")
            with c2:
                if st.button("Remove", key=f"unsave_{jid}"):
                    st.session_state["saved_jobs"].pop(jid, None)
                    st.rerun()

st.divider()

jobs = st.session_state["job_results"]
if not jobs:
    st.info("Run a search to see results here.")
    st.stop()

resume_text = st.session_state["resume_text"]

for j in jobs:
    jid = job_id(j)
    title = j.get("job_title") or "Untitled role"
    comp = job_company(j)
    loc = job_location(j)
    apply = job_apply(j)

    with st.container(border=True):
        top = st.columns([6, 2, 2])
        with top[0]:
            st.markdown(f"### {title}")
            st.caption(f"{comp} • {loc}")
        with top[1]:
            if apply:
                st.link_button("Apply", apply, use_container_width=True)
            else:
                st.button("Apply", disabled=True, use_container_width=True)
        with top[2]:
            saved = jid in st.session_state["saved_jobs"]
            if st.button("★ Saved" if saved else "☆ Save", key=f"save_{jid}", use_container_width=True):
                if saved:
                    st.session_state["saved_jobs"].pop(jid, None)
                else:
                    st.session_state["saved_jobs"][jid] = j
                st.rerun()

        # Match section
        if resume_text:
            if jid in st.session_state["match_cache"]:
                ms = st.session_state["match_cache"][jid]
                st.metric("Resume match", f"{ms['score']}%")
                if ms["highlights"]:
                    st.write("✅ Highlights:", ", ".join(ms["highlights"]))
                if ms["gaps"]:
                    st.write("⚠️ Gaps:", ", ".join(ms["gaps"]))
            else:
                if st.button("🎯 Match Resume", key=f"match_{jid}"):
                    score, hi, gaps = match_score(resume_text, job_desc(j))
                    st.session_state["match_cache"][jid] = {"score": score, "highlights": hi, "gaps": gaps}
                    st.rerun()
        else:
            st.caption("Upload/paste a resume to enable match scoring.")

        with st.expander("Job description"):
            st.write(job_desc(j)[:6000] or "No description provided.")