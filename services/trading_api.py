import logging
import requests
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class TradingApiClient:
    """Client for interacting with the crypto trading application API"""
    
    def __init__(self):
        self.base_url = os.environ.get("TRADING_API_URL", "http://localhost:8000/api")
        self.api_key = os.environ.get("TRADING_API_KEY")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """
        Helper method to make API requests
        
        Args:
            method (str): HTTP method (GET, POST, PUT, DELETE)
            endpoint (str): API endpoint
            data (dict, optional): Data to send in the request body
            params (dict, optional): URL parameters
            
        Returns:
            dict: Response data
        """
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check for errors
            response.raise_for_status()
            
            # Return JSON response
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Trading API request error ({method} {endpoint}): {str(e)}")
            return {"error": str(e), "success": False}
    
    # Trading pair methods
    def get_trading_pairs(self):
        """Get all available trading pairs"""
        return self._make_request("GET", "trading-pairs")
    
    def get_trading_pair(self, pair_id):
        """Get details for a specific trading pair"""
        return self._make_request("GET", f"trading-pairs/{pair_id}")
    
    # Trading configuration methods
    def get_trader_config(self, pair_id):
        """Get trading configuration for a specific pair"""
        return self._make_request("GET", f"trader-config/{pair_id}")
    
    def update_trader_config(self, pair_id, config_data):
        """
        Update trading configuration parameters
        
        Args:
            pair_id (int): ID of the trading pair
            config_data (dict): Configuration parameters to update
                Example: {
                    "profit_margin": 0.5,
                    "trade_size": 0.01,
                    "max_open_time": 48,
                    "stop_loss": 5.0
                }
        """
        return self._make_request("PUT", f"trader-config/{pair_id}", data=config_data)
    
    # Trade methods
    def get_trades(self, pair_id=None, status=None, limit=100):
        """
        Get trades with optional filtering
        
        Args:
            pair_id (int, optional): Filter by trading pair ID
            status (str, optional): Filter by trade status (open, closed, cancelled)
            limit (int, optional): Maximum number of trades to return
        """
        params = {"limit": limit}
        if pair_id:
            params["pair_id"] = pair_id
        if status:
            params["status"] = status
            
        return self._make_request("GET", "trades", params=params)
    
    def get_trade(self, trade_id):
        """Get details for a specific trade"""
        return self._make_request("GET", f"trades/{trade_id}")
    
    def place_trade(self, pair_id, trade_data):
        """
        Place a new trade
        
        Args:
            pair_id (int): ID of the trading pair
            trade_data (dict): Trade parameters
                Example: {
                    "size": 0.01,
                    "entry_price": 50000.0,
                    "ai_recommended": True,
                    "recommendation_reason": "Favorable market conditions"
                }
        """
        data = {
            "pair_id": pair_id,
            **trade_data
        }
        return self._make_request("POST", "trades", data=data)
    
    def cancel_trade(self, trade_id, reason):
        """
        Cancel an open trade
        
        Args:
            trade_id (int): ID of the trade to cancel
            reason (str): Reason for cancellation
        """
        data = {"reason": reason}
        return self._make_request("PUT", f"trades/{trade_id}/cancel", data=data)
    
    # Trader status methods
    def get_trader_status(self, pair_id):
        """
        Get the status of a trader for a specific pair
        
        Args:
            pair_id (int): ID of the trading pair
            
        Returns:
            dict: Trader status information including open trades, 
                 last trade date, performance metrics, etc.
        """
        return self._make_request("GET", f"trader-status/{pair_id}")
    
    def get_all_traders_status(self):
        """Get status for all traders"""
        return self._make_request("GET", "trader-status")
