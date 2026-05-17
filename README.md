# SimplifIQ — Automated Lead Intelligence Pipeline

A fully automated business intelligence and lead enrichment pipeline. When a prospect submits a lead, the system:
1. Validates input values & active API credentials.
2. Performs a deep scrape on the company homepage and primary sub-pages.
3. Maps their digital footprint using a broad Gemini 1.5 Pro search sweep.
4. Generates customized, targeted research prompts using GPT-4o.
5. Executes deep search grounding sweeps across 6 core corporate verticals.
6. Synthesizes professional executive consult copy via GPT-4o.
7. Compiles the report layout into a gorgeous A4 vector PDF.
8. Uploads the report to a Google Drive folder with public share settings.
9. Database-logs the lead row in Google Sheets.
10. Delivers the PDF report as an email attachment and public link using Resend.

---

## 📂 Project Structure

```
Lead-Generation-automation/
│
├── backend/
│   ├── main.py                  # FastAPI router, serving pages and streams
│   ├── config.py                # Environment setting loader and validator
│   ├── models.py                # Pydantic schemas (LeadInput, EnrichedCompanyData)
│   ├── scraper.py               # Asynchronous HTTP & Playwright scraper fallback
│   ├── enrichment.py            # Orchestrator for Multi-AI pipeline (Gemini + OpenAI)
│   ├── pdf_generator.py         # Jinja2 rendering & Playwright PDF compile fallback
│   ├── drive_uploader.py        # Google Drive Service Account uploader
│   ├── sheets_logger.py         # Google Sheets Service Account database logger
│   ├── email_sender.py          # Resend attachment dispatch sender
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
├── credentials/                 # Put google service_account.json here
├── logs/                        # Rolled pipeline log files
│
├── requirements.txt             # Core python dependency pins
├── .env                         # Environment variables (API Keys)
└── README.md                    # This instructions guide
```

---

## 🛠️ Installation & Setup

1. **Step 1: Create local virtual environment and install packages**
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
     RESEND_API_KEY=re_...
     GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
     GOOGLE_SHEET_ID=your_sheets_id
     ```
   - Share your targeted Google Drive Folder and Google Sheet with your Google Service Account email as **Editor**.
   - Download the Service Account JSON key from your GCP console and save it under:
     `credentials/service_account.json`

---

## 🚀 Running the Pipeline

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
