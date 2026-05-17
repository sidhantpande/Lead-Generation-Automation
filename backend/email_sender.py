import os
from pathlib import Path
import resend

from backend.config import settings
from backend.utils.logger import log_step, logger
from backend.utils.retry import api_retry_decorator
from backend.models import LeadInput

@api_retry_decorator("Resend Email Send")
def send_report_email(lead: LeadInput, pdf_path: Path, drive_link: str) -> None:
    """
    Sends the generated PDF report as an email attachment and public link to the lead's email using Resend.
    """
    log_step(9, "EMAIL_SENDER", f"Preparing email dispatch for {lead.email}")
    
    # 1. Validation check
    if not settings.RESEND_API_KEY or settings.RESEND_API_KEY.strip() == "" or "your_resend" in settings.RESEND_API_KEY:
        err_msg = "Email sending aborted: Missing RESEND_API_KEY in configuration."
        logger.error(err_msg)
        raise ValueError(err_msg)

    # 2. Configure API Key
    resend.api_key = settings.RESEND_API_KEY
    
    # 3. Read PDF file bytes for attachment
    logger.info(f"Reading PDF from {pdf_path} for attachment")
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF report file does not exist at {pdf_path}")
        
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
        
    # Convert bytes to a list of integers as required by the Resend Python SDK
    byte_list = list(pdf_bytes)
    
    attachment_name = f"{lead.company_name.replace(' ', '_')}_Intelligence_Report.pdf"
    
    attachments = [
        {
            "filename": attachment_name,
            "content": byte_list
        }
    ]
    
    # 4. Formulate email contents
    subject = f"Your {lead.company_name} Intelligence Report — Prepared by SimplifIQ"
    
    # Premium styled HTML email body
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                color: #334155;
                line-height: 1.6;
                background-color: #f8fafc;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 30px auto;
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            }}
            .header {{
                background-color: #0f172a;
                color: #fbbf24;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 700;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .button-container {{
                text-align: center;
                margin: 35px 0;
            }}
            .button {{
                background-color: #fbbf24;
                color: #0f172a;
                padding: 14px 28px;
                text-decoration: none;
                font-weight: bold;
                border-radius: 5px;
                font-size: 15px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                display: inline-block;
            }}
            .footer {{
                background-color: #f1f5f9;
                padding: 20px 30px;
                text-align: center;
                font-size: 12px;
                color: #64748b;
                border-top: 1px solid #e2e8f0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>SimplifIQ</h1>
            </div>
            <div class="content">
                <p>Hello {lead.name},</p>
                
                <p>We are excited to share your custom <strong>Business Intelligence Report</strong> for <strong>{lead.company_name}</strong>.</p>
                
                <p>Our multi-AI research engines scanned the web and analyzed your digital presence, competitive advantages, industry vertical metrics, and hiring trends to synthesize a 10-page premium executive audit.</p>
                
                <p>We have attached the full PDF report directly to this email. You can also view and download the live report online in our secure Google Drive folder by clicking the button below:</p>
                
                <div class="button-container">
                    <a href="{drive_link}" class="button">View Report Online</a>
                </div>
                
                <p><strong>Key Areas Analyzed in Your Report:</strong></p>
                <ul>
                    <li>C-Level Executive Summary</li>
                    <li>Company Offerings & Buyer Persona Profile</li>
                    <li>Macro Industry Trends & Drivers</li>
                    <li>Direct Competitor Gap Analysis</li>
                    <li>Social Media & Brand Voice Audit</li>
                    <li>Active Hiring & Growth Signals</li>
                    <li>Top 5 Operational Pain Points</li>
                    <li>Immediate 5-Step Strategic Roadmap</li>
                </ul>
                
                <p>We would love to hear your feedback on our findings and discuss how SimplifIQ can assist {lead.company_name} in implementing the recommendations outlined in the report.</p>
                
                <p>Best regards,<br>
                <strong>The SimplifIQ Intelligence Team</strong></p>
            </div>
            <div class="footer">
                <p>This is an automated analysis generated for {lead.company_name} ({lead.website}).<br>
                Confidentiality Notice: The contents of the attached report are confidential.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # 5. Dispatch email
    logger.info(f"Dispatching Resend email call to {lead.email}")
    
    # In Resend Python, Emails.send is invoked as follows:
    resend.Emails.send({
        "from": f"{settings.RESEND_FROM_NAME} <{settings.RESEND_FROM_EMAIL}>",
        "to": lead.email,
        "subject": subject,
        "html": html_content,
        "attachments": attachments
    })
    
    log_step(9, "EMAIL_SENDER", f"Report email successfully sent to {lead.email}", "SUCCESS")
