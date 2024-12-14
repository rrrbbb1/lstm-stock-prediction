from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time

def scroll_page(driver, scroll_duration=10):
    """Scroll the page for a specified duration."""
    start_time = time.time()
    while time.time() - start_time < scroll_duration:
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(0.5)

def get_ecb_press_urls():
    url = "https://www.ecb.europa.eu/press/pubbydate/html/index.en.html?name_of_publication=Press%20release"
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.get(url)

    # Testing for connection
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='/press/pr/date/']"))
        )
        time.sleep(2)
    except Exception as e:
        print(f"Error while waiting for the page to load: {e}")
        driver.quit()
        return []
    
    # Scroll the page to have the maximum of dynamic content
    scroll_page(driver, scroll_duration=115)

    # Scraping content
    soup = BeautifulSoup(driver.page_source, "html.parser")
    sortwrapper = soup.find('div', class_='sort-wrapper')
    div_title_tags = sortwrapper.find_all('div', class_='title')
    filtered_div_title_tags = [el for el in div_title_tags if not el.find_parent('div', class_='accordion')]
    dt_tags = sortwrapper.find_all('dt')
    filtered_dt_tags = [el for el in dt_tags if not el.find_parent('div', class_='accordion')]
    urls_and_titles = []
    for dt_tag, title_tag in zip(filtered_dt_tags, filtered_div_title_tags):
        date = dt_tag.text.strip()
        a_tag = title_tag.find('a')
        if a_tag:
            href = a_tag.get("href")
            full_url = f"https://www.ecb.europa.eu{href}" if href.startswith("/") else href
            title = a_tag.text.strip()
            urls_and_titles.append({"date": date, "title": title, "url": full_url})
    print(f'FOUND {len(filtered_div_title_tags)} TITLES')
    print(f'FOUND {len(filtered_dt_tags)} DATES')

    driver.quit()
    return urls_and_titles

def save_to_csv(data, output_file="data/ecb_press_releases.csv"):
    # Save data to a CSV file
    if data:
        df = pd.DataFrame(data)
        df.to_csv(output_file, index=False, encoding="utf-8")
        print(f"Saved {len(data)} articles to '{output_file}'.")
    else:
        print("No articles found.")

if __name__ == "__main__":
    # Scrape and save press releases
    articles = get_ecb_press_urls()
    print(f"Found {len(articles)} articles.")
    save_to_csv(articles)