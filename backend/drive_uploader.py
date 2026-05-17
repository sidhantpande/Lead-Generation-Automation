import os
import base64
import requests
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from backend.config import settings
from backend.utils.logger import log_step, logger
from backend.utils.retry import api_retry_decorator
from backend.models import LeadInput

@api_retry_decorator("Google Drive Upload")
def upload_pdf_to_drive(pdf_path: Path, company_name: str) -> str:
    """
    Uploads a generated PDF report to a targeted Google Drive folder using service account authentication.
    Applies 'anyone with link can view' permissions and returns the public view web link.
    """
    log_step(7, "DRIVE_UPLOADER", f"Initiating Google Drive upload for {pdf_path.name}")
    
    # 1. Validation checks
    missing_configs = []
    sa_path = Path(settings.GOOGLE_SERVICE_ACCOUNT_PATH)
    
    if not sa_path.exists():
        missing_configs.append(f"Google Service Account file not found at '{settings.GOOGLE_SERVICE_ACCOUNT_PATH}'")
    if not settings.GOOGLE_DRIVE_FOLDER_ID or settings.GOOGLE_DRIVE_FOLDER_ID.strip() == "":
        missing_configs.append("GOOGLE_DRIVE_FOLDER_ID")
        
    if missing_configs:
        err_msg = f"Google Drive upload aborted: Missing requirements: {', '.join(missing_configs)}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    # 2. Authenticate
    logger.info(f"Authenticating Google Drive client using: {sa_path}")
    scopes = ["https://www.googleapis.com/auth/drive"]
    credentials = service_account.Credentials.from_service_account_file(
        str(sa_path), 
        scopes=scopes
    )
    
    service = build("drive", "v3", credentials=credentials)
    
    # 3. Formulate file metadata and media upload payload
    file_metadata = {
        "name": pdf_path.name,
        "parents": [settings.GOOGLE_DRIVE_FOLDER_ID]
    }
    
    media = MediaFileUpload(
        str(pdf_path),
        mimetype="application/pdf",
        resumable=True
    )
    
    # 4. Upload file
    logger.info(f"Uploading file to folder ID: {settings.GOOGLE_DRIVE_FOLDER_ID}")
    drive_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=True
    ).execute()
    
    file_id = drive_file.get("id")
    web_link = drive_file.get("webViewLink")
    
    logger.info(f"Upload complete. File ID: {file_id}")
    
    # 5. Share with public ('anyone with link can view')
    try:
        logger.info(f"Modifying permissions for file {file_id} to public view")
        user_permission = {
            "type": "anyone",
            "role": "reader"
        }
        
        service.permissions().create(
            fileId=file_id,
            body=user_permission,
            supportsAllDrives=True
        ).execute()
    except Exception as perm_err:
        logger.warning(
            f"Public link sharing permission modification skipped. This is typical if the corporate "
            f"organization's domain policy restricts sharing files outside of their Workspace domain. "
            f"Non-fatal error: {str(perm_err)}"
        )
    
    log_step(7, "DRIVE_UPLOADER", f"Successfully uploaded PDF. Public URL: {web_link}", "SUCCESS")
    return web_link

def upload_and_log_via_web_app(pdf_path: Path, lead: LeadInput) -> str:
    """
    Executes fallback upload and sheet logging via Google Apps Script Web App.
    Bypasses standard Google Service Account storage quotas by running as the user's personal identity.
    Returns the generated Google Drive public link.
    """
    log_step(7, "DRIVE_UPLOADER_FALLBACK", f"Initiating Apps Script Web App fallback upload/logging for {pdf_path.name}")
    
    if not settings.GOOGLE_WEB_APP_URL or settings.GOOGLE_WEB_APP_URL.strip() == "":
        raise ValueError("GOOGLE_WEB_APP_URL is not configured in settings/environment.")
        
    # 1. Base64 Encode PDF
    logger.info(f"Encoding PDF '{pdf_path.name}' to Base64...")
    with open(pdf_path, "rb") as f:
        pdf_base64 = base64.b64encode(f.read()).decode("utf-8")
        
    payload = {
        "action": "upload_and_log",
        "filename": pdf_path.name,
        "pdf_base64": pdf_base64,
        "name": lead.name,
        "email": lead.email,
        "company_name": lead.company_name,
        "website": lead.website,
        "linkedin_url": lead.linkedin_url or "N/A",
        "instagram_handle": lead.instagram_handle or "N/A",
        "industry": lead.industry or "N/A",
        "company_size": lead.company_size or "N/A"
    }
    
    # 2. HTTP POST Request
    url = settings.GOOGLE_WEB_APP_URL.strip()
    logger.info(f"POSTing payload to Web App URL: {url}")
    
    response = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=45
    )
    
    if response.status_code != 200:
        raise RuntimeError(f"Web App response failed with status code {response.status_code}: {response.text}")
        
    result = response.json()
    if result.get("status") != "success":
        err_msg = result.get("message", "Unknown Web App error")
        raise RuntimeError(f"Google Apps Script execution error: {err_msg}")
        
    drive_link = result.get("drive_link")
    log_step(7, "DRIVE_UPLOADER_FALLBACK", f"Web App fallback upload/logging completed successfully! Link: {drive_link}", "SUCCESS")
    return drive_link
