from bs4 import BeautifulSoup
import pandas as pd
import re
from playwright.async_api import async_playwright
import asyncio
import requests
from tqdm import tqdm

async def get_BIS_press_urls():
    """Scrape all BIS press release URLs and their dates using Playwright's Async API."""
    articles = []  # List to store articles with URLs and dates

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Launch the browser in headless mode
        page = await browser.new_page()  # Open a new page
        
        for k in tqdm(range(1, 717)):  # Iterate through pages
            url = f"https://www.bis.org/cbspeeches/index.htm?cbspeeches_page={k}"            
            # Navigate to the page
            await page.goto(url)
            await asyncio.sleep(0.5)  # Add a delay to ensure the page fully loads

            # Extract rendered HTML
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            rows = soup.find_all('tr', class_='item')
            for row in rows:
                # Extract the date
                date_cell = row.find('td', class_='item_date')
                date = date_cell.get_text(strip=True) if date_cell else "No date available"
                # Extract the URL
                link = row.find('a', href=re.compile(r"^/review/r\d{6}[a-z]?.htm$"))
                if link and link.get('href'):
                    url = f"https://www.bis.org{link['href']}"
                    title = link.get_text(strip=True)
                else:
                    url = None
                    title = "No title available"

                articles.append({
                    "date": date,
                    "url": url,
                    "title": title
                })

        await browser.close()
    return articles

def get_text_from_url(url):
    """Visit a URL and retrieve the text of all <p> tags."""
    if not url:
        print("Error: No URL provided.")  # Log error for missing URL
        return ""

    # Perform the GET request
    response = requests.get(url, timeout=500)
    if response.status_code != 200:
        print(f"Error fetching content from {url}: Status code {response.status_code}")
        return ""

    soup = BeautifulSoup(response.text, "html.parser")

    # Find all <p> tags on the page
    paragraphs = soup.find_all('p')
    if not paragraphs:
        print(f"No <p> tags found on {url}")
        return ""

    # Combine the text from all <p> tags
    text = " ".join(p.get_text(strip=True) for p in paragraphs)
    return text

def save_to_csv(data, output_file="data/bis_press_releases.csv"):
    """Save data (URLs, dates, titles, and text content) to a CSV file."""
    if not data:
        print("No data found to save.")
        return

    df = pd.DataFrame(data)  # Create a DataFrame with the articles
    df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"Saved {len(data)} entries to '{output_file}'.")

async def main():
    # Scrape press release URLs
    articles = await get_BIS_press_urls()
    print(f"Found {len(articles)} articles. Start scraping content...")

    # Retrieve text content from each URL
    for article in tqdm(articles):
        if article['url']:
            content = get_text_from_url(article['url'])  # Pass only the URL to the function
            article["content"] = content  # Add the retrieved content to the article dictionary
        else:
            print(f"Skipping article with missing URL: {article}")  # Debug: Missing URL

    # Save the articles with content to a CSV
    save_to_csv(articles)

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
