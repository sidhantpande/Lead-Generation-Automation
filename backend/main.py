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
from backend.drive_uploader import upload_pdf_to_drive, upload_and_log_via_web_app
from backend.sheets_logger import log_lead_to_sheets
from backend.email_sender import send_report_email

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Lead Generation Automation Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        
        event_queue = asyncio.Queue()

        async def run_pipeline_task():
            try:
                # ==========================================
                # STEP 0: Configuration Validation Checkpoint
                # ==========================================
                event_queue.put_nowait(yield_event("running", "Step 0: Checking environment configurations and active API keys...", step_active=0))
                missing_configs = settings.validate_setup()
                
                if missing_configs:
                    err_msg = f"Pipeline terminated: Configuration variables missing: {', '.join(missing_configs)}"
                    logger.error(err_msg)
                    event_queue.put_nowait(yield_event("error", err_msg, level="error", step_failed=0))
                    event_queue.put_nowait(None)
                    return

                event_queue.put_nowait(yield_event("running", "All essential configuration requirements validated successfully.", level="success", step_completed=0, step_active=1))
                await asyncio.sleep(0.5)

                # ==========================================
                # STEP 1: Website Scraping
                # ==========================================
                event_queue.put_nowait(yield_event("running", f"Step 1: Commencing scraping sequence for: {lead.website}"))
                
                try:
                    scraped_content = await scrape_website(lead.website)
                    event_queue.put_nowait(yield_event("running", "Website scraping complete. Text extraction finished successfully.", level="success", step_completed=1, step_active=2))
                except Exception as e:
                    err_trace = traceback.format_exc()
                    logger.error(f"Critical Scraping Failure:\n{err_trace}")
                    event_queue.put_nowait(yield_event("error", f"Scraping step encountered a fatal issue: {str(e)}", level="error", step_failed=1))
                    event_queue.put_nowait(None)
                    return

                # ==========================================
                # STEP 2-5: Multi-AI Enrichment Pipeline
                # ==========================================
                event_queue.put_nowait(yield_event("running", "Step 2: Triggering Gemini 1.5 Pro Broad Search Sweep..."))
                
                try:
                    # Define live progress callback for nested operations
                    async def progress_callback(msg: str, lvl: str = "info"):
                        event_queue.put_nowait(yield_event("running", msg, level=lvl, step_active=4))

                    # Step 2: Gemini Broad Sweep
                    from backend.enrichment import run_gemini_broad_sweep, run_openai_prompt_generator, run_gemini_deep_research, run_openai_content_synthesis
                    
                    broad_sweep = await run_gemini_broad_sweep(lead, progress_callback)
                    event_queue.put_nowait(yield_event("running", "Broad search sweep finished. Digital footprint mapped.", level="success", step_completed=2, step_active=3))
                    await asyncio.sleep(0.5)
                    
                    # Step 3: GPT-4o Prompt Synthesis
                    event_queue.put_nowait(yield_event("running", "Step 3: Directing GPT-4o to analyze broad sweep data and construct 6 tailored queries..."))
                    custom_prompts = await run_openai_prompt_generator(lead, broad_sweep, scraped_content)
                    event_queue.put_nowait(yield_event("running", "GPT-4o successfully generated 6 custom research queries.", level="success", step_completed=3, step_active=4))
                    await asyncio.sleep(0.5)
                    
                    # Step 4: Gemini Deep Category Searches
                    event_queue.put_nowait(yield_event("running", "Step 4: Prompting Gemini 1.5 Pro with Google Search Grounding to research all 6 verticals..."))
                    deep_research = await run_gemini_deep_research(custom_prompts, progress_callback)
                    event_queue.put_nowait(yield_event("running", "Gemini 6-category deep web scans completed.", level="success", step_completed=4, step_active=5))
                    await asyncio.sleep(0.5)
                    
                    # Step 5: GPT-4o Business Synthesis
                    event_queue.put_nowait(yield_event("running", "Step 5: Synthesizing deep intelligence raw scans into 10-page consult copy..."))
                    enriched_report = await run_openai_content_synthesis(lead, broad_sweep, scraped_content, deep_research)
                    event_queue.put_nowait(yield_event("running", "Executive report contents synthesized and structured.", level="success", step_completed=5, step_active=6))
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    err_trace = traceback.format_exc()
                    logger.error(f"Critical AI Enrichment Failure:\n{err_trace}")
                    # Identify which step failed to map it on frontend
                    failed_idx = 2
                    if "prompt_generator" in err_trace or "Step 3" in err_trace: failed_idx = 3
                    elif "deep_research" in err_trace or "Step 4" in err_trace: failed_idx = 4
                    elif "content_synthesis" in err_trace or "Step 5" in err_trace: failed_idx = 5
                    
                    event_queue.put_nowait(yield_event("error", f"AI Enrichment pipeline halted: {str(e)}", level="error", step_failed=failed_idx))
                    event_queue.put_nowait(None)
                    return

                # ==========================================
                # STEP 6: PDF Report Layout Compilation
                # ==========================================
                event_queue.put_nowait(yield_event("running", "Step 6: Rendering Jinja2 template and compiling into premium A4 PDF..."))
                
                try:
                    pdf_path = await generate_pdf_report(lead, enriched_report)
                    event_queue.put_nowait(yield_event("running", f"PDF compiled successfully. Saved locally: {pdf_path.name}", level="success", step_completed=6, step_active=7))
                    await asyncio.sleep(0.5)
                except Exception as e:
                    err_trace = traceback.format_exc()
                    logger.error(f"Critical PDF Compilation Failure:\n{err_trace}")
                    event_queue.put_nowait(yield_event("error", f"PDF Generation step encountered a compile error: {str(e)}", level="error", step_failed=6))
                    event_queue.put_nowait(None)
                    return

                # ==========================================
                # STEP 7: Google Drive Upload
                # ==========================================
                event_queue.put_nowait(yield_event("running", f"Step 7: Accessing Google Drive and uploading report file..."))
                
                fallback_sheets_logged = False
                try:
                    drive_link = await asyncio.to_thread(upload_pdf_to_drive, pdf_path, lead.company_name)
                    event_queue.put_nowait(yield_event("running", "Upload complete. Access permissions updated to viewable.", level="success", step_completed=7, step_active=8))
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.warning(f"Google Drive upload issue (Service Account): {str(e)}")
                    # Check if Google Web App URL is configured for fallback
                    if settings.GOOGLE_WEB_APP_URL and settings.GOOGLE_WEB_APP_URL.strip() != "":
                        try:
                            event_queue.put_nowait(yield_event("running", "Service Account upload quota exceeded. Triggering Google Apps Script Web App fallback...", level="warning"))
                            drive_link = await asyncio.to_thread(upload_and_log_via_web_app, pdf_path, lead)
                            fallback_sheets_logged = True
                            event_queue.put_nowait(yield_event("running", "Web App upload & sheet logging completed successfully!", level="success", step_completed=7, step_active=8))
                            await asyncio.sleep(0.5)
                        except Exception as fallback_err:
                            logger.error(f"Fallback Google Web App execution failed: {str(fallback_err)}")
                            drive_link = "#"
                            event_queue.put_nowait(yield_event("running", f"Drive Alert: Apps Script Web App upload also failed ({str(fallback_err)}). Continuing pipeline...", level="warning", step_completed=7, step_active=8))
                            await asyncio.sleep(0.5)
                    else:
                        drive_link = "#"
                        event_queue.put_nowait(yield_event("running", "Drive Alert: Upload skipped (Service Account has no storage quota and Web App fallback not configured). Continuing pipeline...", level="warning", step_completed=7, step_active=8))
                        await asyncio.sleep(0.5)

                # ==========================================
                # STEP 8: Google Sheets Logging
                # ==========================================
                event_queue.put_nowait(yield_event("running", "Step 8: Appending lead data record row in Google Sheets base..."))
                
                if fallback_sheets_logged:
                    event_queue.put_nowait(yield_event("running", "Sheet row already logged via Web App upload fallback step.", level="success", step_completed=8, step_active=9))
                    await asyncio.sleep(0.5)
                else:
                    try:
                        await asyncio.to_thread(log_lead_to_sheets, lead, drive_link, "Success")
                        event_queue.put_nowait(yield_event("running", "Sheet database row successfully appended.", level="success", step_completed=8, step_active=9))
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.warning(f"Google Sheets logging issue (Service Account): {str(e)}")
                        # Check if we can fallback to Web App to log lead (using the same call)
                        if settings.GOOGLE_WEB_APP_URL and settings.GOOGLE_WEB_APP_URL.strip() != "":
                            try:
                                event_queue.put_nowait(yield_event("running", "Service Account Sheets API blocked. Triggering Apps Script Web App log fallback...", level="warning"))
                                drive_link = await asyncio.to_thread(upload_and_log_via_web_app, pdf_path, lead)
                                event_queue.put_nowait(yield_event("running", "Web App log completed successfully via fallback!", level="success", step_completed=8, step_active=9))
                                await asyncio.sleep(0.5)
                            except Exception as fallback_err:
                                logger.error(f"Fallback Google Web App execution failed: {str(fallback_err)}")
                                event_queue.put_nowait(yield_event("running", f"Sheet Alert: Log write fallback failed ({str(fallback_err)}). Continuing pipeline...", level="warning", step_completed=8, step_active=9))
                                await asyncio.sleep(0.5)
                        else:
                            event_queue.put_nowait(yield_event("running", f"Sheet Alert: Log write skipped (permission or API limits). Continuing pipeline...", level="warning", step_completed=8, step_active=9))
                            await asyncio.sleep(0.5)

                # ==========================================
                # STEP 9: Gmail SMTP Email Dispatch
                # ==========================================
                event_queue.put_nowait(yield_event("running", f"Step 9: Connecting to Gmail SMTP and dispatching structured HTML email with PDF attached to {lead.email}..."))
                
                try:
                    await asyncio.to_thread(send_report_email, lead, pdf_path, drive_link)
                    event_queue.put_nowait(yield_event("running", "Email successfully delivered via Gmail SMTP.", level="success", step_completed=9))
                    await asyncio.sleep(0.5)
                except Exception as e:
                    err_trace = traceback.format_exc()
                    logger.error(f"Critical Email Dispatch Failure:\n{err_trace}")
                    event_queue.put_nowait(yield_event("error", f"Gmail SMTP step encountered a delivery failure: {str(e)}", level="error", step_failed=9))
                    event_queue.put_nowait(None)
                    return
                    
                # ==========================================
                # PIPELINE COMPLETE SUCCESS STATE
                # ==========================================
                event_queue.put_nowait(yield_event(
                    "success", 
                    "Pipeline successfully completed! All steps processed without errors.", 
                    level="success",
                    filename=pdf_path.name,
                    drive_link=drive_link
                ))
                logger.info(f"Pipeline finished successfully for {lead.company_name}! Shared file: {pdf_path.name}")
                event_queue.put_nowait(None)
                
            except Exception as outer_e:
                err_trace = traceback.format_exc()
                logger.error(f"Unhandled Pipeline Task Error:\n{err_trace}")
                event_queue.put_nowait(yield_event("error", f"Unhandled pipeline crash: {str(outer_e)}", level="error"))
                event_queue.put_nowait(None)

        # Proactively fire the pipeline run inside an isolated background event loop task
        asyncio.create_task(run_pipeline_task())

        # Stream yielded NDJSON events to the client in real-time as they arrive in the queue
        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield event

    return StreamingResponse(pipeline_generator(), media_type="text/event-stream")
