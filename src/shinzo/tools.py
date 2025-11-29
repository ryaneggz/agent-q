"""Custom tools for the LangGraph agent"""

from typing import Any, Dict
import yfinance as yf
from langchain_core.tools import tool
from shinzo.utils import get_logger

logger = get_logger(__name__)


@tool
def get_company_info(ticker: str) -> Dict[str, Any]:
    """
    Fetch comprehensive company information by ticker symbol.
    
    Args:
        ticker: The stock ticker symbol (e.g., 'AAPL', 'GOOGL', 'MSFT')
    
    Returns:
        A dictionary containing company information including name, sector, 
        industry, market cap, description, and key financial metrics.
    """
    try:
        logger.info(f"Fetching company info for ticker: {ticker}")
        
        # Create a Ticker object
        stock = yf.Ticker(ticker)
        
        # Get company info
        info = stock.info
        
        # Extract relevant information
        company_data = {
            "ticker": ticker.upper(),
            "name": info.get("longName", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", "N/A"),
            "description": info.get("longBusinessSummary", "N/A"),
            "website": info.get("website", "N/A"),
            "employees": info.get("fullTimeEmployees", "N/A"),
            "headquarters": {
                "city": info.get("city", "N/A"),
                "state": info.get("state", "N/A"),
                "country": info.get("country", "N/A"),
            },
            "financial_metrics": {
                "current_price": info.get("currentPrice", "N/A"),
                "previous_close": info.get("previousClose", "N/A"),
                "open": info.get("open", "N/A"),
                "day_high": info.get("dayHigh", "N/A"),
                "day_low": info.get("dayLow", "N/A"),
                "volume": info.get("volume", "N/A"),
                "average_volume": info.get("averageVolume", "N/A"),
                "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
                "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
                "pe_ratio": info.get("trailingPE", "N/A"),
                "forward_pe": info.get("forwardPE", "N/A"),
                "dividend_yield": info.get("dividendYield", "N/A"),
                "beta": info.get("beta", "N/A"),
            }
        }
        
        logger.info(f"Successfully fetched info for {company_data['name']} ({ticker})")
        return company_data
        
    except Exception as e:
        error_msg = f"Error fetching company info for {ticker}: {str(e)}"
        logger.error(error_msg)
        return {
            "ticker": ticker.upper(),
            "error": error_msg,
            "name": "N/A"
        }

