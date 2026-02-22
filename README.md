# 🎯 JobRadar

> **Stop scrolling job boards. Track the companies you want, get fresh postings the moment they drop — matched to your resume.**

Live app → **[datascijobs.streamlit.app](https://datascijobs.streamlit.app)**

---

## What it does

JobRadar is a real-time job intelligence tool built for data science and people analytics professionals. Instead of manually checking multiple job boards every day, you tell it which companies to watch and it surfaces fresh postings — scored against your resume using AI.

![JobRadar Screenshot](https://via.placeholder.com/900x400/0f0c29/a89dff?text=JobRadar+%F0%9F%8E%AF)

---

## Features

- ⚡ **Real-time job search** — pulls live postings from LinkedIn, Indeed, Glassdoor and company career pages
- 📅 **Date filters** — Last 24 hours, 3 days, this week, this month
- 🎯 **AI resume match scoring** — powered by Llama 3.3 70B via Groq (free)
- 📄 **PDF resume parsing** — upload your resume PDF directly, no copy-paste needed
- ⭐ **Save jobs** — bookmark roles to apply to later
- 🏢 **Multi-company tracking** — search across multiple companies in one click
- 💰 **Salary display** — shows compensation range where available

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Job Data | JSearch API via RapidAPI |
| AI Scoring | Groq API (Llama 3.3 70B) |
| PDF Parsing | pypdf |
| Deployment | Streamlit Cloud + GitHub |

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/sharmasunidhi2895-bot/jobradar.git
cd jobradar
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Get your free API keys

**RapidAPI (JSearch) — 200 free requests/month**
1. Go to [rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
2. Subscribe to the Basic (Free) plan
3. Copy your `x-rapidapi-key`

**Groq — Free AI inference**
1. Go to [console.groq.com](https://console.groq.com) — no credit card needed
2. Create an API key
3. Copy your `gsk_...` key

### 4. Add secrets

Create a `.streamlit/secrets.toml` file:
```toml
RAPIDAPI_KEY = "your_rapidapi_key_here"
GROQ_KEY = "your_groq_key_here"
```

### 5. Run locally
```bash
streamlit run app.py
```

---

## Deploy to Streamlit Cloud

1. Fork this repo
2. Go to [share.streamlit.io](https://share.streamlit.io) → Create app
3. Select your repo → `app.py`
4. Go to **Settings → Secrets** and add your API keys
5. Deploy!

---

## How the AI match scoring works

When you upload your resume and click **🎯 Match Resume** on any job card, the app sends your resume and the job description to Llama 3.3 70B (running on Groq's free API). The model returns:

- **Score** (0–100%) — overall fit
- **Strengths** — where your background aligns
- **Gaps** — requirements you may be missing
- **Verdict** — one honest sentence summary

If no Groq key is provided, it falls back to keyword-based scoring automatically.

---

## Built by

**Sunidhi Sharma** — People Analytics & Data Science  
[LinkedIn](https://linkedin.com/in/sharmasunidhi) · [datascijobs.streamlit.app](https://datascijobs.streamlit.app)

---

## License

MIT — free to use and modify.
