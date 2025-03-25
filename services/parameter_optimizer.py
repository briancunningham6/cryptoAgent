import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
from .market_analyzer import MarketAnalyzer
from .trading_api import TradingApiClient
from .openai_service import optimize_trading_parameters

logger = logging.getLogger(__name__)

class ParameterOptimizer:
    """Class for optimizing crypto trading parameters"""
    
    def __init__(self):
        self.trading_client = TradingApiClient()
        self.market_analyzer = MarketAnalyzer()
    
    def optimize_trader_parameters(self, pair_id):
        """
        Optimize trading parameters for a specific trading pair
        
        Args:
            pair_id (int): ID of the trading pair
            
        Returns:
            dict: Results of optimization
        """
        try:
            # Get trading pair details
            pair_response = self.trading_client.get_trading_pair(pair_id)
            if "error" in pair_response:
                logger.error(f"Error getting trading pair: {pair_response['error']}")
                return {"success": False, "error": pair_response['error']}
            
            pair = pair_response.get('data', {})
            
            # Get current trader configuration
            config_response = self.trading_client.get_trader_config(pair_id)
            if "error" in config_response:
                logger.error(f"Error getting trader config: {config_response['error']}")
                return {"success": False, "error": config_response['error']}
            
            current_config = config_response.get('data', {})
            
            # Get historical trades
            trades_response = self.trading_client.get_trades(pair_id=pair_id, limit=100)
            if "error" in trades_response:
                logger.error(f"Error getting trades: {trades_response['error']}")
                return {"success": False, "error": trades_response['error']}
            
            trade_history = trades_response.get('data', [])
            
            # Get current market conditions
            market_conditions = self.market_analyzer.analyze_market_conditions(pair.get('pair_name'))
            
            # Choose optimization strategy
            if len(trade_history) >= 10:
                # Use LLM for optimization with sufficient trading history
                logger.info(f"Using LLM-based optimization for {pair.get('pair_name')}")
                return self._llm_optimize(pair, current_config, trade_history, market_conditions)
            else:
                # Use rule-based optimization with limited history
                logger.info(f"Using rule-based optimization for {pair.get('pair_name')}")
                return self._rule_based_optimize(pair, current_config, trade_history, market_conditions)
        
        except Exception as e:
            logger.error(f"Error optimizing parameters: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _llm_optimize(self, pair, current_config, trade_history, market_conditions):
        """
        Use LLM (OpenAI) to optimize trading parameters
        
        Args:
            pair (dict): Trading pair information
            current_config (dict): Current trading configuration
            trade_history (list): Historical trades
            market_conditions (dict): Current market conditions
            
        Returns:
            dict: Optimization results
        """
        try:
            # Get trading pair name
            pair_name = pair.get('pair_name')
            
            # Process trade history for LLM consumption
            processed_history = self._process_trade_history(trade_history)
            
            # Get LLM-based optimization
            optimization_result = optimize_trading_parameters(
                pair_name,
                current_config,
                processed_history,
                market_conditions
            )
            
            # Validate the response
            if not optimization_result or not isinstance(optimization_result, dict):
                logger.error(f"Invalid optimization result for {pair_name}")
                return {"success": False, "error": "Invalid optimization result"}
            
            # Extract optimized parameters
            optimized_params = {
                "profit_margin": optimization_result.get("profit_margin", current_config.get("profit_margin")),
                "trade_size": optimization_result.get("trade_size", current_config.get("trade_size")),
                "max_open_time": optimization_result.get("max_open_time", current_config.get("max_open_time")),
                "stop_loss": optimization_result.get("stop_loss", current_config.get("stop_loss"))
            }
            
            # Apply sanity checks to optimized parameters
            optimized_params = self._sanitize_parameters(optimized_params, current_config)
            
            # Update trader configuration
            update_response = self.trading_client.update_trader_config(pair.get('id'), optimized_params)
            
            if "error" in update_response:
                logger.error(f"Error updating trader config: {update_response['error']}")
                return {"success": False, "error": update_response['error']}
            
            # Return success response
            return {
                "success": True,
                "optimization_type": "llm",
                "previous_config": current_config,
                "new_config": optimized_params,
                "reasoning": optimization_result.get("reasoning", "No reasoning provided"),
                "expected_improvement": optimization_result.get("expected_improvement", "Unknown")
            }
        
        except Exception as e:
            logger.error(f"Error in LLM optimization: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _rule_based_optimize(self, pair, current_config, trade_history, market_conditions):
        """
        Use rule-based approach to optimize trading parameters
        
        Args:
            pair (dict): Trading pair information
            current_config (dict): Current trading configuration
            trade_history (list): Historical trades
            market_conditions (dict): Current market conditions
            
        Returns:
            dict: Optimization results
        """
        try:
            # Get trading pair name
            pair_name = pair.get('pair_name')
            
            # Initialize optimized parameters
            optimized_params = {
                "profit_margin": current_config.get("profit_margin", 0.5),
                "trade_size": current_config.get("trade_size", 0.01),
                "max_open_time": current_config.get("max_open_time", 48),
                "stop_loss": current_config.get("stop_loss")
            }
            
            reasoning = []
            
            # Adjust profit margin based on market conditions
            trend = market_conditions.get("trend", {}).get("direction", "sideways")
            trend_strength = market_conditions.get("trend", {}).get("strength", 0.5)
            volatility = market_conditions.get("volatility", 10)
            
            # In strong uptrends, we can be more aggressive with profit margin
            if trend == "up" and trend_strength > 0.7:
                optimized_params["profit_margin"] = min(2.0, optimized_params["profit_margin"] * 1.2)
                reasoning.append("Increased profit margin due to strong uptrend")
            
            # In strong downtrends, be more conservative
            elif trend == "down" and trend_strength > 0.7:
                optimized_params["profit_margin"] = max(0.1, optimized_params["profit_margin"] * 0.8)
                reasoning.append("Decreased profit margin due to strong downtrend")
            
            # Adjust trade size based on volatility
            if volatility > 20:
                # High volatility, reduce trade size
                optimized_params["trade_size"] = max(0.001, optimized_params["trade_size"] * 0.9)
                reasoning.append("Decreased trade size due to high volatility")
            elif volatility < 5:
                # Low volatility, consider increasing trade size
                optimized_params["trade_size"] = min(0.1, optimized_params["trade_size"] * 1.1)
                reasoning.append("Increased trade size due to low volatility")
            
            # Adjust max open time based on trend
            if trend == "sideways":
                # Sideways markets may take longer to hit profit targets
                optimized_params["max_open_time"] = min(96, int(optimized_params["max_open_time"] * 1.2))
                reasoning.append("Increased max open time due to sideways market")
            elif trend == "up" and trend_strength > 0.5:
                # Strong uptrends should hit profit targets quicker
                optimized_params["max_open_time"] = max(12, int(optimized_params["max_open_time"] * 0.8))
                reasoning.append("Decreased max open time due to uptrend")
            
            # Add stop loss for downtrends if not already set
            if trend == "down" and optimized_params["stop_loss"] is None:
                optimized_params["stop_loss"] = 5.0
                reasoning.append("Added stop loss due to downtrend")
            
            # Apply sanity checks to optimized parameters
            optimized_params = self._sanitize_parameters(optimized_params, current_config)
            
            # Update trader configuration
            update_response = self.trading_client.update_trader_config(pair.get('id'), optimized_params)
            
            if "error" in update_response:
                logger.error(f"Error updating trader config: {update_response['error']}")
                return {"success": False, "error": update_response['error']}
            
            # Return success response
            return {
                "success": True,
                "optimization_type": "rule_based",
                "previous_config": current_config,
                "new_config": optimized_params,
                "reasoning": " ".join(reasoning),
                "expected_improvement": "Adjusted parameters based on current market conditions"
            }
        
        except Exception as e:
            logger.error(f"Error in rule-based optimization: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _process_trade_history(self, trade_history):
        """
        Process trade history for LLM consumption
        
        Args:
            trade_history (list): Raw trade history
            
        Returns:
            list: Processed trade history
        """
        processed = []
        
        for trade in trade_history:
            # Calculate profit/loss if available
            profit_loss = trade.get('profit_loss')
            
            # Calculate duration for closed trades
            duration_hours = None
            if trade.get('opened_at') and trade.get('closed_at'):
                opened = datetime.fromisoformat(trade.get('opened_at').replace('Z', '+00:00'))
                closed = datetime.fromisoformat(trade.get('closed_at').replace('Z', '+00:00'))
                duration_hours = (closed - opened).total_seconds() / 3600
            
            processed_trade = {
                "id": trade.get('id'),
                "status": trade.get('status'),
                "entry_price": trade.get('entry_price'),
                "target_price": trade.get('target_price'),
                "size": trade.get('size'),
                "profit_loss": profit_loss,
                "duration_hours": duration_hours
            }
            
            processed.append(processed_trade)
        
        return processed
    
    def _sanitize_parameters(self, params, current_config):
        """
        Apply sanity checks to optimized parameters
        
        Args:
            params (dict): Optimized parameters
            current_config (dict): Current configuration
            
        Returns:
            dict: Sanitized parameters
        """
        # Define limits
        limits = {
            "profit_margin": (0.1, 5.0),  # Between 0.1% and 5%
            "trade_size": (0.001, 0.1),   # Between 0.001 and 0.1
            "max_open_time": (1, 168),    # Between 1 hour and 7 days
            "stop_loss": (1.0, 15.0)      # Between 1% and 15%
        }
        
        sanitized = {}
        
        # Apply limits to each parameter
        for param, value in params.items():
            if param in limits and value is not None:
                min_val, max_val = limits[param]
                sanitized[param] = max(min_val, min(max_val, value))
            else:
                sanitized[param] = value
        
        # Ensure we're not changing parameters too drastically from current config
        max_change_pct = 0.3  # Maximum 30% change at a time
        
        for param in ["profit_margin", "trade_size", "max_open_time"]:
            current_value = current_config.get(param)
            if current_value and sanitized[param]:
                max_change = current_value * max_change_pct
                upper_limit = current_value + max_change
                lower_limit = current_value - max_change
                sanitized[param] = max(lower_limit, min(upper_limit, sanitized[param]))
        
        return sanitized
