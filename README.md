# 📄 RFP Eligibility Checker using RAG (Retrieval-Augmented Generation)

This intelligent tool evaluates a vendor’s eligibility for an RFP (Request for Proposal) using **Retrieval-Augmented Generation (RAG)**. It parses and compares both the RFP and vendor/company profile documents, checks for alignment, computes similarity, and generates a structured eligibility report in JSON and PDF formats.

---

## ✅ Key Features

- 🔍 Upload both RFP and Company Profile documents (PDF/DOCX)
- 🧠 Uses vector similarity + LLM (RAG) to compare requirements and qualifications
- 📊 Computes technical match, requirement coverage, and eligibility score
- 📑 Generates downloadable **PDF/JSON eligibility reports**
- 🌐 Web interface built with **Flask**
- 🧠 Fallback to similarity matching if the LLM API fails

---

## 🧰 Tech Stack

| Component            | Technology                           |
|----------------------|--------------------------------------|
| Backend Framework    | Flask + Werkzeug                     |
| Vector Store         | ChromaDB                             |
| Embedding Models     | SentenceTransformers / Groq Embedding |
| LLM Interface        | Groq API (Mixtral) or fallback       |
| PDF Parsing          | PyMuPDF, PyPDF2                      |
| Report Generation    | PDFKit + Jinja2                      |
| Async Processing     | asyncio                              |

---


## 🚀 How It Works

1. 🗂️ Upload **RFP** and **Company Profile** files via `/api/upload` or web UI.
2. 📖 RFP is chunked and embedded using SentenceTransformers into ChromaDB.
3. 🧾 Company profile is also embedded and matched against RFP chunks.
4. 🧠 RAG pipeline (LLM + retrieved context) is used to analyze alignment.
5. 🧮 Technical match score, coverage %, and eligibility flag are computed.
6. 🧾 A report is generated with matching excerpts, scores, and justification.

---

### Clone the Repository

```bash
git clone https://github.com/your-username/rfp-eligibility-rag.git
cd rfp-eligibility-rag
```

### Install Requirements 
```bash
pip install -r requirements.txt
