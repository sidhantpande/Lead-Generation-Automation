import os
import asyncio
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from backend.config import settings
from backend.utils.logger import log_step, logger
from backend.models import LeadInput, EnrichedCompanyData

# WeasyPrint Import Fallback Guard
WEASYPRINT_AVAILABLE = False
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except Exception as e:
    logger.warning(f"WeasyPrint could not be loaded (likely missing cairo/pango system libraries): {str(e)}. Playwright will be utilized as primary PDF compiler.")

async def compile_pdf_weasyprint(rendered_html: str, output_path: Path):
    """
    Compiles HTML to PDF using WeasyPrint.
    """
    if not WEASYPRINT_AVAILABLE:
        raise ImportError("WeasyPrint library is not available in the current environment.")
    
    logger.info("Executing WeasyPrint compilation...")
    # HTML write_pdf is blocking, so run in event loop thread executor
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: HTML(string=rendered_html).write_pdf(str(output_path))
    )
    logger.info("WeasyPrint PDF compile finished successfully.")

async def compile_pdf_playwright(rendered_html: str, output_path: Path):
    """
    Compiles HTML to PDF using headless Playwright Chromium.
    Extremely robust and handles modern CSS layouts and Google Fonts perfectly.
    """
    from playwright.async_api import async_playwright
    logger.info("Executing Playwright PDF compilation...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            # Set the rendered HTML
            await page.set_content(rendered_html)
            
            # Wait for all network resources to be idle & fonts loaded
            logger.debug("Waiting for page styles and Google Fonts to load...")
            await page.evaluate("document.fonts.ready")
            await asyncio.sleep(2.0)  # Brief buffer for heavy rendering assets
            
            # Print page directly to PDF
            await page.pdf(
                path=str(output_path),
                format="A4",
                print_background=True,
                margin={
                    "top": "0mm",
                    "bottom": "0mm",
                    "left": "0mm",
                    "right": "0mm"
                }
            )
            logger.info("Playwright PDF compile finished successfully.")
        finally:
            await browser.close()

async def generate_pdf_report(lead: LeadInput, report_data: EnrichedCompanyData) -> Path:
    """
    Renders Jinja2 report.html template and compiles it into a premium PDF.
    Prefers WeasyPrint if available, falls back automatically to Playwright Chromium.
    """
    log_step(6, "PDF_GENERATION", f"Starting PDF generation process for {lead.company_name}")
    
    # 1. Setup paths
    templates_dir = Path(__file__).parent.parent / "templates"
    output_dir = Path(__file__).parent.parent / settings.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    from slugify import slugify
    file_slug = slugify(lead.company_name, separator="_")
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_filename = f"{file_slug}_Intelligence_Report_{date_str}.pdf"
    output_path = output_dir / output_filename
    
    # 2. Render Jinja2 Template
    logger.info(f"Loading Jinja2 template from {templates_dir}")
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("report.html")
    
    current_date = datetime.now().strftime("%B %d, %Y")
    rendered_html = template.render(
        lead=lead,
        report=report_data,
        date=current_date
    )
    
    # 3. Compile PDF using the Dual Engine strategy
    pdf_compiled = False
    compile_errors = []
    
    # Try WeasyPrint first if available
    if WEASYPRINT_AVAILABLE:
        try:
            log_step(6, "PDF_GENERATION", "Attempting compilation via WeasyPrint engine")
            await compile_pdf_weasyprint(rendered_html, output_path)
            pdf_compiled = True
        except Exception as e:
            err_msg = f"WeasyPrint engine failed: {str(e)}"
            logger.warning(err_msg)
            compile_errors.append(err_msg)
            
    # Try Playwright fallback
    if not pdf_compiled:
        try:
            log_step(6, "PDF_GENERATION", "Triggering Playwright Chromium fallback engine", "WARNING")
            await compile_pdf_playwright(rendered_html, output_path)
            pdf_compiled = True
        except Exception as e:
            err_msg = f"Playwright engine fallback failed: {str(e)}"
            logger.error(err_msg)
            compile_errors.append(err_msg)
            
    # Raise error if both engines failed
    if not pdf_compiled:
        total_errs = " | ".join(compile_errors)
        fail_msg = f"PDF Generation failed on all compiling engines: {total_errs}"
        log_step(6, "PDF_GENERATION", fail_msg, "ERROR")
        raise RuntimeError(fail_msg)
        
    log_step(6, "PDF_GENERATION", f"PDF compiled successfully and saved at: {output_path}", "SUCCESS")
    return output_path
