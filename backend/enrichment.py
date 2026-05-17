import json
import asyncio
from typing import Dict, Any, List
from openai import AsyncOpenAI
from google import genai
from google.genai import types

from backend.config import settings
from backend.utils.logger import log_step, logger
from backend.utils.retry import api_retry_decorator
from backend.utils.fallbacks import get_default_prompts
from backend.models import LeadInput, EnrichedCompanyData

# Configure OpenAI Client
def get_openai_client() -> AsyncOpenAI:
    if not settings.OPENAI_API_KEY:
        raise ValueError("Missing OPENAI_API_KEY. Configure it in your .env file.")
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Configure Gemini Client
def get_gemini_client() -> genai.Client:
    if not settings.GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_API_KEY. Configure it in your .env file.")
    return genai.Client(api_key=settings.GEMINI_API_KEY)

@api_retry_decorator("Gemini Broad Sweep")
async def run_gemini_broad_sweep(lead: LeadInput) -> str:
    """
    Step 1: Executes a broad web-search sweep via Gemini 1.5 Pro to gather overall details on the company.
    """
    log_step(1, "ENRICHMENT", f"Executing Gemini broad sweep for: {lead.company_name}")
    client = get_gemini_client()
    
    prompt = (
        f"Research the company '{lead.company_name}' with website {lead.website}.\n"
        f"Provide a comprehensive business profile, detailing:\n"
        f"1. What they do and their core product/service offerings.\n"
        f"2. Who their target customers are (buyer personas) and their business model.\n"
        f"3. Their founding year, size, and general online presence.\n"
    )
    
    if lead.linkedin_url:
        prompt += f"4. Review their company profile at {lead.linkedin_url}.\n"
    if lead.instagram_handle:
        prompt += f"5. Review their social media presence at Instagram @{lead.instagram_handle}.\n"
        
    prompt += "Return a highly detailed, professional factual profile. Keep it objective."

    # Run in thread pool for maximum concurrency safety
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, 
        lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
    )
    
    text = response.text or ""
    logger.debug(f"Gemini broad sweep finished. Length: {len(text)} characters.")
    log_step(1, "ENRICHMENT", f"Gemini broad sweep completed successfully.", "SUCCESS")
    return text

@api_retry_decorator("OpenAI Prompt Generation")
async def run_openai_prompt_generator(lead: LeadInput, broad_sweep: str, scraped_content: str) -> Dict[str, str]:
    """
    Step 3: OpenAI analyzes initial data and creates 6 highly custom targeted search prompts for the second Gemini pass.
    """
    log_step(3, "ENRICHMENT", "Generating customized deep-research search prompts via GPT-4o")
    openai_client = get_openai_client()
    
    system_prompt = (
        "You are an expert business intelligence prompt engineer. Your job is to analyze initial company research "
        "and website scraping data to formulate exactly 6 targeted, highly-specific research queries that "
        "will be used to search the web for deep information. Each query should focus on uncovering concrete "
        "details (such as specific competitors, market statistics, local hiring events, recent news, etc.) specific to this company.\n\n"
        "You MUST return a JSON object with these EXACT keys:\n"
        "- 'industry_landscape'\n"
        "- 'competitor_analysis'\n"
        "- 'social_media_presence'\n"
        "- 'recent_news'\n"
        "- 'growth_signals'\n"
        "- 'pain_points'\n\n"
        "Ensure your queries are structured to maximize search search quality (avoiding generic phrases, naming direct context instead)."
    )
    
    user_content = (
        f"Company Name: {lead.company_name}\n"
        f"Website: {lead.website}\n"
        f"Dropdown Industry: {lead.industry or 'N/A'}\n"
        f"Dropdown Company Size: {lead.company_size or 'N/A'}\n"
        f"LinkedIn URL: {lead.linkedin_url or 'N/A'}\n"
        f"Instagram: {lead.instagram_handle or 'N/A'}\n"
        f"Additional Context: {lead.additional_context or 'N/A'}\n\n"
        f"--- GEMINI BROAD SWEEP RESEARCH ---\n{broad_sweep}\n\n"
        f"--- SCRAPED WEB CONTENT ---\n{scraped_content}\n"
    )

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )

    raw_content = response.choices[0].message.content
    if not raw_content:
        raise ValueError("OpenAI synthesized prompts content was empty.")
    result_json = json.loads(raw_content)
    logger.debug(f"OpenAI synthesized prompts: {json.dumps(result_json, indent=2)}")
    log_step(3, "ENRICHMENT", "6 customized prompts synthesized successfully.", "SUCCESS")
    return result_json

@api_retry_decorator("Gemini Single Category Sweep")
async def run_gemini_category_sweep(category_name: str, query: str) -> str:
    """
    Sub-helper: Runs search grounding on a single targeted prompt.
    """
    logger.info(f"Gemini deep research starting for category '{category_name}' with query: '{query}'")
    client = get_gemini_client()
    
    prompt = (
        f"Using Google Search grounding, execute this targeted research query:\n"
        f"'{query}'\n\n"
        f"Provide a detailed, factual research summary. Cite specific names, statistics, and dates where available."
    )
    
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None, 
        lambda: client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
    )
    return response.text or ""

async def run_gemini_deep_research(custom_prompts: Dict[str, str]) -> Dict[str, str]:
    """
    Step 4: Executes 6 deep-research queries in parallel via Gemini with search grounding.
    Uses asyncio.gather to optimize performance and reduce latency by up to 60%.
    """
    log_step(4, "ENRICHMENT", "Initiating Gemini deep research pass for 6 strategic verticals in parallel")
    
    async def run_single_category_sweep(category: str, query: str) -> tuple[str, str]:
        try:
            summary = await run_gemini_category_sweep(category, query)
            log_step(4, "ENRICHMENT", f"Completed category sweep: {category}", "SUCCESS")
            return category, summary
        except Exception as e:
            logger.error(f"Failed deep research category '{category}': {str(e)}")
            log_step(4, "ENRICHMENT", f"Failed category sweep: {category}", "WARNING")
            return category, f"Research failed. Insufficient online data for this vertical. Details: {str(e)}"

    # Generate concurrent coroutines for all prompts
    tasks = [run_single_category_sweep(category, query) for category, query in custom_prompts.items()]
    
    # Run all grounding sweeps concurrently
    gathered_results = await asyncio.gather(*tasks)
    
    # Map back to category results dictionary
    results = dict(gathered_results)
    
    log_step(4, "ENRICHMENT", "Gemini 6-category parallel deep research pass finished.", "SUCCESS")
    return results


@api_retry_decorator("OpenAI Content Synthesis")
async def run_openai_content_synthesis(lead: LeadInput, broad_sweep: str, scraped_content: str, deep_research: Dict[str, str]) -> EnrichedCompanyData:
    """
    Step 5: Synthesizes all gathered research into highly professional consult-grade pages, returning validated structured JSON.
    """
    log_step(5, "ENRICHMENT", f"Synthesizing final executive intelligence report contents for {lead.company_name} via GPT-4o")
    openai_client = get_openai_client()
    
    system_prompt = (
        f"You are a Senior Executive Business Intelligence Consultant writing a highly personalized, gold-tier corporate analysis for '{lead.company_name}'.\n"
        f"Your analysis must be authoritative, data-backed, actionable, and forward-looking. Avoid generic statements.\n"
        f"Write actual details, concrete strategies, and tailored pain points matching their online identity.\n\n"
        f"You MUST return your entire analysis formatted as a JSON object matching the following structure:\n"
        f"{{\n"
        f"  \"executive_summary\": \"3-4 paragraphs of a premium C-level overview of their market potential and core analysis.\",\n"
        f"  \"company_profile\": \"Detailed summary of their history, values, products, team, and operational model.\",\n"
        f"  \"industry_landscape\": \"High-level analysis of their industry vertical, macro trends, growth drivers, and market volume.\",\n"
        f"  \"competitive_positioning\": \"Analysis of their market positioning, top direct competitors, differentiation gaps, and defensibility.\",\n"
        f"  \"social_media_analysis\": \"Evaluation of brand presence, voice, engagement metrics on LinkedIn and Instagram (if provided) and overall branding feedback.\",\n"
        f"  \"growth_signals\": \"Interpretation of hiring indicators, recent funding rounds, PR statements, or expansion initiatives.\",\n"
        f"  \"pain_points\": [\n"
        f"    \"Specific operational or technological challenge 1 with deep context\",\n"
        f"    \"Specific operational or technological challenge 2 with deep context\",\n"
        f"    \"Specific operational or technological challenge 3 with deep context\",\n"
        f"    \"Specific operational or technological challenge 4 with deep context\",\n"
        f"    \"Specific operational or technological challenge 5 with deep context\"\n"
        f"  ],\n"
        f"  \"recommendations\": [\n"
        f"    {{\"title\": \"Actionable recommendation title 1\", \"description\": \"Clear actionable implementation guide (2-3 lines)\"}},\n"
        f"    {{\"title\": \"Actionable recommendation title 2\", \"description\": \"Clear actionable implementation guide (2-3 lines)\"}},\n"
        f"    ...\n"
        f"  ],\n"
        f"  \"closing_note\": \"Strategic closing statement (CTA) summarizing next steps.\"\n"
        f"}}\n\n"
        f"Important: Ensure 'pain_points' contains exactly 3 to 5 items, and 'recommendations' contains exactly 3 to 5 fully descriptive items. "
        f"Format everything professionally with perfect punctuation. No markup in strings."
    )

    user_content = (
        f"Company: {lead.company_name}\n"
        f"Website: {lead.website}\n"
        f"Self-Selected Industry: {lead.industry or 'N/A'}\n"
        f"Self-Selected Size: {lead.company_size or 'N/A'}\n"
        f"LinkedIn: {lead.linkedin_url or 'N/A'}\n"
        f"Instagram: {lead.instagram_handle or 'N/A'}\n"
        f"Additional Context: {lead.additional_context or 'N/A'}\n\n"
        f"--- INITIAL BROAD SWEEP ---\n{broad_sweep}\n\n"
        f"--- SCRAPED SITE CONTENT ---\n{scraped_content}\n\n"
        f"--- DEEP RESEARCH VERTICALS ---\n"
        f"Landscape: {deep_research.get('industry_landscape')}\n\n"
        f"Competitors: {deep_research.get('competitor_analysis')}\n\n"
        f"Social Presence: {deep_research.get('social_media_presence')}\n\n"
        f"News/Events: {deep_research.get('recent_news')}\n\n"
        f"Growth Trends: {deep_research.get('growth_signals')}\n\n"
        f"Operational Challenges: {deep_research.get('pain_points')}\n"
    )

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        response_format={"type": "json_object"},
        temperature=0.4
    )

    raw_json = response.choices[0].message.content
    if not raw_json:
        raise ValueError("OpenAI content synthesis response was empty.")
    logger.debug(f"OpenAI raw synthesis output: {raw_json}")
    
    # Parse and validate with Pydantic
    parsed_data = json.loads(raw_json)
    enriched_data = EnrichedCompanyData.model_validate(parsed_data)
    
    log_step(5, "ENRICHMENT", "Intelligence report contents successfully synthesized and validated.", "SUCCESS")
    return enriched_data

async def run_enrichment_pipeline(lead: LeadInput, scraped_content: str) -> EnrichedCompanyData:
    """
    Main orchestrator for the Multi-AI pipeline.
    Validates API configurations before running.
    """
    # Strict API key check before initiating the heavy pipeline
    missing_keys = []
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.strip() == "":
        missing_keys.append("OPENAI_API_KEY")
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.strip() == "":
        missing_keys.append("GEMINI_API_KEY")
        
    if missing_keys:
        err_msg = f"Enrichment pipeline aborted: Missing crucial API keys: {', '.join(missing_keys)}"
        logger.error(err_msg)
        raise ValueError(err_msg)

    # 1. Gemini Broad Sweep
    broad_sweep = await run_gemini_broad_sweep(lead)
    
    # 2. OpenAI analyze and prompt synthesis
    try:
        custom_prompts = await run_openai_prompt_generator(lead, broad_sweep, scraped_content)
    except Exception as e:
        logger.warning(f"GPT-4o custom prompt generation failed ({str(e)}). Falling back to static targeted prompts.")
        custom_prompts = get_default_prompts(lead.company_name, lead.website)
        
    # 3. Gemini deep sweeps for all 6 categories
    deep_research = await run_gemini_deep_research(custom_prompts)
    
    # 4. OpenAI synthesize into final formatted JSON structure
    enriched_report = await run_openai_content_synthesis(lead, broad_sweep, scraped_content, deep_research)
    
    return enriched_report
