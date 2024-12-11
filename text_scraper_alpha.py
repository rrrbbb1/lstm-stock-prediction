import requests
import pandas as pd
import time

api_key = 'SVCQWJEL71W30Y6D'
base_url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&apikey={api_key}"
articles = []

# Define a function to fetch articles
def fetch_articles():
    global articles
    params = {
        "function": "NEWS_SENTIMENT",
        "apikey": api_key
    }
    
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'feed' in data:
            new_articles = [
                {
                    'headline_title': article.get('title', 'N/A'),
                    'date': article.get('time_published', 'N/A'),
                    'content': article.get('summary', 'N/A')  # Assuming 'summary' contains content
                }
                for article in data['feed']
            ]
            articles.extend(new_articles)
            print(f"Fetched {len(new_articles)} articles.")
        else:
            print("No articles found in response.")
    else:
        print(f"Error: {response.status_code}")

# Fetch articles with a delay to respect rate limits
for _ in range(5):  # Adjust the range based on the number of requests you want
    fetch_articles()
    time.sleep(12)  # Sleep to respect rate limits (Alpha Vantage: 5 requests/min for free users)

# Save to CSV
if articles:
    pd.DataFrame(articles).to_csv('financial_news_all.csv', index=False)
    print(f"Saved {len(articles)} articles to financial_news_all.csv")
else:
    print("No articles to save.")