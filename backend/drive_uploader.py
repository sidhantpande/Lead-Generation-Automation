import os
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from backend.config import settings
from backend.utils.logger import log_step, logger
from backend.utils.retry import api_retry_decorator

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
        fields="id, webViewLink"
    ).execute()
    
    file_id = drive_file.get("id")
    web_link = drive_file.get("webViewLink")
    
    logger.info(f"Upload complete. File ID: {file_id}")
    
    # 5. Share with public ('anyone with link can view')
    logger.info(f"Modifying permissions for file {file_id} to public view")
    user_permission = {
        "type": "anyone",
        "role": "reader"
    }
    
    service.permissions().create(
        fileId=file_id,
        body=user_permission
    ).execute()
    
    log_step(7, "DRIVE_UPLOADER", f"Successfully uploaded PDF. Public URL: {web_link}", "SUCCESS")
    return web_link
