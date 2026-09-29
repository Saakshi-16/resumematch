# 🎯 ResumeMatch: AI Resume vs Job Description Analyzer (RAG)

Upload a resume and a job description. ResumeMatch uses **Retrieval-Augmented Generation (RAG)** to check every job requirement against real evidence from the resume. It gives you a **match score**, **matched / partial / missing skills**, **improvement suggestions**, a **chat with citations**, and a **retrieval evaluation page**.

**Tech:** React · Django · Google Gemini · fastembed embeddings · BM25 hybrid search · Docker · AWS EC2

---

## Part 0: Understand what you built (read before your demo)

### RAG in one sentence
Instead of letting an AI guess, we first **retrieve** the most relevant pieces of the documents, ask the AI to **generate** a judgement using **only** those pieces, and then **verify** its claims.

### The pipeline (v2)

| # | Step | What happens | File |
|---|---|---|---|
| 1 | Load & repair | Extract text from PDF / DOCX / TXT and fix PDF letter-spacing ("F AISS" → "FAISS") | `rag/loaders.py` |
| 2 | Section-aware chunking | Detect headings (Experience, Projects, Skills…) and split into ~500-char overlapping chunks that never mix sections | `rag/chunker.py` |
| 3 | Embed | Each chunk → 384-number vector (`BAAI/bge-small-en-v1.5`, CPU) | `rag/embedder.py` |
| 4 | HyDE | The LLM imagines a resume line that would satisfy each requirement, and we search with it too | `rag/analyzer.py` |
| 5 | Hybrid search | BM25 keyword + semantic search for every query, merged with **Reciprocal Rank Fusion** | `rag/index.py` |
| 6 | Rerank | A **cross-encoder** (`ms-marco-MiniLM-L-6-v2`) re-scores the top 15 candidates | `rag/reranker.py` |
| 7 | Judge | Gemini labels each requirement match / partial / missing with an exact quote | `rag/analyzer.py` |
| 8 | Verify | Every quote is fuzzy-matched against the resume; unverifiable "matches" are downgraded (**hallucination check**) | `rag/grounding.py` |
| 9 | Score | Weighted score calculated in Python (must-have ×2, partial = 0.5) | `rag/analyzer.py` |
| 10 | Evaluate | **Ablation study** on hand-labelled gold data: Hit@1, Hit@3, MRR, nDCG@5 and judgement accuracy / macro-F1 / confusion matrix | `rag/evaluation.py` |

### Pages
- **Login**: demo accounts from `backend/data/users.csv`
- **Analyze**: upload a resume, then paste or upload a job description (or click *Try with sample*)
- **Report**: score, pipeline used, requirement-by-requirement evidence with section, ✓ verified badges and retrieved passages
- **Chat**: questions answered with citations [1] [2]; sources show section and reranker relevance
- **Evaluation**: ablation tables and the confusion matrix
- **How it works**: the pipeline explained

### Notebook
`notebooks/rag_walkthrough.ipynb` runs the **same code** step by step with visible outputs. Use it to study, and to show the implementation in your demo (Part 4b).

### Reliability features
- No reranker → skip stage 2. No embeddings → keyword search. No LLM → keyword skill analysis. The app never just crashes.
- The AI must quote evidence, and quotes are **verified** against the resume.
- The score is deterministic code, not an AI guess.

---

## Part 1: Put the project on your PC

1. Download `resumematch.zip`.
2. Right-click it → **Extract All…** → type `C:\projects` → **Extract**.
3. You should now have `C:\projects\resumematch` containing `backend`, `frontend`, `Dockerfile`, `README.md`, and so on.

---

## Part 2: Install the Python packages

You already have the `demoapp` Conda environment with Python 3.11 and Node 20, so we'll reuse it.

Open **Anaconda Prompt**:
```
conda activate demoapp
cd /d C:\projects\resumematch\backend
pip install -r requirements.txt
```
This takes 3–8 minutes. It's finished when you see `Successfully installed ...`.

---

## Part 3: Add your Gemini API key

1. Get a free key at <https://aistudio.google.com/apikey> → **Create API key** → copy it (it starts with `AIza`).
2. Open VS Code → **File → Open Folder** → `C:\projects\resumematch`.
3. In the left panel, right-click the **backend** folder → **New File** → name it exactly `.env` (with the dot at the start).
4. Paste this into it, using your real key, with no spaces or quotes:
   ```
   GEMINI_API_KEY=AIzaSyYOUR_REAL_KEY_HERE
   GEMINI_MODEL=gemini-3.5-flash-lite
   ```
5. Save with **Ctrl + S**.
6. Test the key in Anaconda Prompt (still inside the `backend` folder):
   ```
   python check_gemini.py
   ```
   You want to see `✅ Success! Gemini replied: Gemini is working`.
   - If it says the **model is not found**: change `GEMINI_MODEL` in `.env` to `gemini-3.8-flash` (or `gemini-3.1-flash-lite`), save, and run the check again.

> 🔒 **Never upload `.env` to GitHub or share your key.** The project's `.gitignore` already excludes it.

---

## Part 4: Run it on your PC

Same as your first project: two Anaconda Prompt windows.

**Window 1: Django**
```
conda activate demoapp
cd /d C:\projects\resumematch\backend
python manage.py runserver
```

**Window 2: React**
```
conda activate demoapp
cd /d C:\projects\resumematch\frontend
npm install
npm run dev
```

Open <http://localhost:5173> and log in with `admin` / `admin123`.

### Test everything
1. On **Analyze**, click **Try with sample resume & job**.
   - ⏳ **The first time takes 1–3 minutes**, because the embedding model (~130 MB) and the reranker (~80 MB) download once. After that, it takes 10–30 seconds.
2. **Report**: you should see a score, requirements with evidence quotes, and suggestions. The chips at the top should show all 6 pipeline steps (none crossed out), and under the score you should see **evidence verified %**.
3. **Chat**: click a suggested question, then click **Show sources**.
4. **Evaluation**: click **Run evaluation** (10–40 seconds). You should see tables A and B with 5 and 4 rows, plus part C with accuracy and the confusion matrix.
5. Go back to **Analyze** and try **your own resume** (PDF/DOCX) plus a real job description copied from LinkedIn or Naukri.

If you see a yellow warning *"No Gemini API key configured"*, the `.env` file is missing or in the wrong folder. It must be inside `backend`. Restart Window 1 after fixing it.

---

## Part 4b: Run the step-by-step notebook in VS Code

1. Install the Jupyter support (Anaconda Prompt, one time):
   ```
   conda activate demoapp
   pip install ipykernel
   ```
2. In VS Code, install the extensions **Python** and **Jupyter** (Extensions icon on the left → search → Install).
3. Open `notebooks/rag_walkthrough.ipynb`.
4. Top-right, click **Select Kernel** → **Python Environments** → choose **demoapp**.
5. Click **Run All**. The first run downloads the models (1–2 minutes).
6. To use **your CV**, change `RESUME_FILE` in the second code cell to the full path of your PDF, e.g. `RESUME_FILE = r"C:\Users\YOU\Downloads\SAAKSHI_LOKHANDE_CV.pdf"`.

Steps 8 onwards need the Gemini key in `backend/.env`.

---

## Part 5: Upload to GitHub

1. **Extract `resumematch.zip` again** into `C:\projects\upload-copy`. This fresh copy has no `node_modules`, no `.env` and no model files.
2. On <https://github.com>: **+** → **New repository** → name `resumematch` → **Public** → **Create repository**.
3. Click **uploading an existing file**.
4. Open `C:\projects\upload-copy\resumematch`, press **Ctrl + A**, drag everything onto the page, wait for it to finish, then click **Commit changes**.
5. Check that `Dockerfile` appears in the top-level list of your repository.

> A public GitHub repo is also great for your resume. Just make sure `.env` is **not** in it.

---

## Part 6: Create the EC2 server

1. <https://console.aws.amazon.com> → region **Asia Pacific (Mumbai)** → search **EC2** → **Launch instance**.
2. Settings:
   - **Name:** `resumematch`
   - **OS:** Ubuntu Server 24.04 LTS
   - **Instance type:** `t3.micro` (free-tier eligible). Use `t3.small` if your account allows it, since it's faster.
   - **Key pair:** create one (`resumematch-key`, `.pem`) and keep the downloaded file safe.
   - **Network:** ✅ Allow SSH from Anywhere, ✅ Allow HTTP from the internet
   - **Storage:** change **8** to **20 GiB** (the AI libraries need space)
3. **Launch** → wait for **Running** + **2/2 checks passed** → copy the **Public IPv4 address**.

---

## Part 7: Deploy with Docker

Select the instance → **Connect** → **EC2 Instance Connect** → **Connect**. Then paste these blocks one at a time.

**1. Install Docker and Git**
```bash
sudo apt update
sudo apt install -y docker.io git
sudo systemctl enable --now docker
```

**2. Add 2 GB of swap memory** (prevents crashes on small servers)
```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
```

**3. Download your code** (replace `YOUR-USERNAME`)
```bash
git clone https://github.com/YOUR-USERNAME/resumematch.git
cd resumematch
ls
```
`ls` must show `Dockerfile`.

**4. Build** (5–15 minutes: it builds React, installs the AI libraries and downloads the embedding model)
```bash
sudo docker build -t resumematch .
```

**5. Run.** Paste your real key, and use the same `GEMINI_MODEL` that worked in `check_gemini.py`:
```bash
sudo docker run -d --name resumematch -p 80:8000 \
  -e GEMINI_API_KEY=AIzaSyYOUR_REAL_KEY_HERE \
  -e GEMINI_MODEL=gemini-3.5-flash-lite \
  -v resumematch_data:/app/storage \
  --restart always resumematch
```
- `-e` passes your key into the app without putting it in the code
- `-v resumematch_data:/app/storage` keeps saved analyses even if you rebuild

**6. Check**
```bash
sudo docker ps
curl http://localhost/api/health/
```
Look for `"llm_configured": true` and `"retrieval": "semantic + keyword (hybrid) + cross-encoder reranking"`.

### 🎉 Open `http://YOUR-PUBLIC-IP` in your browser
Type `http://`, not `https://`. The first analysis may take ~20 seconds while the model loads.

### Updating later
Upload the changed files to GitHub, then on EC2:
```bash
cd ~/resumematch && git pull
sudo docker stop resumematch && sudo docker rm resumematch
sudo docker build -t resumematch .
```
Then run the `docker run` command from step 5 again.

---

## Part 8: Troubleshooting

| Problem | Fix |
|---|---|
| `pip install` fails on `onnxruntime` / `fastembed` | Make sure `(demoapp)` is shown and `python --version` says 3.11. Then retry `pip install -r requirements.txt`. |
| Yellow "No Gemini API key" banner | `.env` must be at `backend\.env` (not `.env.txt`). Restart Django after creating it. In VS Code the file name must show as `.env`. |
| "Gemini model … was not found" | Change `GEMINI_MODEL` to `gemini-3.8-flash`, or check current names at <https://ai.google.dev/gemini-api/docs/models>. |
| "Gemini free-tier limit reached" | Wait 1 minute. The app still shows a keyword-based report meanwhile. |
| First analysis is very slow on PC | Normal: the embedding model downloads once (~130 MB). |
| Report says *Search: keyword* | The embedding model couldn't download (internet/firewall). Check Window 1 for `[embedder]` messages. |
| "No text found" for a PDF | It's a scanned image PDF. Use a text PDF or DOCX. |
| EC2 page doesn't open | Use `http://`. Check the security group has **HTTP port 80 from 0.0.0.0/0**. |
| `docker build` shows "Killed" or "no space left" | Add swap (step 2). Increase the disk to 20 GiB (EC2 → Volumes → Modify). |
| See server errors on EC2 | `sudo docker logs resumematch --tail 50` |
| Stop paying after the demo | EC2 → Instance state → **Stop** or **Terminate**. |

---

## Part 9: Your Thursday demo (7–10 minutes)

1. **Problem (30 s):** "Keyword ATS checkers miss meaning, and LLM-only checkers hallucinate skills. I built a RAG system that grounds every judgement in verified evidence."
2. **Live app (2 min):** open your **EC2 URL**, upload **your CV** plus a real JD, then show the pipeline chips, score, evidence quotes with ✓ verified, and "Show retrieved passages".
3. **Chat (1 min):** ask *"Which required skills are missing?"* and show the citations and sources.
4. **Implementation (3 min):** open the **notebook** and walk through: chunking table → embeddings → BM25 vs semantic → RRF → reranker → HyDE line → judgement table → hallucination check demo.
5. **Evaluation (1.5 min):** Evaluation page. "Each component's contribution is measured on hand-labelled data. Here's the ablation, here's judge accuracy vs gold labels."
6. **Engineering (30 s):** Docker, EC2, graceful fallbacks, API key kept out of the code.

### Questions you may be asked
- **Why RAG instead of sending the whole resume to the LLM?** Every verdict is tied to retrieved evidence that we can cite and verify, which reduces hallucination. Retrieval per requirement also keeps prompts focused.
- **Why hybrid search?** Embeddings catch meaning ("led a club" ≈ leadership). BM25 catches exact terms ("FAISS", "Kinesis"). RRF merges the rankings without needing to calibrate scores.
- **Bi-encoder vs cross-encoder?** A bi-encoder embeds query and document separately (fast, used over everything). A cross-encoder processes them together (accurate, slow), so we use it only on the top 15. This is a standard two-stage retrieval design.
- **What is HyDE and why here?** Hypothetical Document Embeddings: the LLM writes a fake answer-like document, and we search with it. JDs and resumes phrase the same skill differently, so a hypothetical resume line is closer to real resume text than the requirement is.
- **How do you detect hallucinations?** Every quoted piece of evidence is fuzzy-matched (difflib ratio ≥ 0.80) against the resume. If it isn't found, the verdict is flagged and "match" is downgraded to "partial". The grounding rate is reported.
- **How did you evaluate?** A hand-labelled gold set. Retrieval is measured with Hit@K, MRR and nDCG in an ablation (adding one component at a time). Judgement is measured with accuracy, macro-F1 and a confusion matrix against gold verdicts.
- **Limitations and next steps:** the gold set is small (a bigger labelled dataset is needed), LLM verdicts vary slightly between runs, and next steps would be fine-tuning the embedding model on resume–JD pairs, a vector database for many resumes, and recruiter mode (rank many candidates).
- **How is it different from your LLaMA RAG project?** That project focused on generation (LoRA fine-tuning, ROUGE/BERTScore). This one focuses on retrieval quality, grounding verification and production deployment.

### Resume bullet you can use
> **ResumeMatch: Evidence-grounded Resume–Job Matching with RAG** (React, Django, Gemini, fastembed, Docker, AWS EC2). Built a two-stage retrieval pipeline (BM25 + dense embeddings with reciprocal rank fusion, HyDE query expansion, cross-encoder reranking) over section-aware chunks; added fuzzy-match grounding verification to flag hallucinated evidence; evaluated via ablation on hand-labelled data (Hit@K, MRR, nDCG, macro-F1); containerized and deployed on AWS EC2.
