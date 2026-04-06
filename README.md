# SkillMatch AI

**Intelligent Multi-Agent Career Page System for Automated Role Matching and Skill Gap Mining**

> CSE-572 Data Mining — Spring 2026 | Arizona State University | Group 36

---

## Overview

SkillMatch AI is a full-stack multi-agent pipeline that parses resumes, matches candidates to career roles, and mines skill gaps using NLP, cosine similarity, K-Means clustering, and association rule mining. It was built as part of the CSE-572 Data Mining course project.

The system ingests a resume (text, PDF, or image), runs it through three specialized agents in sequence, and returns:
- Ranked job role matches with confidence scores
- Prioritized skill gap recommendations ("What to Learn Next")
- Cluster analysis showing where the candidate fits in the broader job market

---

## Live Demo

The frontend is deployed as a static site. The interactive features (Resume Analyzer, Role Matching, Skill Gap) require the FastAPI backend to be running locally.

---

## Architecture

```
Resume (text / PDF / image)
        │
        ▼
┌─────────────────────┐
│  Agent 1            │
│  Resume Parser      │  ← spaCy NLP + regex patterns
│  agent_resume_      │    Extracts: skills, education,
│  parser.py          │    experience, job titles
└────────┬────────────┘
         │  structured skill vector
         ▼
┌─────────────────────┐
│  Agent 2            │
│  Role Matching      │  ← Cosine similarity + IDF weighting
│  agent_role_        │    + K-Means category alignment bonus
│  matcher.py         │    Returns: top-K ranked JD matches
└────────┬────────────┘
         │  target JD + candidate skills
         ▼
┌─────────────────────┐
│  Agent 3            │
│  Skill Gap Miner    │  ← Association rule mining
│  gap_scoring.py     │    + 3× weight for required skills
│                     │    Returns: prioritized upskilling list
└─────────────────────┘
```

The pipeline is evaluated against a TF-IDF baseline across Precision@K metrics. The multi-agent approach outperforms the baseline on all K values.

---

## Features

| Feature | Description |
|---|---|
| **Resume Analyzer** | Upload a PDF, image (JPG/PNG/BMP/TIFF/WebP), or paste text. Extracts skills, education level, years of experience, and job titles using NLP. |
| **Role Matching** | Matches extracted skills against 25 job descriptions (18 senior roles + 7 intern roles) using IDF-weighted cosine similarity. |
| **Skill Gap Analysis** | Shows missing required and preferred skills for a target role, ranked by priority. Required skills are always ranked first with a 3× weight boost. |
| **Clusters** | K-Means clustering (k=9) of 9,000 resumes from the Kaggle dataset. Cluster labels are derived from top skills, not dataset category names. |
| **Association Rules** | Frequent itemset mining (Apriori) on skill co-occurrences to discover which skills appear together most often. |
| **Evaluation** | Side-by-side comparison of the multi-agent pipeline vs. TF-IDF baseline across P@1, P@3, P@5, P@10, Kendall Tau, Spearman ρ, and silhouette scores. |

---

## Job Descriptions

The system includes 25 hand-crafted job descriptions across 10 IT categories:

### Senior / Mid-Level Roles (jd-001 to jd-018)
Java Developer, Python Developer, Web Developer, ETL Developer, Business Analyst, DBA, Network/Systems Admin, DevOps, Business Intelligence, and Recruiter — two roles per category.

### Intern Roles (jd-019 to jd-025) — Masters-relevant
| ID | Role | Company |
|---|---|---|
| jd-019 | Software Engineer Intern | Google |
| jd-020 | Software Developer Intern | Microsoft |
| jd-021 | AI/ML Engineer Intern | Meta |
| jd-022 | Backend Engineer Intern | ByteDance |
| jd-023 | Data Engineer Intern | Amazon |
| jd-024 | Frontend Developer Intern | Spotify |
| jd-025 | Cloud/DevOps Engineer Intern | IBM |

---

## Tech Stack

### Backend
- **Python 3.12**
- **FastAPI** + Uvicorn — REST API server
- **spaCy** (`en_core_web_sm`) — NLP for resume parsing
- **scikit-learn** — K-Means clustering, TF-IDF baseline, silhouette scoring
- **mlxtend** — Apriori association rule mining
- **pdfplumber** — PDF text extraction
- **pytesseract** + **Pillow** — OCR for image resume input
- **scipy** — Kendall Tau, Spearman correlation

### Frontend (pre-built static)
- **React** + **TypeScript** + **Vite**
- **Tailwind CSS**
- **Recharts** — data visualizations
- **React Query** — API state management

---

## Project Structure

```
skillmatch-ai/
├── career-system/
│   └── backend/
│       ├── api.py                    # FastAPI app + static frontend serving
│       ├── agent_resume_parser.py    # Agent 1: resume parsing
│       ├── agent_role_matcher.py     # Agent 2: role matching
│       ├── agent_skill_normalizer.py # Skill normalization utilities
│       ├── gap_scoring.py            # Agent 3: skill gap scoring
│       ├── job_descriptions.py       # All 25 JDs + save/load helpers
│       ├── job_descriptions.json     # Pre-serialized JDs
│       ├── skill_dictionary.py       # 341-skill lookup dictionary
│       ├── skills_dictionary.json    # Pre-serialized skill dict
│       ├── clustering.py             # K-Means + hierarchical clustering
│       ├── association_rules.py      # Apriori rule mining
│       ├── baseline.py               # TF-IDF baseline matcher
│       ├── evaluation.py             # Evaluation metrics (P@K, Tau, ρ)
│       ├── preprocessing.py          # Text cleaning + section segmentation
│       ├── pipeline.py               # End-to-end pipeline runner
│       ├── config.py                 # Paths and constants
│       └── results/                  # Pre-computed JSON results
│           ├── clustering.json
│           ├── association_rules.json
│           ├── evaluation.json
│           ├── matching_results.json
│           ├── gap_scores.json
│           ├── pipeline_summary.json
│           └── baseline_results.json
├── career-app/
│   ├── client/src/pages/
│   │   └── analyze.tsx               # Resume Analyzer page (PDF/image/text)
│   └── server/
│       └── routes.ts                 # Express proxy routes
└── career-app-static/                # Pre-built frontend (deploy as-is)
    ├── index.html
    └── assets/
        ├── index-DSsGtbA1.js
        └── index-DTtYguQY.css
```

---

## Running Locally

### Prerequisites

**Python 3.12+** is required.

```bash
# Install Tesseract OCR (for image resume support)
sudo apt-get install tesseract-ocr      # Ubuntu/Debian
brew install tesseract                  # macOS

# Install all Python dependencies
pip install -r requirements.txt

# Download the spaCy English model
python -m spacy download en_core_web_sm
```

### Start the Backend

```bash
cd career-system/backend
python api.py
# Server starts on http://localhost:5000
```

The FastAPI server:
- Serves the REST API at `/api/*`
- Serves the static frontend at `/`
- Strips the `/port/5000` prefix automatically for hosted environments

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/parse-resume` | Parse resume text → skills, education, experience |
| `POST` | `/api/parse-resume-pdf` | Parse PDF or image file upload |
| `POST` | `/api/match-roles` | Match skill list against JDs, return top-K |
| `POST` | `/api/skill-gap` | Compute skill gap for a target JD |
| `GET` | `/api/job-descriptions` | List all 25 JDs |
| `GET` | `/api/clusters` | K-Means cluster results + labels |
| `GET` | `/api/association-rules` | Apriori rule mining results |
| `GET` | `/api/evaluation` | Pipeline evaluation metrics |
| `GET` | `/api/health` | Health check |

---

## Evaluation Results

The multi-agent pipeline outperforms the TF-IDF baseline on all Precision@K metrics:

| Metric | Multi-Agent | TF-IDF Baseline | Δ |
|---|---|---|---|
| P@1 | **0.270** | 0.232 | +16.4% |
| P@3 | **0.249** | 0.200 | +24.5% |
| P@5 | **0.227** | 0.164 | +38.4% |
| P@10 | **0.164** | 0.121 | +35.5% |
| Kendall Tau | 0.413 | — | — |
| Spearman ρ | 0.519 | — | — |
| K-Means Silhouette | 0.245 | — | — |

Gap validation: recommended skills show ~25% improvement vs. ~2.8% for random skills — a **9× improvement ratio**.

---

## Dataset

The system was trained and evaluated on the [Kaggle Resume Dataset](https://www.kaggle.com/datasets/gauravduttakiit/resume-dataset) containing 9,000+ resumes across 25 job categories. K-Means clustering reduced these to 9 meaningful skill-based clusters.

---

## Team

**Group 36 — CSE-572 Data Mining, Spring 2026**
Arizona State University

- Bharanidharan Maheswaran
- Vineeth
- Karthikeyan
- Deepti

---

## License

This project is for academic purposes as part of the CSE-572 course at Arizona State University.
