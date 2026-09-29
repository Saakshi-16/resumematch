"""
The API endpoints. React calls these URLs and Django replies with JSON.
"""
import csv
import json
import traceback
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rag import embedder, evaluation, llm, pipeline, store
from rag.chat import answer

MAX_FILE_MB = 5


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


def health(request):
    return JsonResponse({
        "status": "ok",
        "llm_configured": llm.configured(),
        "llm_model": settings.GEMINI_MODEL,
        "retrieval": embedder.status(),
        "embedding_model": settings.EMBEDDING_MODEL,
    })


@csrf_exempt
def login(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST"}, status=405)
    body = _json_body(request)
    username = str(body.get("username", "")).strip()
    password = str(body.get("password", "")).strip()
    with open(settings.BASE_DIR / "data" / "users.csv", newline="", encoding="utf-8") as f:
        for user in csv.DictReader(f):
            if user["username"] == username and user["password"] == password:
                return JsonResponse({"success": True, "username": username, "full_name": user["full_name"]})
    return JsonResponse({"success": False, "error": "Wrong username or password"}, status=401)


@csrf_exempt
def analyze(request):
    """Accepts: resume (file) + either jd_file (file) or jd_text (text). Or use_sample=1."""
    if request.method != "POST":
        return JsonResponse({"error": "Use POST"}, status=405)
    try:
        if request.POST.get("use_sample") == "1":
            (rn, rb), (jn, jb) = pipeline.sample_files()
        else:
            resume = request.FILES.get("resume")
            if not resume:
                return JsonResponse({"error": "Please upload your resume."}, status=400)
            if resume.size > MAX_FILE_MB * 1024 * 1024:
                return JsonResponse({"error": f"Resume must be smaller than {MAX_FILE_MB} MB."}, status=400)
            rn, rb = resume.name, resume.read()

            jd_file = request.FILES.get("jd_file")
            jd_text = (request.POST.get("jd_text") or "").strip()
            if jd_file:
                jn, jb = jd_file.name, jd_file.read()
            elif len(jd_text) >= 50:
                jn, jb = "job_description.txt", jd_text.encode("utf-8")
            else:
                return JsonResponse({"error": "Please paste the job description (at least a few lines) or upload it."}, status=400)

        meta = pipeline.analyze(rn, rb, jn, jb)
        return JsonResponse(_public(meta))
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        return JsonResponse({"error": f"Something went wrong while analyzing: {e}"}, status=500)


def _public(meta):
    return {k: meta[k] for k in ("id", "resume_name", "jd_name", "resume_chunks", "jd_chunks", "report")}


def analysis(request, analysis_id):
    try:
        meta, _ = store.load(analysis_id)
    except KeyError:
        return JsonResponse({"error": "Analysis not found. Please run a new analysis."}, status=404)
    return JsonResponse(_public(meta))


@csrf_exempt
def chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST"}, status=405)
    body = _json_body(request)
    question = str(body.get("question", "")).strip()
    if not question:
        return JsonResponse({"error": "Please type a question."}, status=400)
    try:
        meta, index = store.load(str(body.get("analysis_id", "")))
    except KeyError:
        return JsonResponse({"error": "Analysis not found. Please run a new analysis first."}, status=404)
    return JsonResponse(answer(index, question[:1000], body.get("history", []), report=meta.get("report")))


@csrf_exempt
def evaluate(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST"}, status=405)
    return JsonResponse(evaluation.run())


def react_app(request):
    index_file = Path(settings.FRONTEND_DIST) / "index.html"
    if index_file.exists():
        return HttpResponse(index_file.read_text(encoding="utf-8"))
    return HttpResponse(
        "<h2>ResumeMatch backend is running.</h2><p>During development open "
        "<a href='http://localhost:5173'>http://localhost:5173</a>.</p>"
    )
