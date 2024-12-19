import yfinance as yf
import pandas as pd
from datetime import datetime

# Define the list of indices
INDICES = {
    "France - CAC 40": "^FCHI",
    "Germany - DAX 40": "^GDAXI",
    "UK - FTSE 100": "^FTSE",
    "Italy - FTSE MIB": "FTSEMIB.MI",
    "Spain - IBEX 35": "^IBEX",
    "Switzerland - SMI": "^SSMI",
    "Netherlands - AEX": "^AEX",
    "Belgium - BEL 20": "^BFX",
    "Austria - ATX": "^ATX",
    "Portugal - PSI 20": "^PSI20",
    "Sweden - OMX Stockholm 30": "^OMX",
    "Norway - OBX": "^OBX",
    "Poland - WIG20": "^WIG20",
    "Hungary - BUX": "^BUX",
    "Turkey - BIST 100": "XU100.IS",
}

tickers = list(INDICES.values())  # Extract the tickers from the dictionary

# Function to fetch Close prices and format with an Index column
def fetch_close_prices_with_index(tickers, start_date, end_date):
    try:
        # Download the data from Yahoo Finance
        data = yf.download(tickers, start=start_date, end=end_date, group_by="ticker", progress=False)
        # Extract only the Close prices
        close_prices = data.loc[:, (slice(None), "Close")]
        # Flatten the MultiIndex columns for simplicity
        close_prices.columns = [col[0] for col in close_prices.columns]
        # Melt the DataFrame to have a single column for ticker (Index)
        close_prices = close_prices.reset_index().melt(id_vars="Date", var_name="Index", value_name="Close")
        return close_prices
    except Exception as e:
        print(f"Failed to fetch data: {e}")
        return pd.DataFrame()

# Entry point
if __name__ == "__main__":
    # Define the date range
    start_date = "2017-01-03"
    end_date = datetime.now().strftime("%Y-%m-%d")

    # Fetch the Close prices with an Index column
    close_data = fetch_close_prices_with_index(tickers, start_date, end_date)

    if not close_data.empty:
        # Save the formatted data to a CSV file
        output_file = "data/european_indices.csv"
        close_data.to_csv(output_file, index=False)
        print(f"Formatted data successfully saved to {output_file}")
    else:
        print("No data was fetched.")
