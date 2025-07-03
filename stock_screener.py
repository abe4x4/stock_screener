
import pandas as pd
import yfinance as yf
from finvizfinance.screener.performance import Performance
from datetime import datetime
import time
import os

# --- Configuration ---
PREVIOUS_STOCKS_FILE = "/home/isa/code/isa-projects/stock_screener/previous_stocks.txt"

def play_alert_sound():
    """Plays a sound alert using the command line.
    This uses the 'paplay' command, which is common on PulseAudio systems (most Linux desktops).
    You can change this to any command that plays a sound file.
    """
    try:
        # A common system sound file. You can replace this with any .wav or .ogg file.
        sound_file = "/usr/share/sounds/freedesktop/stereo/bell.oga"
        if os.path.exists(sound_file):
            os.system(f"paplay {sound_file}")
        else:
            # Fallback for systems that don't have this specific sound file
            os.system("echo -e '\a'") # Simple terminal bell
    except Exception as e:
        print(f"Could not play sound alert: {e}")

def get_previous_stocks():
    """Reads the set of previously found stocks from a file."""
    if not os.path.exists(PREVIOUS_STOCKS_FILE):
        return set()
    with open(PREVIOUS_STOCKS_FILE, 'r') as f:
        return set(line.strip() for line in f)

def save_stocks(stocks):
    """Saves the current set of stocks to a file."""
    with open(PREVIOUS_STOCKS_FILE, 'w') as f:
        for stock in stocks:
            f.write(f"{stock}\n")

def screen_stocks():
    """Screens for stocks based on the defined criteria."""
    try:
        # --- 1. Initial Screening with Finviz ---
        print("--- Starting initial screening with Finviz... ---")
        filters_dict = {
            'Price': 'Under $20',
            'Float': 'Under 20M',
            'Average True Range': 'Over 0.5'
        }
        stock_screener = Performance()
        stock_screener.set_filter(filters_dict=filters_dict)
        df = stock_screener.screener_view(order='Price')
        df = df[df['Price'] >= 2]
        tickers = df['Ticker'].to_list()
        print(f"--- Found {len(tickers)} stocks in the initial screening. ---")

        # --- 2. Detailed Analysis with yfinance ---
        print("--- Performing detailed analysis with yfinance... ---")
        top_stocks = []
        for ticker in tickers:
            try:
                stock_data = yf.Ticker(ticker)
                hist = stock_data.history(period="1mo")
                if hist.empty:
                    continue
                latest = hist.iloc[-1]
                price_change_pct = ((latest['Close'] - latest['Open']) / latest['Open']) * 100
                if price_change_pct < 10:
                    continue
                avg_volume = hist['Volume'][:-1].mean()
                if latest['Volume'] < 5 * avg_volume:
                    continue
                if not stock_data.news:
                    continue
                top_stocks.append({
                    'Ticker': ticker,
                    'Price': latest['Close'],
                    'Price_Change_Pct': price_change_pct,
                    'Volume': latest['Volume'],
                    'Avg_Volume': avg_volume,
                    'News_Titles': [n.get('title', 'No Title Available') for n in stock_data.news[:2]]
                })
                time.sleep(0.5)
            except Exception as e:
                print(f"Could not process {ticker}: {e}")

        # --- 3. Ranking, Alerting, and Saving ---
        if not top_stocks:
            print("--- No stocks met all the criteria in this run. ---")
            return

        top_stocks_df = pd.DataFrame(top_stocks)
        top_stocks_df = top_stocks_df.sort_values(by='Price_Change_Pct', ascending=False)
        top_10_stocks = top_stocks_df.head(10)

        # --- Sound Alert Logic ---
        previous_stocks = get_previous_stocks()
        current_stocks = set(top_10_stocks['Ticker'])
        new_stocks = current_stocks - previous_stocks

        if new_stocks:
            print(f"--- New stocks found: {', '.join(new_stocks)} ---")
            play_alert_sound()
            # Update the file with the new complete list
            save_stocks(current_stocks)

        # --- Save the results to a CSV file ---
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = f"/home/isa/code/isa-projects/stock_screener/top_10_stocks_{timestamp}.csv"
        top_10_stocks.to_csv(output_path, index=False)

        print(f"--- Top 10 stocks for this run saved to {output_path} ---")
        print(top_10_stocks)

    except Exception as e:
        print(f"An error occurred during the screening process: {e}")

if __name__ == "__main__":
    screen_stocks()
