# SimplifIQ — Automated Lead Intelligence Pipeline

SimplifIQ is a premium, fully automated business intelligence and lead enrichment platform. When a prospect submits a lead, the system automatically scrapes their website, performs a broad multi-agent AI research sweep (using Gemini search grounding and OpenAI GPT-4o synthesis), compiles a professional A4 vector PDF report, and delivers it securely via Google Drive, Google Sheets, and Gmail SMTP.

---

## 🔗 Quick Guides

To help you get set up and understand the inner workings of SimplifIQ, we have prepared two highly detailed, premium guides:

*   ### [🔑 Setup & Onboarding Guide (ONBOARDING.md)](ONBOARDING.md)
    *Detailed step-by-step instructions on how to acquire and configure all required credentials: OpenAI keys, Gemini keys, Gmail App Passwords, GCP Service Account JSON keys, Google Drive Folder IDs, and Google Sheets Database IDs.*

*   ### [⚙️ Pipeline Architecture & Data Flow (PIPELINE.md)](PIPELINE.md)
    *A comprehensive deep-dive into the technical layers, data models, web scrapers, multi-AI grounding sweeps, dual-engine PDF compilers, and SMTP delivery pipelines (featuring a full Mermaid architecture diagram).*

---

## 📂 Project Structure

```
Lead-Generation-automation/
│
├── backend/
│   ├── main.py                  # FastAPI router, serving pages and NDJSON streams
│   ├── config.py                # Environment setting loader and validator
│   ├── models.py                # Pydantic schemas (LeadInput, EnrichedCompanyData)
│   ├── scraper.py               # Asynchronous HTTP & Playwright scraper fallback
│   ├── enrichment.py            # Orchestrator for Multi-AI pipeline (Gemini + OpenAI)
│   ├── pdf_generator.py         # Jinja2 rendering & Playwright PDF compile fallback
│   ├── drive_uploader.py        # Google Drive Service Account uploader
│   ├── sheets_logger.py         # Google Sheets Service Account database logger
│   ├── email_sender.py          # SMTP Gmail App Password delivery dispatch
│   │
│   └── utils/
│       ├── logger.py            # loguru formatted console & file logger
│       ├── retry.py             # tenacity exponential backoff decorators
│       └── fallbacks.py         # static fallback content for website blocks
│
├── frontend/
│   └── index.html               # Premium glassmorphic interface and stream visualizer
│
├── templates/
│   └── report.html              # Custom Jinja2 styling sheet template for PDF A4
│
├── outputs/                     # Local temporary storage for generated PDFs
├── credentials/                 # Put Google service_account.json here
├── logs/                        # Rolled pipeline log files
│
├── requirements.txt             # Core Python dependency pins
├── .env                         # Environment variables (API Keys)
│
├── ONBOARDING.md                # Credentials Retrieval Guide
├── PIPELINE.md                  # Pipeline Architecture Document
└── README.md                    # Main landing page
```

---

## 🛠️ Quick Installation

1. **Step 1: Create a local virtual environment and install packages**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Step 2: Setup your configurations**
   - Copy the placeholder `.env` and fill in your keys:
     ```env
     OPENAI_API_KEY=sk-proj-...
     GEMINI_API_KEY=AIzaSy...
     GMAIL_ADDRESS=you@gmail.com
     GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
     GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
     GOOGLE_SHEET_ID=your_sheets_id
     ```
   - Place your Google Service Account key in:
     `credentials/service_account.json`
   - Review [ONBOARDING.md](ONBOARDING.md) for full credential retrieval steps.

---

## 🚀 Running the Server

To boot up the local FastAPI server:
```bash
venv/bin/uvicorn backend.main:app --reload
```
Open your browser and navigate to: **[http://localhost:8000](http://localhost:8000)**.

---

## 🧪 Testing Diagnostics

We have set up an offline, local diagnostic script that validates settings, tests Pydantic validation, and runs the A4 layout compilation using Playwright PDF printer with custom mockup data.

To trigger the test:
```bash
venv/bin/python3 scratch/test_pipeline.py
```
*(Verify the generated vector PDF under `outputs/stripe_Intelligence_Report_*.pdf`!)*
