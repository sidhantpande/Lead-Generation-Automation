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

class CompetitorItem(BaseModel):
    name: str = Field(..., description="Name of the direct competitor")
    focus: str = Field(..., description="Main business focus or niche of this competitor")
    advantage: str = Field(..., description="Our target company's primary competitive advantage over them")

class PersonaItem(BaseModel):
    name: str = Field(..., description="Name or role of the target buyer persona (e.g. CTO, VP of Operations)")
    pain_point: str = Field(..., description="Primary daily friction or frustration they face")
    value_hook: str = Field(..., description="How our target company's product/service directly solves their pain")

class EnrichedCompanyData(BaseModel):
    executive_summary: str = Field(..., description="3-4 paragraph high-level consult-grade summary")
    company_profile: str = Field(..., description="Detailed profile of company services and target users")
    primary_value_prop: str = Field(..., description="Concise, high-impact summary of their core customer value hook")
    target_personas: List[PersonaItem] = Field(..., min_length=2, max_length=2, description="2 core buyer personas targeted by the business")
    industry_landscape: str = Field(..., description="Market analysis, macro trends, and drivers")
    competitive_positioning: str = Field(..., description="Differentiators, competitor gaps, and positions")
    competitors_matrix: List[CompetitorItem] = Field(..., min_length=2, max_length=3, description="2-3 direct competitors comparison matrix")
    social_media_analysis: str = Field(..., description="LinkedIn and Instagram presence audit")
    social_scorecard: Dict[str, str] = Field(..., description="Audit scores (e.g., linkedin_score, instagram_score, branding_grade, cohesion_score)")
    growth_signals: str = Field(..., description="Hiring surges, press events, and partnership expansions")
    pain_points: List[str] = Field(..., min_length=3, max_length=5, description="3-5 detailed operational challenge bullets")
    recommendations: List[RecommendationItem] = Field(..., min_length=3, max_length=5, description="3-5 structured recommendation cards")
    roadmap_phases: List[str] = Field(..., min_length=3, max_length=5, description="3-5 chronological phase milestone titles corresponding to the recommendations")
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
