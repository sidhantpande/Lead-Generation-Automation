# SimplifIQ Assessment — Complete Detailed Plan

---

## 1. SYSTEM OVERVIEW

A fully automated lead intelligence pipeline. When a prospect submits a form, the system:
1. Validates and stores their input
2. Researches their company using a multi-AI pipeline
3. Generates a personalized, professional PDF audit report
4. Uploads it to a specific Google Drive folder
5. Logs the lead + Drive link to a Google Sheet
6. Emails the prospect with the PDF attached + Drive link

Zero human intervention at any step.

---

## 2. COMPLETE TECH STACK

### Backend
| Tool | Purpose | Why |
|---|---|---|
| Python 3.11+ | Core language | Best library ecosystem for all requirements |
| FastAPI | Web framework | Async support, auto docs, clean routing |
| Uvicorn | ASGI server | Runs FastAPI |
| python-dotenv | Env variable management | Load .env cleanly |
| pydantic | Data validation | Validate form input with clear error messages |

### AI Layer
| Tool | Purpose | Why |
|---|---|---|
| OpenAI `gpt-4o` | Orchestrator + synthesizer | Best reasoning for planning + PDF content generation |
| Google `gemini-1.5-pro` | Research engine | Native google_search grounding, real-time web access |
| `openai` Python SDK | OpenAI API calls | Official SDK |
| `google-generativeai` | Gemini API calls | Official Google SDK |

### Scraping
| Tool | Purpose | Why |
|---|---|---|
| `requests` | HTTP requests to websites | Lightweight, fast |
| `BeautifulSoup4` | HTML parsing | Extract clean text from pages |
| `playwright` | JS-heavy site fallback | Headless browser when BS4 fails |
| `lxml` | HTML parser for BS4 | Faster than html.parser |

### PDF Generation
| Tool | Purpose | Why |
|---|---|---|
| `WeasyPrint` | HTML/CSS → PDF | Lets us style the report with CSS, looks premium |
| `Jinja2` | HTML templating | Dynamic content injection into report.html |
| `Pillow` | Image handling (logo fetch/resize) | Process company logos if fetchable |

### Google Services
| Tool | Purpose | Why |
|---|---|---|
| `google-api-python-client` | Drive + Sheets API | Official Google client library |
| `google-auth` | Service account auth | Server-side auth, no OAuth user flow needed |
| `google-auth-httplib2` | HTTP transport for auth | Required by google-api-python-client |

### Email
| Tool | Purpose | Why |
|---|---|---|
| `resend` Python SDK | Send email with PDF attachment | Clean API, reliable delivery |

### Utilities
| Tool | Purpose |
|---|---|
| `httpx` | Async HTTP (backup for requests) |
| `python-slugify` | Clean filenames for PDFs |
| `loguru` | Clean structured logging |
| `tenacity` | Retry logic for API calls |

---

## 3. COMPLETE PROJECT STRUCTURE

```
simplifiq-assessment/
│
├── backend/
│   ├── main.py                  # FastAPI app entry point, all routes
│   ├── config.py                # All env variables, loaded once
│   ├── models.py                # Pydantic models for form input + internal data
│   │
│   ├── scraper.py               # Website scraping (BS4 primary, Playwright fallback)
│   ├── enrichment.py            # Full multi-AI pipeline (Gemini → OpenAI → Gemini → OpenAI)
│   ├── pdf_generator.py         # Jinja2 rendering + WeasyPrint PDF export
│   ├── drive_uploader.py        # Google Drive API — upload + get shareable link
│   ├── sheets_logger.py         # Google Sheets API — append lead row
│   ├── email_sender.py          # Resend — send email with PDF attached + Drive link
│   │
│   └── utils/
│       ├── logger.py            # Loguru setup
│       ├── retry.py             # Tenacity retry wrappers for API calls
│       └── fallbacks.py        # Default content if any step fails
│
├── frontend/
│   └── index.html               # Lead capture form (standalone HTML/CSS/JS)
│
├── templates/
│   └── report.html              # Jinja2 HTML template for PDF (all CSS inside)
│
├── outputs/                     # Temp folder — generated PDFs saved here before upload
│   └── .gitkeep
│
├── credentials/
│   └── service_account.json     # Google Service Account key (never commit this)
│
├── .env                         # All API keys and config
├── .env.example                 # Template .env with placeholder values (commit this)
├── .gitignore                   # Excludes .env, credentials/, outputs/
├── requirements.txt             # All Python dependencies pinned
└── README.md                    # Full setup instructions + architecture explanation
```

---

## 4. FORM FIELDS (frontend/index.html)

### Required Fields
| Field | Input Type | Validation |
|---|---|---|
| Full Name | text | Non-empty, min 2 chars |
| Work Email | email | Valid email format |
| Company Name | text | Non-empty |
| Company Website | url | Valid URL format, must start with http/https |

### Optional Fields
| Field | Input Type | Note |
|---|---|---|
| LinkedIn Company URL | url | linkedin.com URL |
| Instagram Handle | text | With or without @ |
| Industry | dropdown | 15-20 common options + "Other" |
| Company Size | dropdown | 1-10 / 11-50 / 51-200 / 200+ |
| Additional Context | textarea | Any extra info they want to share |

### Industry Dropdown Options
- SaaS / Software
- Finance & Fintech
- Consulting & Advisory
- E-commerce & Retail
- Healthcare
- Education / EdTech
- Real Estate
- Marketing & Advertising
- Manufacturing
- Legal Services
- Logistics & Supply Chain
- Media & Entertainment
- Non-Profit
- Other

---

## 5. ENVIRONMENT VARIABLES (.env)

```env
# OpenAI
OPENAI_API_KEY=sk-...

# Gemini
GEMINI_API_KEY=AIza...

# Resend
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=reports@yourdomain.com
RESEND_FROM_NAME=SimplifIQ Intelligence

# Google
GOOGLE_SERVICE_ACCOUNT_PATH=credentials/service_account.json
GOOGLE_DRIVE_FOLDER_ID=1aBcDeFgHiJkLmNoPqRsTu   # ID from Drive folder URL
GOOGLE_SHEET_ID=1aBcDeFgHiJkLmNoPqRsTu            # ID from Sheets URL

# App
APP_HOST=0.0.0.0
APP_PORT=8000
OUTPUT_DIR=outputs
```

---

## 6. DATA MODELS (backend/models.py)

### LeadInput — what the form sends
```
- name: str
- email: EmailStr
- company_name: str
- website: HttpUrl
- linkedin_url: Optional[str]
- instagram_handle: Optional[str]
- industry: Optional[str]
- company_size: Optional[str]
- additional_context: Optional[str]
```

### EnrichedCompanyData — output of the full AI pipeline
```
- company_overview: str
- industry_landscape: str
- competitor_analysis: str
- product_service_summary: str
- social_media_presence: str
- recent_news: str
- growth_signals: str
- pain_points: list[str]        # 3-5 specific pain points
- recommendations: list[str]    # 3-5 specific recommendations
- executive_summary: str        # OpenAI-generated summary paragraph
```

### LeadRecord — what gets logged to Sheets
```
- timestamp: str
- name: str
- email: str
- company_name: str
- website: str
- linkedin_url: str
- instagram_handle: str
- report_status: str            # "success" | "partial" | "failed"
- drive_pdf_link: str
```

---

## 7. THE COMPLETE AI PIPELINE (backend/enrichment.py)

### Step 1 — Gemini Broad Sweep (Pass 1)

**What it does:** Gets a general picture of the company from across the web.

**Input to Gemini:**
```
"Research the company '{company_name}' with website {website}.
Find: what they do, their core product/service, their target customers,
their founding story if available, and their general online presence.
Also check {linkedin_url} and Instagram @{handle} if provided.
Return a comprehensive overview."
```

**Gemini config:**
- Model: `gemini-1.5-pro`
- Tool: `google_search` enabled
- Temperature: 0.3 (factual, not creative)

**Output:** Raw text blob — broad company overview from the web.

---

### Step 2 — Traditional Website Scrape

**What it does:** Pulls actual content directly from their website.

**Pages to scrape (in order):**
1. Homepage (/)
2. /about or /about-us
3. /services or /solutions or /products
4. /team (if exists)

**Process:**
```
requests.get(url, timeout=10, headers={User-Agent: ...})
→ BeautifulSoup(html, 'lxml')
→ Remove: script, style, nav, footer, header tags
→ Extract: all <p>, <h1>-<h4>, <li> text
→ Clean: strip whitespace, remove duplicates
→ Limit: first 3000 words to avoid token overflow
```

**Playwright fallback:**
- Triggered if requests returns 403, 429, or JS-rendered blank page
- Launches headless Chromium
- Waits for page load, then extracts text
- Times out after 15 seconds

**Failure fallback:**
- If both fail → set `scraped_text = "Website scraping failed. Using external research only."`
- Pipeline continues, never breaks

---

### Step 3 — OpenAI Analysis + Prompt Generation

**What it does:** Analyzes all data collected so far and generates precise, targeted research prompts for Gemini's second pass.

**Input to OpenAI (gpt-4o):**
```
System: "You are a business intelligence analyst. Your job is to analyze 
company data and generate precise research prompts that will be used to 
gather deep intelligence about this company."

User: 
- Company Form Data: {all form fields}
- Gemini Broad Research: {step 1 output}
- Website Scraped Content: {step 2 output}

Generate exactly 6 targeted research prompts, one per category, 
returned as a JSON object with these keys:
{
  "industry_landscape": "...",
  "competitor_analysis": "...", 
  "social_media_strategy": "...",
  "recent_news_funding": "...",
  "growth_signals_hiring": "...",
  "pain_points_challenges": "..."
}
Each prompt should be specific to THIS company, not generic.
```

**Output:** JSON with 6 targeted prompts, each specific to the company.

---

### Step 4 — Gemini Deep Research (Pass 2)

**What it does:** Executes each of the 6 prompts from Step 3, filling each research category.

**Process:**
- Loop through each of the 6 prompts
- Send each to Gemini with `google_search` enabled
- Collect response per category
- Store as dict: `{ "industry_landscape": "...", "competitor_analysis": "...", ... }`

**Error handling per prompt:**
- If one prompt fails → use fallback: `"Insufficient data available for this category."`
- Never stop the pipeline for a single failed prompt
- Log which categories succeeded/failed

**Total Gemini calls in Pass 2:** 6

---

### Step 5 — OpenAI PDF Content Synthesis

**What it does:** Takes ALL collected data and produces the final, structured report content section by section.

**Input to OpenAI (gpt-4o):**
```
System: "You are a senior business consultant writing a premium intelligence 
report for {company_name}. The report must feel deeply personalized — 
not generic. Use specific facts, names, numbers wherever available. 
Tone: authoritative, insightful, forward-looking."

User:
- All form data
- Gemini broad research (Step 1)
- Scraped website content (Step 2)  
- All 6 deep research categories (Step 4)

Generate the following sections as JSON:
{
  "executive_summary": "3-4 paragraph overview...",
  "company_profile": "...",
  "industry_landscape": "...",
  "competitive_positioning": "...",
  "social_media_analysis": "...",
  "growth_signals": "...",
  "pain_points": ["point 1", "point 2", "point 3", "point 4", "point 5"],
  "recommendations": [
    {"title": "...", "description": "..."},
    {"title": "...", "description": "..."},
    ...
  ],
  "closing_note": "..."
}
```

**Output:** Fully structured JSON — ready to inject into the PDF template.

---

## 8. PDF REPORT STRUCTURE (templates/report.html)

### Page 1 — Cover Page
- Company Name (large, prominent)
- "Business Intelligence Report" subtitle
- Company website
- Date generated
- "Prepared by SimplifIQ" branding
- Company logo (fetched from website favicon or clearbit logo API as fallback)
- Background: dark themed, premium feel

### Page 2 — Executive Summary
- 3-4 paragraph high-level overview
- Key stats bar (company size, industry, founded year if available)

### Page 3 — Company Profile
- What they do
- Core product/service
- Target customers
- Business model

### Page 4 — Industry & Market Landscape
- Industry overview
- Market trends relevant to them
- Where they sit in the market

### Page 5 — Competitive Positioning
- Who their competitors are
- How they differentiate (or should)
- Gaps in the market

### Page 6 — Social Media & Brand Presence
- LinkedIn analysis
- Instagram analysis
- Overall brand voice assessment

### Page 7 — Growth Signals & Opportunities
- Hiring trends
- Recent news / funding
- Expansion signals

### Page 8 — Identified Challenges
- 5 specific pain points (bullet format, each with brief explanation)

### Page 9 — Recommendations
- 5 specific recommendations (card format)
- Each: Title + 2-3 line description

### Page 10 — Closing Note + CTA
- Personalized closing paragraph
- "Book a call with SimplifIQ" CTA

### PDF Styling
- Font: Playfair Display (headings) + Source Sans Pro (body) via Google Fonts
- Colors: Deep navy + white + gold accent
- Each section starts on a new page
- Page numbers in footer
- SimplifIQ logo in header on every page after cover

---

## 9. GOOGLE DRIVE SETUP (backend/drive_uploader.py)

### Pre-requisites
1. Create a Google Cloud Project
2. Enable Google Drive API
3. Create a Service Account → download JSON key
4. Create a Drive folder → copy its ID from the URL
5. Share that Drive folder with the Service Account email (give Editor access)

### Upload Flow
```
1. Authenticate using service_account.json
2. Upload PDF file from outputs/ folder
3. Set file name: "{company_name}_Intelligence_Report_{date}.pdf"
4. Set parent folder: GOOGLE_DRIVE_FOLDER_ID
5. Set permission: "anyone with link can view"
6. Return: shareable webViewLink
```

### Output
- Returns a public shareable URL to the PDF
- This URL gets logged to Sheets and included in the email

---

## 10. GOOGLE SHEETS SETUP (backend/sheets_logger.py)

### Pre-requisites
1. Enable Google Sheets API on same Google Cloud Project
2. Same Service Account used for Drive
3. Create a Google Sheet → copy its ID from the URL
4. Share the Sheet with the Service Account email (Editor access)

### Sheet Structure
**Tab name:** `Lead Responses`

**Columns (Row 1 = headers):**
```
A: Timestamp
B: Full Name  
C: Email
D: Company Name
E: Website
F: LinkedIn
G: Instagram
H: Industry
I: Company Size
J: Report Status
K: Drive PDF Link
```

### Append Flow
```
1. Authenticate using service_account.json
2. Build row array with all lead data
3. Append to next empty row in "Lead Responses" tab
4. Report Status: "Success" / "Partial (some steps failed)" / "Failed"
```

---

## 11. EMAIL SETUP (backend/email_sender.py)

### Pre-requisites
- Resend account + API key
- Domain verified in Resend OR use their default sending domain

### Email Content

**Subject:** `Your {Company Name} Intelligence Report — Prepared by SimplifIQ`

**Body (HTML email):**
- Personalized greeting using their name
- 2-3 lines explaining the report
- Drive link as a button ("View Report Online")
- Note that PDF is also attached
- Professional SimplifIQ signature

**Attachment:**
- The generated PDF file
- File name: `{company_name}_Intelligence_Report.pdf`

---

## 12. FASTAPI ROUTES (backend/main.py)

```
GET  /               → Serves frontend/index.html
POST /api/submit     → Main pipeline trigger
GET  /health         → Health check (returns {"status": "ok"})
```

### POST /api/submit Flow
```python
1.  Receive form data → validate with Pydantic → return 422 if invalid
2.  Return 200 immediately with {"message": "Processing your report..."}
3.  Run pipeline in background task (FastAPI BackgroundTasks)
4.  Inside background task:
    a. Gemini Pass 1
    b. Scrape website
    c. OpenAI → generate prompts
    d. Gemini Pass 6x (deep research)
    e. OpenAI → synthesize PDF content
    f. Render HTML template with Jinja2
    g. WeasyPrint → generate PDF → save to outputs/
    h. Upload to Drive → get link
    i. Append to Google Sheets
    j. Send email with PDF + Drive link
    k. Clean up PDF from outputs/ folder
    l. Log final status
```

**Why background task?**
The full pipeline takes 30-60 seconds. We return 200 immediately so the form doesn't time out. The user gets an email when it's done.

---

## 13. ERROR HANDLING & FALLBACKS

| Step | Failure Scenario | Fallback |
|---|---|---|
| Form validation | Invalid email/URL | Return 422 with field-level errors |
| Website scrape (BS4) | 403, timeout, JS page | Try Playwright |
| Website scrape (Playwright) | Also fails | Set scraped_text = "N/A", continue |
| Gemini Pass 1 | API error | Use only form data + scrape for Step 3 |
| OpenAI prompt generation | API error | Use pre-written default prompts per category |
| Individual Gemini prompt (Pass 2) | Fails | That category = "Data unavailable", continue |
| OpenAI PDF synthesis | API error | Use template with whatever data was collected |
| PDF generation | WeasyPrint error | Log error, mark report_status = "Failed" |
| Drive upload | Auth error / quota | Log error, email without Drive link |
| Sheets logging | Any error | Log error, don't block email sending |
| Email sending | Resend error | Retry 3x with exponential backoff |

**Core principle:** No single failure kills the pipeline. Every step has a fallback. The email always attempts to send.

---

## 14. RETRY LOGIC (backend/utils/retry.py)

Using `tenacity`:
- All external API calls wrapped in retry decorator
- Max retries: 3
- Wait: exponential backoff (1s → 2s → 4s)
- Applied to: OpenAI calls, Gemini calls, Resend calls
- Drive and Sheets: 2 retries only

---

## 15. LOGGING (backend/utils/logger.py)

Using `loguru`:
```
[timestamp] [STEP 1] Gemini broad sweep started for: Acme Corp
[timestamp] [STEP 1] Gemini broad sweep completed (847 tokens)
[timestamp] [STEP 2] Scraping https://acme.com ...
[timestamp] [STEP 2] Scraped 2,341 words from 3 pages
[timestamp] [STEP 3] OpenAI prompt generation started
[timestamp] [STEP 3] 6 prompts generated successfully
[timestamp] [STEP 4] Gemini deep research — industry_landscape ✓
[timestamp] [STEP 4] Gemini deep research — competitor_analysis ✓
...
[timestamp] [STEP 5] PDF content synthesized (2,100 tokens)
[timestamp] [STEP 6] PDF generated: acme-corp-report-2025-05-17.pdf (1.2MB)
[timestamp] [STEP 7] Uploaded to Drive: https://drive.google.com/...
[timestamp] [STEP 8] Logged to Sheets ✓
[timestamp] [STEP 9] Email sent to contact@acme.com ✓
[timestamp] PIPELINE COMPLETE — Total time: 47s
```

---

## 16. README STRUCTURE

1. Project Overview (2-3 lines)
2. System Architecture (the pipeline diagram)
3. Tech Stack (table)
4. Prerequisites (what accounts/APIs needed)
5. Google Cloud Setup (step by step)
   - Create project
   - Enable Drive + Sheets APIs
   - Create Service Account
   - Share Drive folder + Sheet with Service Account
6. Environment Variables setup
7. Installation
   ```bash
   git clone ...
   cd simplifiq-assessment
   pip install -r requirements.txt
   playwright install chromium
   cp .env.example .env
   # Fill in .env values
   ```
8. Running the app
   ```bash
   uvicorn backend.main:app --reload
   # Open http://localhost:8000
   ```
9. Testing the pipeline
10. Assumptions & Tradeoffs
11. Known Limitations
12. Future Improvements

---

## 17. ASSUMPTIONS & TRADEOFFS (for README + interview)

**Assumptions:**
- Company website is publicly accessible
- Gemini's google_search grounding provides sufficient real-time data
- PDF is generated server-side (not client-side)
- Service Account is used for Google APIs (no user OAuth)

**Tradeoffs:**
- Multi-AI pipeline adds latency (~45-60s total) but significantly improves report quality vs single model
- WeasyPrint chosen over ReportLab for CSS-based styling — better visual output, slightly harder to install
- Background task means user doesn't see progress — acceptable for a prototype
- No database used — Sheets acts as the data store

**Limitations:**
- Very new companies or stealth startups may have minimal web presence
- Gemini search grounding is non-deterministic — same company may yield slightly different results each run
- Rate limits on all three APIs could bottleneck at high volume
- Playwright adds ~200MB to deployment size

---

## 18. IMPLEMENTATION ORDER (recommended)

```
Day 1
  1. Project scaffold + .env setup
  2. Pydantic models
  3. Frontend form (HTML)
  4. FastAPI routes + basic validation

Day 2
  5. Website scraper (BS4 + Playwright fallback)
  6. Gemini Pass 1 (broad sweep)
  7. OpenAI prompt generation

Day 3
  8. Gemini Pass 2 (deep research, all 6 categories)
  9. OpenAI PDF content synthesis

Day 4
  10. report.html template design
  11. WeasyPrint PDF generation
  12. Test full enrichment → PDF flow

Day 5
  13. Google Drive upload
  14. Google Sheets logging
  15. Resend email (attachment + link)
  16. End-to-end test

Day 6
  17. Error handling + fallbacks
  18. Retry logic
  19. Logging
  20. README
  21. Final polish
```

---

*Total estimated build time: 5-6 focused days*
*Assessment difficulty: Medium-High | Differentiator: Multi-AI pipeline + report quality*
