import asyncio
import os
import pandas as pd
import yfinance as yf
from datetime import datetime
from tqdm.asyncio import tqdm

# Function to fetch S&P 500 tickers and companies from Wikipedia
def get_sp500_tickers():
    sp500_url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    table = pd.read_html(sp500_url)
    sp500_table = table[0]  # The S&P 500 list is in the first table on the page

    # Dynamically identify the column for tickers and company names
    ticker_column = [col for col in sp500_table.columns if "Ticker" in col or "Symbol" in col][0]
    company_column = [col for col in sp500_table.columns if "Security" in col or "Company" in col][0]

    tickers = sp500_table[ticker_column].tolist()
    companies = sp500_table[company_column].tolist()

    print('Tickers and Companies fetched:', len(tickers))
    return tickers, companies

# Asynchronous wrapper for yf.download
async def async_download(ticker, start_date, end_date):
    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(None, lambda: yf.download(ticker, start_date, end_date, progress=False))
        return data
    except Exception as e:
        print(f"Error downloading data for {ticker}: {e}")
        return None

# Function to fetch data with retries and clean it
async def fetch_with_retries(ticker, company, start_date, end_date, retries=3, delay=1):
    for attempt in range(retries):
        data = await async_download(ticker, start_date, end_date)

        if data is not None and not data.empty:
            # Prepare clean data
            data["Company"] = company
            data = data.reset_index()  # Ensure 'Date' is a column
            data = data[["Date", "Open", "High", "Low", "Close", "Volume", "Company"]]
            data['Date'] = pd.to_datetime(data['Date'])
            data = data.values
            columns = ["Date", "Open", "High", "Low", "Close", "Volume", "Company"]
            data = pd.DataFrame(data, columns=columns)
            return data
        await asyncio.sleep(delay)

    print(f"Failed to fetch data for {ticker} after {retries} retries.")
    return pd.DataFrame()

# Main function to fetch all data
async def fetch_all_data(start_date, end_date, delay_between_requests=0.5):
    tickers, companies = get_sp500_tickers()
    results = []
    with tqdm(total=len(tickers), desc="Fetching data", dynamic_ncols=True) as pbar:
        for ticker, company in zip(tickers, companies):
            raw_data = await fetch_with_retries(ticker, company, start_date, end_date)
            if not raw_data.empty:
                results.append(raw_data)
            await asyncio.sleep(delay_between_requests)
            pbar.update(1)
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()

# Entry point
if __name__ == "__main__":
    start_date = "2017-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")

    try:
        print("Fetching S&P 500 data...")
        all_data = asyncio.run(fetch_all_data(start_date, end_date))

        if not all_data.empty:
            print("Data successfully fetched. Converting to DataFrame...")
            all_data["Date"] = pd.to_datetime(all_data["Date"])  # Ensure 'Date' is in datetime format
            all_data = all_data.sort_values(by="Date")  # Sort by date

            # Save the cleaned data to CSV
            os.makedirs("data", exist_ok=True)
            output_file = "data/sp500_prices.csv"
            all_data.to_csv(output_file, index=False)
            print(f"All data saved to '{output_file}'")
        else:
            print("No data was fetched.")
    except KeyboardInterrupt:
        print("Process interrupted by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")