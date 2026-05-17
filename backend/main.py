import os
import json
import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from backend.config import settings
from backend.models import LeadInput
from backend.utils.logger import log_step, logger
from backend.scraper import scrape_website
from backend.enrichment import run_enrichment_pipeline
from backend.pdf_generator import generate_pdf_report
from backend.drive_uploader import upload_pdf_to_drive
from backend.sheets_logger import log_lead_to_sheets
from backend.email_sender import send_report_email

app = FastAPI(title="Lead Generation Automation Server", version="1.0.0")

# Setup folder directories
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
OUTPUTS_DIR = Path(__file__).parent.parent / settings.OUTPUT_DIR
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# 1. GET / - Serves Lead capture interface
@app.get("/")
async def serve_frontend():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html file not found in directory structure.")
    return FileResponse(index_file)

# 2. GET /health - Simple health checks
@app.get("/health")
async def health_check():
    missing_keys = settings.validate_setup()
    return {
        "status": "healthy" if not missing_keys else "incomplete_config",
        "missing_configurations": missing_keys
    }

# 3. GET /api/download/{filename} - Fetch generated PDF directly
@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = OUTPUTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Requested PDF file {filename} does not exist on the server.")
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )

# 4. POST /api/submit - Real-Time Streaming NDJSON Pipeline
@app.post("/api/submit")
async def submit_lead(lead: LeadInput):
    """
    POST lead capture inputs and streams back live pipeline execution status logs.
    """
    
    async def pipeline_generator():
        # Step tracking variables
        pdf_path = None
        drive_link = "#"
        
        # Helper to yield structured NDJSON events
        def yield_event(status: str, message: str, level: str = "info", **kwargs):
            event = {
                "status": status,
                "message": message,
                "level": level,
                "timestamp": datetime.now().isoformat(),
                **kwargs
            }
            return f"{json.dumps(event)}\n"

        logger.info(f"New pipeline connection request received for {lead.company_name} ({lead.email})")
        
        # ==========================================
        # STEP 0: Configuration Validation Checkpoint
        # ==========================================
        yield yield_event("running", "Step 0: Checking environment configurations and active API keys...", step_active=0)
        missing_configs = settings.validate_setup()
        
        if missing_configs:
            err_msg = f"Pipeline terminated: Configuration variables missing: {', '.join(missing_configs)}"
            logger.error(err_msg)
            yield yield_event("error", err_msg, level="error", step_failed=0)
            return

        yield yield_event("running", "All essential configuration requirements validated successfully.", level="success", step_completed=0, step_active=1)
        await asyncio.sleep(0.5)

        # ==========================================
        # STEP 1: Website Scraping
        # ==========================================
        yield yield_event("running", f"Step 1: Commencing scraping sequence for: {lead.website}")
        
        try:
            scraped_content = await scrape_website(lead.website)
            yield yield_event("running", "Website scraping complete. Text extraction finished successfully.", level="success", step_completed=1, step_active=2)
        except Exception as e:
            err_trace = traceback.format_exc()
            logger.error(f"Critical Scraping Failure:\n{err_trace}")
            yield yield_event("error", f"Scraping step encountered a fatal issue: {str(e)}", level="error", step_failed=1)
            return

        # ==========================================
        # STEP 2-5: Multi-AI Enrichment Pipeline
        # ==========================================
        yield yield_event("running", "Step 2: Triggering Gemini 1.5 Pro Broad Search Sweep...")
        
        try:
            # We run enrichment.py pipeline which internally runs step 2, 3, 4, 5
            # To show a live visual update, we will run them individually in main or within enrichment.
            # But running them here allows granular visual step increments on the frontend!
            
            # Step 2: Gemini Broad Sweep
            from backend.enrichment import run_gemini_broad_sweep, run_openai_prompt_generator, run_gemini_deep_research, run_openai_content_synthesis
            
            broad_sweep = await run_gemini_broad_sweep(lead)
            yield yield_event("running", "Broad search sweep finished. Digital footprint mapped.", level="success", step_completed=2, step_active=3)
            await asyncio.sleep(0.5)
            
            # Step 3: GPT-4o Prompt Synthesis
            yield yield_event("running", "Step 3: Directing GPT-4o to analyze broad sweep data and construct 6 tailored queries...")
            custom_prompts = await run_openai_prompt_generator(lead, broad_sweep, scraped_content)
            yield yield_event("running", "GPT-4o successfully generated 6 custom research queries.", level="success", step_completed=3, step_active=4)
            await asyncio.sleep(0.5)
            
            # Step 4: Gemini Deep Category Searches
            yield yield_event("running", "Step 4: Prompting Gemini 1.5 Pro with Google Search Grounding to research all 6 verticals...")
            deep_research = await run_gemini_deep_research(custom_prompts)
            yield yield_event("running", "Gemini 6-category deep web scans completed.", level="success", step_completed=4, step_active=5)
            await asyncio.sleep(0.5)
            
            # Step 5: GPT-4o Business Synthesis
            yield yield_event("running", "Step 5: Synthesizing deep intelligence raw scans into 10-page consult copy...")
            enriched_report = await run_openai_content_synthesis(lead, broad_sweep, scraped_content, deep_research)
            yield yield_event("running", "Executive report contents synthesized and structured.", level="success", step_completed=5, step_active=6)
            await asyncio.sleep(0.5)
            
        except Exception as e:
            err_trace = traceback.format_exc()
            logger.error(f"Critical AI Enrichment Failure:\n{err_trace}")
            # Identify which step failed to map it on frontend
            failed_idx = 2
            if "prompt_generator" in err_trace or "Step 3" in err_trace: failed_idx = 3
            elif "deep_research" in err_trace or "Step 4" in err_trace: failed_idx = 4
            elif "content_synthesis" in err_trace or "Step 5" in err_trace: failed_idx = 5
            
            yield yield_event("error", f"AI Enrichment pipeline halted: {str(e)}", level="error", step_failed=failed_idx)
            return

        # ==========================================
        # STEP 6: PDF Report Layout Compilation
        # ==========================================
        yield yield_event("running", "Step 6: Rendering Jinja2 template and compiling into premium A4 PDF...")
        
        try:
            pdf_path = await generate_pdf_report(lead, enriched_report)
            yield yield_event("running", f"PDF compiled successfully. Saved locally: {pdf_path.name}", level="success", step_completed=6, step_active=7)
            await asyncio.sleep(0.5)
        except Exception as e:
            err_trace = traceback.format_exc()
            logger.error(f"Critical PDF Compilation Failure:\n{err_trace}")
            yield yield_event("error", f"PDF Generation step encountered a compile error: {str(e)}", level="error", step_failed=6)
            return

        # ==========================================
        # STEP 7: Google Drive Upload
        # ==========================================
        yield yield_event("running", f"Step 7: Accessing Google Drive and uploading report file...")
        
        try:
            drive_link = await asyncio.to_thread(upload_pdf_to_drive, pdf_path, lead.company_name)
            yield yield_event("running", "Upload complete. Access permissions updated to viewable.", level="success", step_completed=7, step_active=8)
            await asyncio.sleep(0.5)
        except Exception as e:
            err_trace = traceback.format_exc()
            logger.error(f"Critical Google Drive Failure:\n{err_trace}")
            yield yield_event("error", f"Google Drive step encountered a fatal issue: {str(e)}", level="error", step_failed=7)
            return

        # ==========================================
        # STEP 8: Google Sheets Logging
        # ==========================================
        yield yield_event("running", "Step 8: Appending lead data record row in Google Sheets base...")
        
        try:
            await asyncio.to_thread(log_lead_to_sheets, lead, drive_link, "Success")
            yield yield_event("running", "Sheet database row successfully appended.", level="success", step_completed=8, step_active=9)
            await asyncio.sleep(0.5)
        except Exception as e:
            err_trace = traceback.format_exc()
            logger.error(f"Critical Google Sheets Failure:\n{err_trace}")
            yield yield_event("error", f"Google Sheets step encountered a fatal database issue: {str(e)}", level="error", step_failed=8)
            return

        # ==========================================
        # STEP 9: Gmail SMTP Email Dispatch
        # ==========================================
        yield yield_event("running", f"Step 9: Connecting to Gmail SMTP and dispatching structured HTML email with PDF attached to {lead.email}...")
        
        try:
            await asyncio.to_thread(send_report_email, lead, pdf_path, drive_link)
            yield yield_event("running", "Email successfully delivered via Gmail SMTP.", level="success", step_completed=9)
            await asyncio.sleep(0.5)
        except Exception as e:
            err_trace = traceback.format_exc()
            logger.error(f"Critical Email Dispatch Failure:\n{err_trace}")
            yield yield_event("error", f"Gmail SMTP step encountered a delivery failure: {str(e)}", level="error", step_failed=9)
            return
            
        # ==========================================
        # PIPELINE COMPLETE SUCCESS STATE
        # ==========================================
        yield yield_event(
            "success", 
            "Pipeline successfully completed! All steps processed without errors.", 
            level="success",
            filename=pdf_path.name,
            drive_link=drive_link
        )
        logger.info(f"Pipeline finished successfully for {lead.company_name}! Shared file: {pdf_path.name}")
        
    return StreamingResponse(pipeline_generator(), media_type="text/event-stream")
