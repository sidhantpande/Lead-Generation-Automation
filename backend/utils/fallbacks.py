from typing import Dict, Any, List

def get_fallback_scraped_data(url: str, error_msg: str) -> str:
    """
    Returns standard fallback text if scraping both BS4 and Playwright fail.
    Scraping failure is treated as non-critical since Gemini search can still locate company info.
    """
    return f"Website scraping for {url} failed. Reason: {error_msg}. Continuing using search enrichment."

def get_default_prompts(company_name: str, website: str) -> Dict[str, str]:
    """
    Default research prompts in case GPT-4o fails to synthesize custom ones.
    Allows Gemini search pass to still have high-quality targeted queries.
    """
    return {
        "industry_landscape": f"What is the current industry landscape, market size, and primary growth drivers for the industry that {company_name} ({website}) operates in?",
        "competitor_analysis": f"Who are the top 3 direct competitors of {company_name} ({website})? Detail their strengths, weaknesses, and market overlap.",
        "social_media_presence": f"Analyze the brand voice, posting frequency, and user engagement of {company_name} on LinkedIn and Instagram.",
        "recent_news": f"Search for any recent news, press releases, funding rounds, or product launches related to {company_name} from the past 12-18 months.",
        "growth_signals": f"Are there active growth signals for {company_name} such as hiring surges, office expansions, or strategic partnerships?",
        "pain_points": f"Based on its website and market positioning, what are 3-5 specific business pain points, technological challenges, or operational gaps {company_name} is likely facing?"
    }
