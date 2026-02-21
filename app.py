import streamlit as st
import requests
from datetime import datetime, timezone

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="JobRadar", page_icon="🎯", layout="wide")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap');
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
  .block-container { padding-top: 2rem; max-width: 960px; }
  h1,h2,h3 { font-family: 'Syne', sans-serif; }
  div[data-testid="stMetricValue"] { font-size: 1.8rem; }
  .stButton>button {
    background: linear-gradient(135deg, #6c63ff, #8b5cf6);
    color: white; border: none; border-radius: 10px;
    font-family: 'Syne', sans-serif; font-weight: 800;
    padding: 0.6rem 1.4rem; width: 100%;
  }
  .stButton>button:hover { opacity: 0.9; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("# 🎯 JobRadar")
st.markdown("**Real live jobs · Fresh postings only · AI resume match scoring**")
st.divider()

# ── Sidebar config ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    rapid_key = st.text_input(
        "RapidAPI Key",
        type="password",
        placeholder="Paste your x-rapidapi-key…",
        help="Free key at rapidapi.com → JSearch → Subscribe Basic"
    )
    st.caption("Get free key: [rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)")

    st.markdown("---")

    anthropic_key = None  # Free scoring — no API key needed

    st.markdown("---")
    st.markdown("### 📅 Filters")

    date_posted = st.selectbox(
        "Date Posted",
        options=["today", "3days", "week", "month", ""],
        format_func=lambda x: {
            "today":  "⚡ Last 24 hours",
            "3days":  "📅 Last 3 days",
            "week":   "📅 This week",
            "month":  "📅 This month",
            "":       "📅 Any time",
        }.get(x, x)
    )

    emp_type = st.selectbox(
        "Employment Type",
        options=["", "FULLTIME", "PARTTIME", "CONTRACTOR", "INTERN"],
        format_func=lambda x: {
            "":           "All types",
            "FULLTIME":   "Full-time",
            "PARTTIME":   "Part-time",
            "CONTRACTOR": "Contract",
            "INTERN":     "Internship",
        }.get(x, x)
    )

    results_per_co = st.slider("Results per company", 3, 10, 5)

# ── Main search form ───────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    companies_raw = st.text_input(
        "🏢 Companies (comma-separated)",
        placeholder="Roblox, Google, Stripe, Meta…"
    )
with col2:
    keywords = st.text_input(
        "🔍 Job Title / Keywords",
        placeholder="People Science, Data Analyst…"
    )

location = st.text_input(
    "📍 Location",
    placeholder="United States, Remote, New York NY…",
    value="United States"
)

# ── Resume upload ──────────────────────────────────────────────────────────────
with st.expander("📄 Upload Resume for AI Match % Scoring (optional)"):
    resume_file = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"])
    resume_text_input = st.text_area("Or paste your resume text here", height=150)

    resume_text = ""
    if resume_file:
        if resume_file.type == "text/plain":
            resume_text = resume_file.read().decode("utf-8")
            st.session_state["resume_text"] = resume_text
            st.success(f"✓ Resume loaded — {len(resume_text)} characters")
        elif resume_file.type == "application/pdf":
            st.warning("📄 PDF not supported — please paste your resume text in the box below.")
    elif resume_text_input.strip():
        resume_text = resume_text_input.strip()
        st.session_state["resume_text"] = resume_text
        st.success(f"✓ Resume text ready — {len(resume_text)} characters")

    # Restore from session state if present
    if not resume_text and "resume_text" in st.session_state:
        resume_text = st.session_state["resume_text"]

st.divider()

# ── Search button ──────────────────────────────────────────────────────────────
search_clicked = st.button("⚡ Find Fresh Jobs Now", use_container_width=True)

# ── Helper functions ───────────────────────────────────────────────────────────
def fmt_posted(ts):
    if not ts: return "Recently"
    d = int((datetime.now(timezone.utc).timestamp() - ts) / 86400)
    if d == 0: return "🟢 Today"
    if d == 1: return "🟢 Yesterday"
    if d < 7:  return f"🟡 {d} days ago"
    if d < 30: return f"⚪ {d//7} week{'s' if d//7>1 else ''} ago"
    return f"🔴 {d//30} month{'s' if d//30>1 else ''} ago"

def fmt_salary(job):
    mn = job.get("job_min_salary")
    mx = job.get("job_max_salary")
    period = {"year":"/yr","month":"/mo","hour":"/hr"}.get((job.get("job_salary_period") or "").lower(), "")
    if mn and mx: return f"${int(mn):,} – ${int(mx):,}{period}"
    if mn: return f"${int(mn):,}+{period}"
    return None

def search_company(company, keywords, location, rapid_key, date_posted, emp_type, n):
    # Search directly for "keywords at company" — most targeted query
    query = f"{keywords} at {company}"
    params = {
        "query": query,
        "page": "1",
        "num_pages": "2",
        "results_per_page": "10",
        "country": "us",
    }
    if date_posted: params["date_posted"] = date_posted
    if emp_type:    params["employment_types"] = emp_type

    resp = requests.get(
        "https://jsearch.p.rapidapi.com/search",
        headers={
            "x-rapidapi-key":  rapid_key,
            "x-rapidapi-host": "jsearch.p.rapidapi.com",
        },
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    all_results = resp.json().get("data", [])

    # Strict filter: employer name must contain the company name
    company_lower = company.lower()
    strict = [j for j in all_results if company_lower in (j.get("employer_name") or "").lower()]

    if strict:
        return strict[:n]

    # If no strict matches, try broader search without date filter
    params2 = {
        "query": f"{keywords} {company}",
        "page": "1",
        "num_pages": "2",
        "results_per_page": "10",
        "country": "us",
    }
    if emp_type: params2["employment_types"] = emp_type

    resp2 = requests.get(
        "https://jsearch.p.rapidapi.com/search",
        headers={
            "x-rapidapi-key":  rapid_key,
            "x-rapidapi-host": "jsearch.p.rapidapi.com",
        },
        params=params2,
        timeout=15,
    )
    resp2.raise_for_status()
    all_results2 = resp2.json().get("data", [])
    strict2 = [j for j in all_results2 if company_lower in (j.get("employer_name") or "").lower()]

    return strict2[:n] if strict2 else []

def match_resume(job, resume_text, anthropic_key=None):
    """Free keyword-based resume match scoring — no API needed."""
    import re
    from collections import Counter

    # Get job text
    job_title = (job.get("job_title") or "").lower()
    job_desc  = (job.get("job_description") or "").lower()
    job_quals = " ".join((job.get("job_highlights") or {}).get("Qualifications", [])).lower()
    job_text  = f"{job_title} {job_desc} {job_quals}"

    resume_lower = resume_text.lower()

    # Key skill categories to check
    skill_groups = {
        "Data Analysis":      ["data analysis","sql","python","r ","tableau","power bi","excel","statistics","regression","hypothesis"],
        "People Analytics":   ["people analytics","hr analytics","workforce","people science","organizational","talent","employee","engagement","retention","attrition"],
        "Machine Learning":   ["machine learning","ml","predictive","modeling","scikit","xgboost","random forest","neural","deep learning"],
        "Experimentation":    ["a/b test","experiment","causal","statistical significance","p-value","survey","research"],
        "Communication":      ["dashboard","presentation","stakeholder","insight","report","visualiz","storytelling"],
        "Leadership":         ["lead","manage","mentor","team","cross-functional","strategy","roadmap"],
        "Tools":              ["excel","google sheets","looker","dbt","airflow","spark","bigquery","snowflake","databricks"],
    }

    matched_skills = []
    missing_skills = []
    score = 0

    for group, keywords in skill_groups.items():
        job_needs  = any(k in job_text   for k in keywords)
        resume_has = any(k in resume_lower for k in keywords)
        if job_needs and resume_has:
            matched_skills.append(group)
            score += 14
        elif job_needs and not resume_has:
            missing_skills.append(group)

    # Bonus: direct keyword overlap between job and resume
    job_words    = set(re.findall(r'\b\w{5,}\b', job_text))
    resume_words = set(re.findall(r'\b\w{5,}\b', resume_lower))
    overlap = len(job_words & resume_words)
    bonus = min(overlap // 3, 15)
    score = min(score + bonus, 100)

    # Build verdict
    if score >= 75:
        verdict = "Strong match — your background aligns well with this role."
    elif score >= 50:
        verdict = "Good match — you meet several key requirements but have some gaps."
    else:
        verdict = "Partial match — consider highlighting more relevant experience."

    return {
        "score":     score,
        "strengths": matched_skills[:3] if matched_skills else ["Resume loaded successfully"],
        "gaps":      missing_skills[:2] if missing_skills else [],
        "verdict":   verdict,
    }

def render_source_badge(job):
    pub = (job.get("job_publisher") or "").lower()
    link = (job.get("job_apply_link") or "").lower()
    combined = pub + link
    if "linkedin"  in combined: return "🔵 LinkedIn"
    if "indeed"    in combined: return "🟢 Indeed"
    if "glassdoor" in combined: return "🟣 Glassdoor"
    return "🏢 Company Site"

# ── Run search ─────────────────────────────────────────────────────────────────
if search_clicked:
    if not rapid_key:
        st.error("⚠️ Please add your RapidAPI key in the sidebar.")
        st.stop()
    if not companies_raw.strip():
        st.error("⚠️ Please enter at least one company name.")
        st.stop()
    if not keywords.strip():
        st.error("⚠️ Please enter a job title or keywords.")
        st.stop()

    companies = [c.strip() for c in companies_raw.split(",") if c.strip()]
    all_jobs = []

    progress = st.progress(0, text="Starting search…")
    for i, company in enumerate(companies):
        progress.progress((i) / len(companies), text=f"🔍 Searching {company}… ({i+1}/{len(companies)})")
        try:
            jobs = search_company(company, keywords, location, rapid_key, date_posted, emp_type, results_per_co)
            all_jobs.extend(jobs)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (401, 403):
                st.error("❌ Invalid RapidAPI key. Please check the sidebar.")
                st.stop()
            elif e.response.status_code == 429:
                st.error("⚠️ Rate limit reached. You've used your free 200 requests this month.")
                st.stop()
            else:
                st.warning(f"Error searching {company}: {e}")
        except Exception as e:
            st.warning(f"Error searching {company}: {e}")

    progress.progress(1.0, text="✅ Done!")

    # Deduplicate by job_id
    seen = set()
    unique = []
    for j in all_jobs:
        if j.get("job_id") not in seen:
            seen.add(j.get("job_id"))
            unique.append(j)

    # Hard date filter on client side too (JSearch sometimes ignores it)
    now_ts = datetime.now(timezone.utc).timestamp()
    max_age = {"today":1,"3days":3,"week":7,"month":30}.get(date_posted, 9999)
    if date_posted:
        unique = [j for j in unique if not j.get("job_posted_at_timestamp") or
                  (now_ts - j["job_posted_at_timestamp"]) / 86400 <= max_age]

    # Sort newest first
    unique.sort(key=lambda j: j.get("job_posted_at_timestamp") or 0, reverse=True)

    if not unique:
        date_label = {"today":"last 24 hours","3days":"last 3 days","week":"this week","month":"this month"}.get(date_posted,"")
        st.warning(f"No jobs found{' posted in the '+date_label if date_label else ''}. Try 'Any time' or broader keywords.")
        st.stop()

    # ── Stats ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ Jobs Found", len(unique))
    c2.metric("🏢 Companies", len(set(j.get("employer_name","") for j in unique)))
    c3.metric("🌐 Remote", sum(1 for j in unique if j.get("job_is_remote")))
    today_count = sum(1 for j in unique if fmt_posted(j.get("job_posted_at_timestamp")).startswith("🟢"))
    c4.metric("🆕 Fresh (today/yesterday)", today_count)

    st.markdown("---")

    # ── Job cards ──────────────────────────────────────────────────────────────
    for job in unique:
        posted   = fmt_posted(job.get("job_posted_at_timestamp"))
        salary   = fmt_salary(job)
        source   = render_source_badge(job)
        loc_str  = "🌐 Remote" if job.get("job_is_remote") else ", ".join(filter(None,[job.get("job_city"),job.get("job_state"),job.get("job_country")]))
        emp_str  = (job.get("job_employment_type") or "Full-time").replace("_"," ").title()
        desc     = (job.get("job_description") or "")[:300]
        quals    = (job.get("job_highlights") or {}).get("Qualifications", [])[:3]
        apply_url= job.get("job_apply_link") or job.get("job_google_link","#")

        with st.container(border=True):
            # Header row
            hcol1, hcol2 = st.columns([3,1])
            with hcol1:
                st.markdown(f"### {job.get('job_title','Job Opening')}")
                st.markdown(f"**{job.get('employer_name','Company')}** &nbsp;·&nbsp; {source}")
            with hcol2:
                st.markdown(f"**{posted}**")
                if salary:
                    st.markdown(f"💰 `{salary}`")

            # Meta row
            meta_parts = [f"📍 {loc_str}", f"💼 {emp_str}"]
            st.markdown("  &nbsp;|&nbsp;  ".join(meta_parts))

            # Description
            if desc:
                st.markdown(f"<p style='color:#888;font-size:14px;'>{desc}…</p>", unsafe_allow_html=True)

            # Skill tags
            if quals:
                tags_html = " ".join([f"<span style='background:rgba(108,99,255,0.15);border:1px solid rgba(108,99,255,0.3);color:#a89dff;padding:3px 10px;border-radius:6px;font-size:12px;margin-right:4px'>{q[:50]}</span>" for q in quals])
                st.markdown(tags_html, unsafe_allow_html=True)
                st.markdown("")

            # Action row
            btn_col1, btn_col2, btn_col3 = st.columns([1,1,3])
            with btn_col1:
                st.link_button("Apply Now ↗", apply_url, use_container_width=True)

            with btn_col2:
                if resume_text:
                    match_key = f"match_{job.get('job_id','')}"
                    if match_key not in st.session_state:
                        if st.button("🎯 Match Resume", key=f"btn_{job.get('job_id','')}"):
                            with st.spinner("Analyzing match…"):
                                try:
                                    result = match_resume(job, resume_text)
                                    st.session_state[match_key] = result
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Match failed: {e}")
                    else:
                        result = st.session_state[match_key]
                        score = result.get("score", 0)
                        color = "green" if score>=75 else "orange" if score>=50 else "red"
                        label = "Strong Match" if score>=75 else "Good Match" if score>=50 else "Weak Match"
                        st.markdown(f"**:{color}[{score}% — {label}]**")
                elif not resume_text:
                    st.caption("↑ Add resume to match")

            # Show match details if available
            match_key = f"match_{job.get('job_id','')}"
            if match_key in st.session_state:
                result = st.session_state[match_key]
                with st.expander("View match details"):
                    if result.get("strengths"):
                        st.markdown("**✅ Strengths:** " + " · ".join(result["strengths"]))
                    if result.get("gaps"):
                        st.markdown("**⚠️ Gaps:** " + " · ".join(result["gaps"]))
                    if result.get("verdict"):
                        st.markdown(f"*{result['verdict']}*")

        st.markdown("")
