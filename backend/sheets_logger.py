import threading
from datetime import datetime
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build

from backend.config import settings
from backend.utils.logger import log_step, logger
from backend.utils.retry import api_retry_decorator
from backend.models import LeadInput, LeadRecord

# Global re-entrant threading lock for thread-safe Sheets appending
_sheets_lock = threading.Lock()

@api_retry_decorator("Google Sheets Append")
def log_lead_to_sheets(lead: LeadInput, drive_link: str, status: str = "Success") -> None:
    """
    Appends a new lead entry row in Google Sheets under the 'Lead Responses' tab.
    Guarantees thread safety and race-condition prevention using a global threading Lock.
    """
    with _sheets_lock:
        log_step(8, "SHEETS_LOGGER", f"Logging lead {lead.email} to Google Sheet")
        
        # 1. Validation checks
        missing_configs = []
        sa_path = Path(settings.GOOGLE_SERVICE_ACCOUNT_PATH)
        
        if not sa_path.exists():
            missing_configs.append(f"Google Service Account file not found at '{settings.GOOGLE_SERVICE_ACCOUNT_PATH}'")
        if not settings.GOOGLE_SHEET_ID or settings.GOOGLE_SHEET_ID.strip() == "":
            missing_configs.append("GOOGLE_SHEET_ID")
            
        if missing_configs:
            err_msg = f"Google Sheets logging aborted: Missing requirements: {', '.join(missing_configs)}"
            logger.error(err_msg)
            raise ValueError(err_msg)

        # 2. Authenticate
        logger.info(f"Authenticating Google Sheets client using: {sa_path}")
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = service_account.Credentials.from_service_account_file(
            str(sa_path), 
            scopes=scopes
        )
        
        service = build("sheets", "v4", credentials=credentials)
        
        # 3. Create the row values
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Structure matching row requirements:
        # A: Timestamp, B: Full Name, C: Email, D: Company Name, E: Website,
        # F: LinkedIn, G: Instagram, H: Industry, I: Company Size, J: Report Status, K: Drive PDF Link
        row_values = [
            timestamp_str,
            lead.name,
            lead.email,
            lead.company_name,
            lead.website,
            lead.linkedin_url or "N/A",
            lead.instagram_handle or "N/A",
            lead.industry or "N/A",
            lead.company_size or "N/A",
            status,
            drive_link
        ]
        
        # 4. Perform append call (writes to next empty row in Lead Responses tab)
        spreadsheet_id = settings.GOOGLE_SHEET_ID
        range_name = "'Lead Responses'!A:K"  # Appends to the tab named 'Lead Responses'
        value_input_option = "USER_ENTERED"
        
        body = {
            "values": [row_values]
        }
        
        logger.info(f"Appending row to Sheet ID {spreadsheet_id} in tab 'Lead Responses'")
        
        # Check sheet and append
        try:
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption=value_input_option,
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
        except Exception as append_err:
            # If the 'Lead Responses' tab does not exist, let's try appending to Sheet1 or creating it
            logger.warning(f"Failed appending specifically to tab 'Lead Responses' ({str(append_err)}). Trying base range A:K.")
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range="A:K",
                valueInputOption=value_input_option,
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            
        log_step(8, "SHEETS_LOGGER", "Lead successfully appended to Google Sheet.", "SUCCESS")
