"""
Data fetcher: yfinance (OHLCV + technicals), Wikimedia pageviews,
pytrends (Google Trends), EODHD sentiment.
Mirrors thesis inputs, adapted for S&P 500 / free APIs.
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from pytrends.request import TrendReq

logger = logging.getLogger(__name__)

EODHD_API_KEY = os.getenv("EODHD_API_KEY", "")

SP100_TICKERS = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK-B", "JPM", "UNH",
    "V", "XOM", "LLY", "JNJ", "MA", "PG", "HD", "AVGO", "MRK", "CVX",
    "ABBV", "COST", "PEP", "ADBE", "WMT", "BAC", "KO", "MCD", "TMO", "CSCO",
    "ACN", "CRM", "ABT", "PFE", "LIN", "NFLX", "NKE", "TXN", "DHR", "AMD",
    "WFC", "PM", "ORCL", "NEE", "INTC", "QCOM", "UNP", "MS", "RTX", "HON",
    "IBM", "AMGN", "CAT", "SBUX", "GE", "INTU", "SPGI", "GS", "LOW", "AMAT",
    "DE", "AXP", "ELV", "BKNG", "ISRG", "VRTX", "MDLZ", "ADI", "PLD", "GILD",
    "ADP", "LRCX", "TJX", "MMC", "SYK", "BLK", "CI", "CB", "MO", "DUK",
    "SO", "ZTS", "CME", "EOG", "ITW", "COP", "BSX", "NOC", "F", "GM",
    "USB", "TGT", "PNC", "MMM", "ETN", "EMR", "COF", "MET", "AON", "SLB",
]

WIKI_TITLES = {
    "AAPL": "Apple_Inc.", "MSFT": "Microsoft", "AMZN": "Amazon_(company)",
    "NVDA": "Nvidia", "GOOGL": "Alphabet_Inc.", "META": "Meta_Platforms",
    "TSLA": "Tesla,_Inc.", "JPM": "JPMorgan_Chase", "UNH": "UnitedHealth_Group",
    "V": "Visa_Inc.", "XOM": "ExxonMobil", "JNJ": "Johnson_%26_Johnson",
    "PG": "Procter_%26_Gamble", "HD": "The_Home_Depot", "MRK": "Merck_%26_Co.",
    "CVX": "Chevron_Corporation", "KO": "The_Coca-Cola_Company", "MCD": "McDonald%27s",
    "WMT": "Walmart", "BAC": "Bank_of_America", "PFE": "Pfizer",
    "NFLX": "Netflix", "NKE": "Nike,_Inc.", "IBM": "IBM", "AMGN": "Amgen",
    "CAT": "Caterpillar_Inc.", "SBUX": "Starbucks", "GS": "Goldman_Sachs",
    "INTC": "Intel", "QCOM": "Qualcomm", "GE": "General_Electric",
}


def fetch_financial_data(ticker: str, start: str, end: str) -> Optional[pd.DataFrame]:
    """Fetch OHLCV from yfinance and compute SMA50, MACD, RSI."""
    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty:
            return None

        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.columns = ["Open", "High", "Low", "Close", "Volume"]
        df.index.name = "Date"

        # SMA 50
        df["SMA50"] = df["Close"].rolling(window=50).mean()

        # MACD
        exp12 = df["Close"].ewm(span=12, adjust=False).mean()
        exp26 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = exp12 - exp26

        # RSI
        delta = df["Close"].diff(1)
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14, min_periods=1).mean()
        avg_loss = loss.rolling(window=14, min_periods=1).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        df["RSI"] = 100 - (100 / (1 + rs))

        df.fillna(method="ffill", inplace=True)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        logger.error(f"Financial data fetch failed for {ticker}: {e}")
        return None


def fetch_wikipedia_pageviews(ticker: str, start: str, end: str) -> Optional[pd.Series]:
    """Fetch Wikipedia daily pageviews for a ticker (if mapping exists)."""
    title = WIKI_TITLES.get(ticker)
    if not title:
        return None

    start_fmt = start.replace("-", "")
    end_fmt = end.replace("-", "")
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"en.wikipedia/all-access/all-agents/{title}/daily/{start_fmt}/{end_fmt}"
    )
    headers = {
        "User-Agent": "Mozilla/5.0",
        "From": "trading-bot@example.com",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        items = resp.json().get("items", [])
        records = {
            pd.to_datetime(item["timestamp"], format="%Y%m%d%H"): item["views"]
            for item in items
        }
        return pd.Series(records, name="wiki_views")
    except Exception as e:
        logger.error(f"Wikipedia fetch failed for {ticker}: {e}")
        return None


def fetch_google_trends(ticker: str, start: str, end: str) -> Optional[pd.Series]:
    """Fetch Google Trends relative hit rate for a ticker."""
    company_names = {
        "AAPL": "Apple iPhone", "MSFT": "Microsoft", "AMZN": "Amazon",
        "NVDA": "Nvidia GPU", "GOOGL": "Google", "META": "Meta Facebook",
        "TSLA": "Tesla", "JPM": "JPMorgan", "V": "Visa card",
        "XOM": "ExxonMobil", "KO": "Coca-Cola", "MCD": "McDonald's",
        "WMT": "Walmart", "PFE": "Pfizer", "NFLX": "Netflix",
        "NKE": "Nike", "IBM": "IBM", "SBUX": "Starbucks",
    }
    keyword = company_names.get(ticker)
    if not keyword:
        return None

    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        pytrends.build_payload([keyword], timeframe=f"{start} {end}", geo="")
        df = pytrends.interest_over_time()
        if df.empty:
            return None
        series = df[keyword].resample("D").ffill()
        series.name = "google_trends"
        return series
    except Exception as e:
        logger.error(f"Google Trends fetch failed for {ticker}: {e}")
        return None


def fetch_sentiment(ticker: str, start: str, end: str) -> Optional[pd.Series]:
    """Fetch EODHD news sentiment score [-1, 1]."""
    if not EODHD_API_KEY:
        return None
    try:
        url = (
            f"https://eodhd.com/api/sentiments"
            f"?s={ticker}&from={start}&to={end}"
            f"&api_token={EODHD_API_KEY}&fmt=json"
        )
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        records = {}
        for symbol_data in data.values():
            for item in symbol_data:
                date = pd.to_datetime(item.get("date"))
                score = item.get("normalized")
                if date and score is not None:
                    records[date] = score
        if not records:
            return None
        series = pd.Series(records, name="sentiment")
        series = series.resample("D").mean().ffill()
        return series
    except Exception as e:
        logger.error(f"Sentiment fetch failed for {ticker}: {e}")
        return None


def build_feature_dataframe(
    ticker: str,
    start: str,
    end: str,
    include_wiki: bool = True,
    include_trends: bool = True,
    include_sentiment: bool = True,
) -> Optional[pd.DataFrame]:
    """
    Assemble full feature matrix for a ticker.
    Columns: Close, SMA50, MACD, RSI, [wiki_views], [google_trends], [sentiment]
    """
    fin = fetch_financial_data(ticker, start, end)
    if fin is None:
        return None

    df = fin[["Close", "SMA50", "MACD", "RSI"]].copy()

    if include_wiki:
        wiki = fetch_wikipedia_pageviews(ticker, start, end)
        if wiki is not None:
            df = df.join(wiki, how="left")
            df["wiki_views"] = df["wiki_views"].fillna(method="ffill").fillna(0)
            # Normalize to [0,1]
            max_val = df["wiki_views"].max()
            if max_val > 0:
                df["wiki_views"] /= max_val

    if include_trends:
        trends = fetch_google_trends(ticker, start, end)
        if trends is not None:
            df = df.join(trends, how="left")
            df["google_trends"] = df["google_trends"].fillna(method="ffill").fillna(0)
            df["google_trends"] /= 100.0  # pytrends gives 0-100

    if include_sentiment:
        sentiment = fetch_sentiment(ticker, start, end)
        if sentiment is not None:
            df = df.join(sentiment, how="left")
            df["sentiment"] = df["sentiment"].fillna(method="ffill").fillna(0)

    df.fillna(method="ffill", inplace=True)
    df.dropna(inplace=True)
    return df
