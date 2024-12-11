import requests
import pandas as pd

api_key = 'decb4a3a45a040f5a4476e57f3370de1'
url = f"https://newsapi.org/v2/everything?q=finance&apiKey={api_key}"

response = requests.get(url)
data = response.json()

# Extract headlines and publication dates
articles = [{'headline_title': article['title'], 'date': article['publishedAt']} for article in data['articles']]

# Save to CSV
pd.DataFrame(articles).to_csv('financial_news.csv', index=False)