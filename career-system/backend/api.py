"""
api.py – FastAPI application exposing REST endpoints for the web UI.

Loads pre-computed models/results from ``results/`` on startup and serves:
  - POST /api/parse-resume
  - POST /api/match-roles
  - POST /api/skill-gap
  - GET  /api/clusters
  - GET  /api/evaluation
  - GET  /api/job-descriptions
  - GET  /api/association-rules/{cluster_id}

Run with:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import RESULTS_DIR, PARAMS
from skill_dictionary import SkillLookup, load_dictionary
from job_descriptions import load_job_descriptions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

# ── FastAPI app ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="Intelligent Multi-Agent Career Page System",
    description="CSE-572 ASU – Automated Role Matching & Skill Gap Mining",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Strip /port/5000 prefix so the built frontend works when accessed directly
class StripPortPrefixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.scope.get("path", "")
        if path.startswith("/port/5000"):
            request.scope["path"] = path[len("/port/5000"):] or "/"
        return await call_next(request)


app.add_middleware(StripPortPrefixMiddleware)

# ── Startup: load pre-computed data ─────────────────────────────────────────

_state: Dict[str, Any] = {}


@app.on_event("startup")
def load_state() -> None:
    """Load pre-computed results into memory."""
    logger.info("Loading pre-computed results …")

    # Skill lookup
    _state["skill_lookup"] = SkillLookup()

    # Job descriptions
    _state["jds"] = load_job_descriptions()

    # Clustering
    clust_path = RESULTS_DIR / "clustering.json"
    if clust_path.exists():
        with open(clust_path) as f:
            _state["clustering"] = json.load(f)
        logger.info("  Loaded clustering results")
    else:
        _state["clustering"] = None
        logger.warning("  clustering.json not found – run pipeline first")

    # Association rules
    rules_path = RESULTS_DIR / "association_rules.json"
    if rules_path.exists():
        with open(rules_path) as f:
            _state["rules"] = json.load(f)
        logger.info("  Loaded association rules")
    else:
        _state["rules"] = None

    # Evaluation
    eval_path = RESULTS_DIR / "evaluation.json"
    if eval_path.exists():
        with open(eval_path) as f:
            _state["evaluation"] = json.load(f)
        logger.info("  Loaded evaluation results")
    else:
        _state["evaluation"] = None

    # Pipeline summary
    summary_path = RESULTS_DIR / "pipeline_summary.json"
    if summary_path.exists():
        with open(summary_path) as f:
            _state["summary"] = json.load(f)
    else:
        _state["summary"] = None

    logger.info("Startup complete.")


# ── Request / response models ──────────────────────────────────────────────


class ResumeTextRequest(BaseModel):
    text: str


class MatchRolesRequest(BaseModel):
    skills: List[str]
    top_k: int = 10


class SkillGapRequest(BaseModel):
    skills: List[str]
    target_jd_id: str


# ── Endpoints ──────────────────────────────────────────────────────────────


@app.post("/api/parse-resume")
def parse_resume(req: ResumeTextRequest) -> Dict[str, Any]:
    """Upload resume text → parsed + normalised skills."""
    from preprocessing import preprocess_single
    from agent_resume_parser import ResumeParser
    from agent_skill_normalizer import SkillNormalizer

    pre = preprocess_single(req.text)
    parser = ResumeParser(_state["skill_lookup"])
    parsed = parser.parse(pre)

    normalizer = SkillNormalizer(_state["skill_lookup"])
    normed = normalizer.normalize(parsed)

    return {
        "skills": normed["normalized_skills"],
        "skill_scores": normed["skill_scores"],
        "skill_categories": normed["skill_categories"],
        "years_experience": normed.get("years_experience"),
        "education_level": normed.get("education_level", "Unknown"),
        "job_titles_mentioned": normed.get("job_titles_mentioned", []),
        "sections_found": list(pre.get("sections", {}).keys()),
    }


_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def _extract_text_from_file(filename: str, contents: bytes) -> str:
    """Extract text from a PDF or image file."""
    import io
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == ".pdf":
        import pdfplumber
        try:
            with pdfplumber.open(io.BytesIO(contents)) as pdf:
                pages_text = [page.extract_text() or "" for page in pdf.pages]
            return "\n".join(pages_text).strip()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}")

    elif ext in _IMAGE_EXTENSIONS:
        from PIL import Image
        import pytesseract
        try:
            img = Image.open(io.BytesIO(contents))
            # Convert to RGB if needed (e.g. RGBA PNGs)
            if img.mode not in ("L", "RGB"):
                img = img.convert("RGB")
            text = pytesseract.image_to_string(img)
            return text.strip()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not read image: {e}")

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Upload a PDF or image (JPG, PNG).",
        )


@app.post("/api/parse-resume-pdf")
async def parse_resume_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload a PDF or image file → extract text → parsed + normalised skills."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    contents = await file.read()
    text = _extract_text_from_file(file.filename, contents)

    if not text:
        raise HTTPException(
            status_code=400,
            detail="No text could be extracted from the file.",
        )

    from preprocessing import preprocess_single
    from agent_resume_parser import ResumeParser
    from agent_skill_normalizer import SkillNormalizer

    pre = preprocess_single(text)
    parser = ResumeParser(_state["skill_lookup"])
    parsed = parser.parse(pre)

    normalizer = SkillNormalizer(_state["skill_lookup"])
    normed = normalizer.normalize(parsed)

    return {
        "skills": normed["normalized_skills"],
        "skill_scores": normed["skill_scores"],
        "skill_categories": normed["skill_categories"],
        "years_experience": normed.get("years_experience"),
        "education_level": normed.get("education_level", "Unknown"),
        "job_titles_mentioned": normed.get("job_titles_mentioned", []),
        "sections_found": list(pre.get("sections", {}).keys()),
        "extracted_text": text,
    }


@app.post("/api/match-roles")
def match_roles(req: MatchRolesRequest) -> Dict[str, Any]:
    """Given candidate skills, return ranked matching roles."""
    from agent_role_matcher import RoleMatcher

    # Build a synthetic candidate dict
    candidate = {
        "resume_id": -1,
        "normalized_skills": req.skills,
        "skill_scores": {s: 1.0 for s in req.skills},
    }

    cluster_profiles = None
    if _state.get("clustering"):
        cluster_profiles = _state["clustering"].get("cluster_profiles")

    matcher = RoleMatcher(
        job_descriptions=_state["jds"],
        cluster_profiles=cluster_profiles,
    )

    matches = matcher.match(candidate, top_k=req.top_k)
    return {"matches": matches}


@app.post("/api/skill-gap")
def skill_gap(req: SkillGapRequest) -> Dict[str, Any]:
    """Given candidate skills and a target JD, return gap analysis."""
    from gap_scoring import compute_gap

    # Find the target JD
    jd = None
    for j in _state["jds"]:
        if j["id"] == req.target_jd_id:
            jd = j
            break
    if jd is None:
        raise HTTPException(status_code=404, detail=f"JD '{req.target_jd_id}' not found")

    candidate = {
        "resume_id": -1,
        "normalized_skills": req.skills,
        "skill_scores": {s: 1.0 for s in req.skills},
    }

    # Use cluster 0 as default if no clustering data
    cluster_freq: Dict[str, float] = {}
    lift_idx: Dict[str, float] = {}

    if _state.get("clustering") and _state.get("rules"):
        # Pick cluster 0 as a reasonable default for ad-hoc queries
        cluster_id = 0
        rules_data = _state["rules"].get(str(cluster_id), {})
        from collections import defaultdict
        for rule in rules_data.get("rules", []):
            for s in rule.get("antecedents", []) + rule.get("consequents", []):
                lift_idx[s] = max(lift_idx.get(s, 0.0), rule.get("lift", 1.0))
    else:
        cluster_id = 0

    gap = compute_gap(candidate, jd, cluster_id, cluster_freq, lift_idx)
    return gap


# ── Skill-based cluster label generator ─────────────────────────────────────

# Map dominant skills to descriptive role-based cluster names
# Order matters: more specific patterns first to avoid ambiguous matches
_SKILL_ROLE_MAP = [
    ({"Informatica", "ETL", "Data Warehousing", "Teradata", "SSIS", "Talend"}, "Data Warehousing & ETL"),
    ({"SAP", "SAP BusinessObjects", "SAP HANA", "SAP ABAP"}, "SAP & Enterprise Systems"),
    ({"Java", "Spring", "Hibernate", "JSP", "Struts", "J2EE", "Servlets"}, "Java Development"),
    ({"CSS", "JavaScript", "HTML", "jQuery", "Angular", "React", "Bootstrap", "AJAX"}, "Frontend / Web Development"),
    ({"Cisco", "Active Directory", "VMware", "LAN/WAN", "VPN", "DNS", "DHCP"}, "Network & Systems Admin"),
    ({"PL/SQL", "TOAD", "Oracle", "Shell Scripting", "Unix"}, "Oracle DBA & Administration"),
    ({"Selenium", "QA", "Testing", "JUnit", "Automation", "Visual Basic"}, "QA & Test Engineering"),
    ({"SQL", "SQL Server", "Oracle", "Database", "MySQL", "Java", "Windows"}, "SQL & Application Development"),
    ({"Linux", "Shell Scripting", "Unix", "WebLogic", "Jenkins", "AWS", "Ansible"}, "DevOps & Linux Admin"),
    ({"Visio", "UML", "Agile", "SDLC", "JIRA", "Documentation", "Requirements", "Microsoft Teams"}, "Business Analysis & PM"),
    ({"Python", "Machine Learning", "TensorFlow", "Data Science", "R", "Pandas"}, "Data Science & ML"),
    ({"Recruiter", "Recruiting", "Talent Acquisition", "HR"}, "Recruiting & HR"),
]


def _generate_cluster_label(top_skills: List) -> str:
    """Generate a descriptive label from a cluster's top skills."""
    skill_names = {s[0] if isinstance(s, (list, tuple)) else s for s in top_skills[:10]}

    best_label = None
    best_overlap = 0
    for signature_skills, label in _SKILL_ROLE_MAP:
        overlap = len(skill_names & signature_skills)
        if overlap > best_overlap:
            best_overlap = overlap
            best_label = label

    if best_label and best_overlap >= 2:
        return best_label

    # Fallback: use top 2-3 skills as the label
    skill_list = [s[0] if isinstance(s, (list, tuple)) else s for s in top_skills[:3]]
    return " / ".join(skill_list)


@app.get("/api/clusters")
def get_clusters() -> Dict[str, Any]:
    """Return cluster info (labels, top skills, sizes)."""
    clust = _state.get("clustering")
    if clust is None:
        raise HTTPException(status_code=404, detail="Clustering results not available. Run pipeline first.")

    profiles = clust.get("cluster_profiles", {})
    summary = []
    for cid, prof in profiles.items():
        label = _generate_cluster_label(prof["top_skills"])
        summary.append({
            "cluster_id": int(cid),
            "label": label,
            "size": prof["size"],
            "top_skills": prof["top_skills"][:10],
            "category_distribution": prof.get("category_distribution", {}),
        })

    return {
        "n_clusters": clust.get("n_clusters"),
        "kmeans_silhouette": clust.get("kmeans_silhouette"),
        "hierarchical_silhouette": clust.get("hierarchical_silhouette"),
        "clusters": summary,
    }


@app.get("/api/evaluation")
def get_evaluation() -> Dict[str, Any]:
    """Return evaluation metrics."""
    ev = _state.get("evaluation")
    if ev is None:
        raise HTTPException(status_code=404, detail="Evaluation results not available. Run pipeline first.")
    return ev


@app.get("/api/job-descriptions")
def get_job_descriptions() -> List[Dict]:
    """Return all job descriptions."""
    return _state.get("jds", [])


@app.get("/api/association-rules/{cluster_id}")
def get_association_rules(cluster_id: int) -> Dict[str, Any]:
    """Return rules for a specific cluster."""
    rules = _state.get("rules")
    if rules is None:
        raise HTTPException(status_code=404, detail="Association rules not available. Run pipeline first.")

    cluster_rules = rules.get(str(cluster_id))
    if cluster_rules is None:
        raise HTTPException(status_code=404, detail=f"No rules for cluster {cluster_id}")

    return cluster_rules


@app.get("/api/health")
def health() -> Dict[str, str]:
    """Health check."""
    return {"status": "ok"}


# ── Serve the static frontend ───────────────────────────────────────────────

_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "career-app-static"

if _STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        """Serve the SPA frontend for any non-API route."""
        # Try to serve a real file first
        file_path = _STATIC_DIR / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        # Otherwise return index.html for SPA routing
        return FileResponse(str(_STATIC_DIR / "index.html"))


# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=5000, reload=False)
