import logging
import requests
import os
import json
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ExchangeApiClient:
    """Client for interacting with cryptocurrency exchange APIs"""
    
    def __init__(self, exchange_name="binance"):
        self.exchange_name = exchange_name.lower()
        
        # Set up exchange-specific configurations
        if self.exchange_name == "binance":
            self.base_url = "https://api.binance.com/api/v3"
            self.api_key = os.environ.get("BINANCE_API_KEY")
            self.api_secret = os.environ.get("BINANCE_API_SECRET")
        elif self.exchange_name == "coinbase":
            self.base_url = "https://api.exchange.coinbase.com"
            self.api_key = os.environ.get("COINBASE_API_KEY")
            self.api_secret = os.environ.get("COINBASE_API_SECRET")
        else:
            raise ValueError(f"Unsupported exchange: {exchange_name}")
        
        self.headers = {
            "Content-Type": "application/json",
            "X-MBX-APIKEY": self.api_key if self.exchange_name == "binance" else None
        }
        
        # Remove None values from headers
        self.headers = {k: v for k, v in self.headers.items() if v is not None}
    
    def _make_request(self, method, endpoint, params=None, data=None, auth_required=False):
        """
        Helper method to make API requests to the exchange
        
        Args:
            method (str): HTTP method (GET, POST, DELETE)
            endpoint (str): API endpoint
            params (dict, optional): URL parameters
            data (dict, optional): Data to send in the request body
            auth_required (bool): Whether authentication is required
            
        Returns:
            dict: Response data
        """
        url = f"{self.base_url}/{endpoint}"
        
        # Add authentication if required (exchange-specific)
        if auth_required:
            if self.exchange_name == "binance":
                if not params:
                    params = {}
                params["timestamp"] = int(time.time() * 1000)
                # Signature computation would go here in a real implementation
                # params["signature"] = compute_signature(params, self.api_secret)
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, params=params, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check for errors
            response.raise_for_status()
            
            # Return JSON response
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Exchange API request error ({method} {endpoint}): {str(e)}")
            return {"error": str(e), "success": False}
    
    # Market data methods
    def get_ticker(self, symbol):
        """
        Get current price ticker for a symbol
        
        Args:
            symbol (str): Trading pair symbol (e.g., "BTCUSDT")
            
        Returns:
            dict: Current price information
        """
        if self.exchange_name == "binance":
            endpoint = "ticker/24hr"
            params = {"symbol": symbol}
        elif self.exchange_name == "coinbase":
            endpoint = f"products/{symbol}/ticker"
            params = None
        
        return self._make_request("GET", endpoint, params=params)
    
    def get_klines(self, symbol, interval="1h", limit=500, start_time=None, end_time=None):
        """
        Get candlestick/kline data for a symbol
        
        Args:
            symbol (str): Trading pair symbol (e.g., "BTCUSDT")
            interval (str): Candle interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, etc.)
            limit (int): Maximum number of candles to return
            start_time (int, optional): Start time in milliseconds
            end_time (int, optional): End time in milliseconds
            
        Returns:
            list: List of candles with OHLCV data
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        
        if self.exchange_name == "binance":
            endpoint = "klines"
        elif self.exchange_name == "coinbase":
            endpoint = f"products/{symbol}/candles"
            # Adjust params for Coinbase
            params = {
                "granularity": self._convert_interval_to_seconds(interval),
                "limit": limit
            }
        
        response = self._make_request("GET", endpoint, params=params)
        
        # Format response based on exchange
        if self.exchange_name == "binance":
            # Binance returns: [timestamp, open, high, low, close, volume, ...]
            return [
                {
                    "timestamp": candle[0],
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                }
                for candle in response
            ]
        elif self.exchange_name == "coinbase":
            # Coinbase returns: [timestamp, low, high, open, close, volume]
            return [
                {
                    "timestamp": candle[0] * 1000,  # Convert to ms
                    "open": float(candle[3]),
                    "high": float(candle[2]),
                    "low": float(candle[1]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                }
                for candle in response
            ]
        
        return response
    
    def get_order_book(self, symbol, limit=100):
        """
        Get order book for a symbol
        
        Args:
            symbol (str): Trading pair symbol (e.g., "BTCUSDT")
            limit (int): Maximum number of orders to return
            
        Returns:
            dict: Order book data
        """
        if self.exchange_name == "binance":
            endpoint = "depth"
            params = {"symbol": symbol, "limit": limit}
        elif self.exchange_name == "coinbase":
            endpoint = f"products/{symbol}/book"
            params = {"level": 2}
        
        return self._make_request("GET", endpoint, params=params)
    
    def get_recent_trades(self, symbol, limit=500):
        """
        Get recent trades for a symbol
        
        Args:
            symbol (str): Trading pair symbol (e.g., "BTCUSDT")
            limit (int): Maximum number of trades to return
            
        Returns:
            list: Recent trades
        """
        if self.exchange_name == "binance":
            endpoint = "trades"
            params = {"symbol": symbol, "limit": limit}
        elif self.exchange_name == "coinbase":
            endpoint = f"products/{symbol}/trades"
            params = {"limit": limit}
        
        return self._make_request("GET", endpoint, params=params)
    
    # Helper methods
    def _convert_interval_to_seconds(self, interval):
        """Convert interval string to seconds for Coinbase API"""
        unit = interval[-1]
        value = int(interval[:-1])
        
        if unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 60 * 60
        elif unit == 'd':
            return value * 60 * 60 * 24
        
        return 3600  # Default to 1h
