import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    RESEND_API_KEY: Optional[str] = Field(default=None)
    
    # Resend Settings
    RESEND_FROM_EMAIL: str = Field(default="reports@yourdomain.com")
    RESEND_FROM_NAME: str = Field(default="SimplifIQ Intelligence")
    
    # Google API Settings
    GOOGLE_SERVICE_ACCOUNT_PATH: str = Field(default="credentials/service_account.json")
    GOOGLE_DRIVE_FOLDER_ID: Optional[str] = Field(default=None)
    GOOGLE_SHEET_ID: Optional[str] = Field(default=None)
    
    # App Settings
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000)
    OUTPUT_DIR: str = Field(default="outputs")
    
    # Allow loading from .env
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_setup(self) -> List[str]:
        """
        Validates the configuration and returns a list of missing or invalid configurations.
        """
        missing = []
        
        # Check OpenAI key
        if not self.OPENAI_API_KEY or self.OPENAI_API_KEY.strip() == "" or "your_openai" in self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
            
        # Check Gemini key
        if not self.GEMINI_API_KEY or self.GEMINI_API_KEY.strip() == "" or "your_gemini" in self.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
            
        # Check Resend key
        if not self.RESEND_API_KEY or self.RESEND_API_KEY.strip() == "" or "your_resend" in self.RESEND_API_KEY:
            missing.append("RESEND_API_KEY")
            
        # Check Google Service Account
        sa_path = Path(self.GOOGLE_SERVICE_ACCOUNT_PATH)
        if not sa_path.exists():
            missing.append(f"Google Service Account File ({self.GOOGLE_SERVICE_ACCOUNT_PATH}) is missing")
            
        # Check Drive folder ID
        if not self.GOOGLE_DRIVE_FOLDER_ID or self.GOOGLE_DRIVE_FOLDER_ID.strip() == "" or "your_google_drive" in self.GOOGLE_DRIVE_FOLDER_ID:
            missing.append("GOOGLE_DRIVE_FOLDER_ID")
            
        # Check Sheets ID
        if not self.GOOGLE_SHEET_ID or self.GOOGLE_SHEET_ID.strip() == "" or "your_google_sheet" in self.GOOGLE_SHEET_ID:
            missing.append("GOOGLE_SHEET_ID")
            
        return missing

# Instantiate settings singleton
settings = Settings()
