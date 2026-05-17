import asyncio
import re
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from backend.utils.logger import log_step, logger
from backend.utils.fallbacks import get_fallback_scraped_data

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": USER_AGENT}

def clean_html_content(html_content: str) -> str:
    """
    Parses HTML content, removes boilerplate, and extracts clean, compact text.
    """
    if not html_content or html_content.strip() == "":
        return ""
    
    soup = BeautifulSoup(html_content, "lxml")
    
    # Strip unnecessary boilerplate tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "svg", "form"]):
        tag.decompose()
        
    # Get clean text
    text = soup.get_text(separator="\n")
    
    # Remove multiple newlines and spaces
    lines = [line.strip() for line in text.splitlines()]
    clean_lines = [line for line in lines if line]
    clean_text = " ".join(clean_lines)
    
    # Compress spaces
    clean_text = re.sub(r"\s+", " ", clean_text)
    
    # Truncate content to avoid token blow-up (limit to ~3000 words)
    words = clean_text.split()
    if len(words) > 3000:
        clean_text = " ".join(words[:3000]) + " [Truncated]"
        
    return clean_text

async def scrape_page_http(client: httpx.AsyncClient, url: str) -> str:
    """
    Scrapes a page using standard async HTTP request.
    """
    logger.debug(f"HTTP request to {url}")
    response = await client.get(url, headers=HEADERS, timeout=10.0, follow_redirects=True)
    response.raise_for_status()
    return clean_html_content(response.text)

async def scrape_page_playwright(playwright_browser, url: str) -> str:
    """
    Scrapes a page using headless Playwright Chromium.
    """
    logger.debug(f"Playwright request to {url}")
    page = await playwright_browser.new_page(user_agent=USER_AGENT)
    try:
        # Navigate and wait for DOM load
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        # Give JS another brief moment to finish rendering
        await asyncio.sleep(1.5)
        content = await page.content()
        return clean_html_content(content)
    finally:
        await page.close()

async def scrape_website(base_url: str) -> str:
    """
    Scrapes homepage and discovers/scrapes core internal sub-pages (e.g. About, Services).
    Tries httpx first, falls back to Playwright Chromium.
    """
    log_step(2, "SCRAPER", f"Initiating web scrape for {base_url}")
    
    parsed_base = urlparse(base_url)
    base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
    
    # List of targeted sub-pages to fetch
    pages_to_scrape = [base_url]
    scraped_contents = []
    
    # Step 1: Fetch Homepage first and look for internal links
    homepage_html = ""
    use_playwright_fallback = False
    playwright_error = ""
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            logger.info(f"Attempting standard HTTP fetch of homepage: {base_url}")
            response = await client.get(base_url, headers=HEADERS)
            if response.status_code in [403, 429] or len(response.text.strip()) < 500:
                logger.warning(f"Standard HTTP got status {response.status_code} or sparse response. Triggering Playwright fallback.")
                use_playwright_fallback = True
            else:
                homepage_html = response.text
                scraped_contents.append(f"--- HOMEPAGE ---\n{clean_html_content(homepage_html)}")
        except Exception as e:
            logger.warning(f"Standard HTTP homepage fetch failed: {str(e)}. Triggering Playwright fallback.")
            use_playwright_fallback = True
            playwright_error = str(e)
            
    # Try scraping sub-pages if HTTP was successful
    if not use_playwright_fallback and homepage_html:
        soup = BeautifulSoup(homepage_html, "lxml")
        found_links = set()
        
        # Look for About, Services, Products, Team
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            full_url = urljoin(base_url, href)
            parsed_full = urlparse(full_url)
            
            # Ensure it is internal domain
            if parsed_full.netloc == parsed_base.netloc:
                path_lower = parsed_full.path.lower()
                if any(x in path_lower for x in ["about", "service", "product", "team", "solution"]):
                    found_links.add(full_url)
                    
        # Limit to top 3 sub-pages to optimize time/token constraints
        subpages = list(found_links)[:3]
        if subpages:
            logger.info(f"Discovered {len(subpages)} sub-pages to scrape: {subpages}")
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                for sub_url in subpages:
                    try:
                        sub_text = await scrape_page_http(client, sub_url)
                        if sub_text:
                            scraped_contents.append(f"\n--- SUBPAGE: {sub_url} ---\n{sub_text}")
                    except Exception as sub_e:
                        logger.warning(f"Failed HTTP scrape on sub-page {sub_url}: {str(sub_e)}")
                        
    # Step 2: Playwright Fallback if HTTP homepage fetch was blocked/failed
    if use_playwright_fallback:
        log_step(2, "SCRAPER", "Spawning Playwright headless browser for extraction", "WARNING")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                try:
                    logger.info(f"Playwright scraping homepage: {base_url}")
                    homepage_text = await scrape_page_playwright(browser, base_url)
                    if homepage_text:
                        scraped_contents.append(f"--- HOMEPAGE (PLAYWRIGHT) ---\n{homepage_text}")
                        
                        # Guessing standard sub-pages as fallback since we didn't parse HTML links dynamically here
                        common_sub_paths = ["/about", "/about-us", "/services", "/products"]
                        for path in common_sub_paths:
                            sub_url = urljoin(base_domain, path)
                            try:
                                logger.info(f"Playwright guessing standard subpage: {sub_url}")
                                sub_text = await scrape_page_playwright(browser, sub_url)
                                if sub_text and "404" not in sub_text and "not found" not in sub_text.lower():
                                    scraped_contents.append(f"\n--- SUBPAGE (PLAYWRIGHT): {sub_url} ---\n{sub_text}")
                            except Exception as playwright_sub_e:
                                logger.debug(f"Playwright guess subpage failed for {sub_url}: {str(playwright_sub_e)}")
                    else:
                        raise ValueError("Playwright returned empty text content")
                finally:
                    await browser.close()
        except Exception as e:
            error_msg = f"Playwright scrape failed: {str(e)}"
            log_step(2, "SCRAPER", error_msg, "ERROR")
            return get_fallback_scraped_data(base_url, error_msg)

    # Combine everything and final check
    full_scraped_text = "\n".join(scraped_contents)
    if not full_scraped_text.strip() or len(full_scraped_text.strip()) < 100:
        log_step(2, "SCRAPER", "Scraped text content is insufficient/empty. Triggering fallback.", "WARNING")
        return get_fallback_scraped_data(base_url, "Insufficient text content scraped")
        
    words_count = len(full_scraped_text.split())
    log_step(2, "SCRAPER", f"Scraping completed successfully. Scraped {words_count} words.", "SUCCESS")
    return full_scraped_text
