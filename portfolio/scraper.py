"""
Web scraper utilities for fetching stock prices from Financial Times and Yahoo Finance.
Includes robust error handling, retry logic, and logging.
"""

import logging
import time
import locale
from decimal import Decimal
from typing import Optional, Tuple
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)


class ScraperException(Exception):
    """Base exception for scraper errors"""
    pass


class ScraperTimeoutException(ScraperException):
    """Raised when scraper times out"""
    pass


class ScraperParseException(ScraperException):
    """Raised when parsing HTML fails"""
    pass


class PriceScraper:
    """Handles price scraping with retry logic and error handling"""
    
    # FT URLs by stock type
    FT_BASE_URL = "https://markets.ft.com/data/"
    FT_URLS = {
        "etfs": "etfs/tearsheet/summary?s=",
        "fund": "funds/tearsheet/performance?s=",
        "equity": "equities/tearsheet/summary?s=",
        "curr": "currencies/tearsheet/summary?s="
    }
    
    YAHOO_BASE_URL = "https://finance.yahoo.com/quote/"
    
    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1  # seconds
    MAX_BACKOFF = 8  # seconds
    TIMEOUT = 10  # seconds
    
    # User agent to avoid being blocked
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    def __init__(self):
        """Initialize scraper with logging"""
        self.session = None
    
    def _create_session(self) -> HTMLSession:
        """Create an HTMLSession with proper headers"""
        session = HTMLSession()
        session.headers.update({'User-Agent': self.USER_AGENT})
        return session
    
    def _fetch_with_retry(self, url: str, max_retries: int = None) -> requests.Response:
        """
        Fetch URL with exponential backoff retry logic.
        
        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts
            
        Returns:
            Response object
            
        Raises:
            ScraperTimeoutException: If all retries fail due to timeout
            ScraperException: If all retries fail for other reasons
        """
        if max_retries is None:
            max_retries = self.MAX_RETRIES
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                session = self._create_session()
                logger.debug(f"Fetching URL (attempt {attempt + 1}/{max_retries}): {url}")
                
                response = session.get(url, timeout=self.TIMEOUT)
                response.raise_for_status()
                
                logger.debug(f"Successfully fetched {url}")
                return response
                
            except requests.Timeout as e:
                last_exception = e
                logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries} for {url}")
                
                if attempt < max_retries - 1:
                    backoff = min(self.INITIAL_BACKOFF * (2 ** attempt), self.MAX_BACKOFF)
                    logger.debug(f"Waiting {backoff}s before retry...")
                    time.sleep(backoff)
                else:
                    raise ScraperTimeoutException(f"Timeout after {max_retries} attempts for {url}") from e
                    
            except requests.RequestException as e:
                last_exception = e
                logger.warning(f"Request failed on attempt {attempt + 1}/{max_retries}: {e}")
                
                if attempt < max_retries - 1:
                    backoff = min(self.INITIAL_BACKOFF * (2 ** attempt), self.MAX_BACKOFF)
                    logger.debug(f"Waiting {backoff}s before retry...")
                    time.sleep(backoff)
                else:
                    raise ScraperException(f"Failed to fetch {url} after {max_retries} attempts") from e
            
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}/{max_retries}: {e}")
                
                if attempt < max_retries - 1:
                    backoff = min(self.INITIAL_BACKOFF * (2 ** attempt), self.MAX_BACKOFF)
                    time.sleep(backoff)
                else:
                    raise ScraperException(f"Unexpected error after {max_retries} attempts: {e}") from e
        
        # Should not reach here, but just in case
        raise ScraperException(f"Failed to fetch {url}") from last_exception
    
    def _convert_to_decimal(self, value_str: str) -> Decimal:
        """
        Convert locale-formatted string to Decimal.
        
        Args:
            value_str: String representation of number in current locale
            
        Returns:
            Decimal value
            
        Raises:
            ScraperParseException: If conversion fails
        """
        try:
            if not value_str or not value_str.strip():
                raise ValueError("Empty value string")
            
            value = locale.atof(value_str.strip())
            return Decimal(str(value))
        except (ValueError, TypeError) as e:
            raise ScraperParseException(f"Failed to convert '{value_str}' to decimal: {e}") from e
    
    def _parse_ft_price(self, soup: BeautifulSoup) -> Optional[Decimal]:
        """
        Parse price from Financial Times HTML.
        
        Args:
            soup: BeautifulSoup object of FT page
            
        Returns:
            Price as Decimal, or None if not found
            
        Raises:
            ScraperParseException: If parsing fails
        """
        try:
            elements = soup.find_all("span", class_='mod-ui-data-list__value')
            
            if not elements:
                raise ScraperParseException("Price element not found - FT page structure may have changed")
            
            price_element = elements[0]
            if not price_element or not price_element.string:
                raise ScraperParseException("Price element is empty")
            
            price_str = price_element.string.strip()
            price = self._convert_to_decimal(price_str)
            
            logger.debug(f"Parsed FT price: {price}")
            return price
            
        except ScraperParseException:
            raise
        except Exception as e:
            raise ScraperParseException(f"Error parsing FT price: {e}") from e
    
    def _parse_yahoo_price(self, soup: BeautifulSoup) -> Optional[Decimal]:
        """
        Parse price from Yahoo Finance HTML.
        
        Args:
            soup: BeautifulSoup object of Yahoo page
            
        Returns:
            Price as Decimal, or None if not found
            
        Raises:
            ScraperParseException: If parsing fails
        """
        try:
            price_element = soup.find("span", attrs={"data-testid": "qsp-price"})
            
            if not price_element or not price_element.string:
                raise ScraperParseException("Price element not found - Yahoo page structure may have changed")
            
            price_str = price_element.string.strip()
            price = self._convert_to_decimal(price_str)
            
            logger.debug(f"Parsed Yahoo price: {price}")
            return price
            
        except ScraperParseException:
            raise
        except Exception as e:
            raise ScraperParseException(f"Error parsing Yahoo price: {e}") from e
    
    def scrape_ft_price(self, stock_code: str, stock_type: str) -> Optional[Decimal]:
        """
        Scrape price from Financial Times.
        
        Args:
            stock_code: FT stock code (e.g., 'MSFT:USD')
            stock_type: Type of stock ('equity', 'fund', 'etfs', 'curr')
            
        Returns:
            Price as Decimal, or None if scraping fails
            
        Raises:
            ScraperException: If scraping fails after retries
        """
        if stock_type not in self.FT_URLS:
            raise ValueError(f"Unknown stock type: {stock_type}")
        
        url = self.FT_BASE_URL + self.FT_URLS[stock_type] + stock_code
        
        try:
            response = self._fetch_with_retry(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            price = self._parse_ft_price(soup)
            return price
            
        except ScraperException as e:
            logger.error(f"Failed to scrape FT price for {stock_code}: {e}")
            raise
    
    def scrape_yahoo_price(self, yahoo_code: str) -> Optional[Decimal]:
        """
        Scrape price from Yahoo Finance.
        
        Args:
            yahoo_code: Yahoo ticker code
            
        Returns:
            Price as Decimal, or None if scraping fails
            
        Raises:
            ScraperException: If scraping fails after retries
        """
        url = self.YAHOO_BASE_URL + yahoo_code
        
        try:
            response = self._fetch_with_retry(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            price = self._parse_yahoo_price(soup)
            return price
            
        except ScraperException as e:
            logger.error(f"Failed to scrape Yahoo price for {yahoo_code}: {e}")
            raise


class PerformanceScraper:
    """Handles performance data scraping from Financial Times"""
    
    FT_BASE_URL = "https://markets.ft.com/data/"
    FT_URLS = {
        "etfs": "etfs/tearsheet/performance?s=",
        "fund": "funds/tearsheet/performance?s=",
    }
    
    TIMEOUT = 10
    MAX_RETRIES = 3
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    # Column indices for performance data in FT table
    # Row 1 contains: 5y, 3y, 1y, 6m, 3m, 1m
    PERF_COLUMNS = {
        'perf_5y': 1,
        'perf_3y': 2,
        'perf_1y': 3,
        'perf_6m': 4,
        'perf_3m': 5,
        'perf_1m': 6,
    }
    
    def __init__(self):
        self.session = None
    
    def _create_session(self) -> HTMLSession:
        """Create an HTMLSession with proper headers"""
        session = HTMLSession()
        session.headers.update({'User-Agent': self.USER_AGENT})
        return session
    
    def _fetch_with_retry(self, url: str) -> requests.Response:
        """Fetch URL with retry logic"""
        last_exception = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                session = self._create_session()
                logger.debug(f"Fetching performance data (attempt {attempt + 1}): {url}")
                response = session.get(url, timeout=self.TIMEOUT)
                response.raise_for_status()
                return response
                
            except requests.Timeout as e:
                last_exception = e
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.MAX_RETRIES}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
            except requests.RequestException as e:
                last_exception = e
                logger.warning(f"Request failed on attempt {attempt + 1}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
        
        raise ScraperException(f"Failed to fetch {url} after {self.MAX_RETRIES} attempts") from last_exception
    
    def _convert_to_decimal(self, value_str: str) -> Optional[Decimal]:
        """Convert locale-formatted string to Decimal"""
        try:
            if not value_str or value_str == '--':
                return None
            # Remove trailing % sign
            clean_str = value_str.rstrip('%').strip()
            value = locale.atof(clean_str)
            return Decimal(str(value))
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert '{value_str}' to decimal: {e}")
            return None
    
    def scrape_performance(self, stock_code: str, stock_type: str) -> dict:
        """
        Scrape performance data from Financial Times.
        
        Args:
            stock_code: FT stock code
            stock_type: Type of stock ('fund' or 'etfs')
            
        Returns:
            Dictionary with performance data keys ('perf_5y', 'perf_3y', etc.)
            
        Raises:
            ScraperException: If scraping fails
        """
        if stock_type not in self.FT_URLS:
            raise ValueError(f"Performance data not available for stock type: {stock_type}")
        
        url = self.FT_BASE_URL + self.FT_URLS[stock_type] + stock_code
        perf_data = {}
        
        try:
            response = self._fetch_with_retry(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the performance table
            table_container = soup.find("div", class_='mod-ui-table--freeze-pane__scroll-container')
            if not table_container:
                raise ScraperParseException("Performance table not found - page structure may have changed")
            
            rows = table_container.find_all("tr")
            if len(rows) < 2:
                raise ScraperParseException("Not enough rows in performance table")
            
            # Data is in the second row
            perf_row = rows[1]
            columns = perf_row.find_all("td")
            
            # Extract each performance metric
            for field_name, col_index in self.PERF_COLUMNS.items():
                if col_index < len(columns):
                    value_str = columns[col_index].get_text(strip=True)
                    value = self._convert_to_decimal(value_str)
                    if value is not None:
                        perf_data[field_name] = value
                    logger.debug(f"{field_name}: {value}")
            
            return perf_data
            
        except ScraperParseException as e:
            logger.error(f"Failed to parse performance data: {e}")
            raise ScraperException(f"Parse error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error scraping performance: {e}")
            raise ScraperException(f"Unexpected error: {e}") from e
