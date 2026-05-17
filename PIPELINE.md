# Pipeline Architecture & Data Flow

This document details the architectural layers and execution sequence of the **Lead Generation Automation Pipeline**.

---

## 🗺️ Visual Architecture Diagram

```mermaid
graph TD
    A[User Form Submission] --> B[Phase 1: Validation & Checkpoints]
    B -->|Check Keys & Files| C{All Credentials Set?}
    C -->|No| D[Halt & Yield Explicit Visual Error Panel]
    C -->|Yes| E[Phase 2: Web Scraping Engine]
    
    E -->|1. Try Asynchronous HTTPX| F[BeautifulSoup Parser]
    E -->|2. Failure Fallback| G[Headless Playwright Chromium]
    
    F & G -->|Extract HTML & Text| H[Phase 3: Multi-AI Orchestrator]
    
    H -->|Stage 1: Broad Sweep| I[Gemini 1.5 Pro Search Grounding]
    I -->|Map Digital Footprint| J[OpenAI GPT-4o Query Generator]
    J -->|Formulate Custom Prompts| K[Stage 2: Deep Sweeps Across 6 Verticals]
    K -->|Execute Grounding Sweeps| L[OpenAI GPT-4o Synthesis Engine]
    L -->|Format Consultancy Copy| M[Phase 4: Dual A4 PDF Compiler]
    
    M -->|Jinja2 Template Styles| N{WeasyPrint Available?}
    N -->|Yes| O[Render A4 PDF]
    N -->|No Fallback| P[Headless Playwright browser.pdf Printing]
    
    O & P -->|Generate A4 Vector PDF| Q[Phase 5: Database & Cloud Integrations]
    Q -->|Service Account Auth| R[Google Drive Uploader]
    Q -->|Service Account Auth| S[Google Sheets Logger]
    
    R -->|Generate Public Web Link| T[Phase 6: SMTP Email Delivery]
    S -->|Append Database Row Record| T
    
    T -->|Connect smtp.gmail.com:587| U[MIMEMultipart Gmail App Password Dispatch]
    U -->|Attachment Delivered| V[Complete success state yielded to UI]
```

---

## ⚙️ Detailed Pipeline Stages

### 🔒 Stage 1: Validation & Checkpoints
- **Operations**:
  - Loads configuration settings using Pydantic Settings in `config.py`.
  - Verifies presence of API credentials and Google service account files.
  - Automatically prepends standard web headers (e.g. `https://`) if missing.
- **Error Behavior**:
  - Halts processing instantly upon missing configuration.
  - Logs full tracebacks and yields explicit JSON events to the user interface.

### 🌐 Stage 2: Web Scraping Engine (`scraper.py`)
- **First Sweep (Static)**:
  - Invokes `httpx` asynchronously to pull homepage markup, parsing with `BeautifulSoup4` and `lxml`.
  - Crawls secondary subpages (e.g. `/about`, `/contact`, `/pricing`) if found.
- **Dynamic Fallback (Headless Browser)**:
  - If static requests are blocked (403/429/Cloudflare) or pages are Single Page Applications (SPAs), it spins up a **headless Playwright Chromium** instance.
  - Waits for document paint fonts and fetches dynamic content seamlessly.

### 🤖 Stage 3: Multi-AI Orchestration (`enrichment.py`)
- **Stage A (Broad Sweep)**:
  - Gemini 1.5 Pro uses **Google Search Grounding** to perform a broad sweep across the company name and domain, mapping their digital presence.
- **Stage B (Query Creation)**:
  - GPT-4o processes the scraped markup and Gemini footprint to generate targeted, hyper-specific queries for deep vertical analysis.
- **Stage C (Grounding Sweep)**:
  - Gemini executes these targeted search queries across **6 business verticals**:
    1. Executive Summary & Brand Identity
    2. Offerings & ICP profile
    3. Macro Industry Drivers
    4. Competitor Gap Analysis
    5. Brand & Social Presence
    6. Active Hiring & Growth Signals
- **Stage D (Consulting Synthesis)**:
  - GPT-4o acts as an Executive Consultant, consolidating all data streams to draft a premium, formal copy covering operational pain points, actionable recommendations, and closing calls-to-action.

### 📄 Stage 4: Dual A4 PDF Compiler (`pdf_generator.py`)
- **Layout Styling**:
  - Compiles report copy into a premium Jinja2 [templates/report.html](templates/report.html) using gold/navy print styling, full cover page bleeds, dynamic headers, and running page counters.
- **Rendering Fallback**:
  - Attempts to compile via `WeasyPrint` first.
  - If standard workstation headers (Cairo/Pango dependencies) are missing, it falls back to **headless Playwright**, waiting for fonts to load before printing an exact A4 vector PDF.

### ☁️ Stage 5: Cloud & Database Integrations
- **Google Drive (`drive_uploader.py`)**:
  - Uses GCP Service Account JSON to upload the vector PDF to the designated shared folder.
  - Updates permission settings to make it viewable by "anyone with the link", returning a web share URL.
- **Google Sheets Database (`sheets_logger.py`)**:
  - Appends log details in the next empty row of the Google Sheet, acting as the centralized pipeline ledger.

### ✉️ Stage 6: Gmail App Password SMTP Dispatch (`email_sender.py`)
- **Message Assembly**:
  - Uses standard Python `email` packages to assemble a rich HTML email container.
  - Encodes the generated PDF as a MIME base64 attachment.
- **Transmission**:
  - Connects to Google's SMTP server `smtp.gmail.com:587` over a secure TLS session.
  - Uses your Gmail App Password to instantly dispatch the email, bypassing external SDK fees.
