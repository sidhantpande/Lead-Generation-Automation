from pydantic import BaseModel, Field, EmailStr, HttpUrl, field_validator
from typing import Optional, List, Dict, Any

class LeadInput(BaseModel):
    name: str = Field(..., min_length=2, description="Full name of the lead prospect")
    email: EmailStr = Field(..., description="Corporate or work email address")
    company_name: str = Field(..., min_length=1, description="Legal/trade name of the business")
    website: str = Field(..., description="Corporate website URL (e.g. acme.com or https://acme.com)")
    linkedin_url: Optional[str] = Field(default=None, description="Optional Company LinkedIn URL")
    instagram_handle: Optional[str] = Field(default=None, description="Optional Instagram account handle")
    industry: Optional[str] = Field(default=None, description="Self-selected industry vertical")
    company_size: Optional[str] = Field(default=None, description="Self-selected size interval")
    additional_context: Optional[str] = Field(default=None, description="Optional extra details provided by lead")

    @field_validator("website", mode="before")
    @classmethod
    def clean_website_url(cls, v: Any) -> str:
        """
        Prepend https:// if no protocol is supplied so it is a valid URL structure.
        """
        if not isinstance(v, str):
            raise ValueError("Website must be a text string")
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v

class RecommendationItem(BaseModel):
    title: str = Field(..., description="Actionable title of the business recommendation")
    description: str = Field(..., description="Deep, highly context-driven advice explanation")

class EnrichedCompanyData(BaseModel):
    executive_summary: str = Field(..., description="3-4 paragraph high-level consult-grade summary")
    company_profile: str = Field(..., description="Detailed profile of company services and target users")
    industry_landscape: str = Field(..., description="Market analysis, macro trends, and drivers")
    competitive_positioning: str = Field(..., description="Differentiators, competitor gaps, and positions")
    social_media_analysis: str = Field(..., description="LinkedIn and Instagram presence audit")
    growth_signals: str = Field(..., description="Hiring surges, press events, and partnership expansions")
    pain_points: List[str] = Field(..., min_items=3, max_items=5, description="3-5 detailed operational challenge bullets")
    recommendations: List[RecommendationItem] = Field(..., min_items=3, max_items=5, description="3-5 structured recommendation cards")
    closing_note: str = Field(..., description="Strategic outro call-to-action")

class LeadRecord(BaseModel):
    timestamp: str = Field(..., description="Datetime when lead was received")
    name: str = Field(..., description="Full Name")
    email: str = Field(..., description="Work Email")
    company_name: str = Field(..., description="Company Name")
    website: str = Field(..., description="Website")
    linkedin_url: str = Field(..., description="LinkedIn URL")
    instagram_handle: str = Field(..., description="Instagram Handle")
    industry: str = Field(..., description="Industry Dropdown")
    company_size: str = Field(..., description="Company Size Dropdown")
    report_status: str = Field(..., description="Success, Partial, or Failed status")
    drive_pdf_link: str = Field(..., description="Shareable URL of the generated report")
