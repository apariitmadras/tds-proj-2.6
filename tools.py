# tools.py

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import Dict, Any
import subprocess

async def scrape_website(url: str, output_file: str = "scraped_content.html") -> None:
    """
    Scrape the given URL using Playwright (headless browser) and save HTML.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            content = await page.content()
            with open(output_file, "w", encoding="utf-8") as f:
                await f.write(content)
        except Exception as e:
            print(f"Failed to load page {url}: {e}")
        await browser.close()

def get_relevant_data(file_name: str, css_selector: str = None) -> Dict[str, Any]:
    """
    Read the given HTML file and extract text content matching the CSS selector.
    """
    with open(file_name, encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    if css_selector:
        elements = soup.select(css_selector)
        return {"data": [el.get_text(strip=True) for el in elements]}
    else:
        return {"data": soup.get_text(strip=True)}

def answer_questions(code: str) -> str:
    """
    Execute the provided Python code string and return its stdout.
    """
    with open("temp_script.py", "w") as f:
        f.write(code)
    result = subprocess.run(["python", "temp_script.py"], capture_output=True, text=True)
    if result.stderr:
        raise RuntimeError(result.stderr)
    return result.stdout
