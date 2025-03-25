import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from .trading_api import TradingApiClient
from .market_analyzer import MarketAnalyzer
from .openai_service import detect_trader_issues

logger = logging.getLogger(__name__)

class TraderMonitor:
    """Class for monitoring crypto trader activity and detecting issues"""
    
    def __init__(self):
        self.trading_client = TradingApiClient()
        self.market_analyzer = MarketAnalyzer()
    
    def monitor_all_traders(self):
        """
        Monitor all traders and detect issues
        
        Returns:
            dict: Monitoring results for all traders
        """
        try:
            # Get all traders status
            traders_response = self.trading_client.get_all_traders_status()
            if "error" in traders_response:
                logger.error(f"Error getting traders status: {traders_response['error']}")
                return {"success": False, "error": traders_response['error']}
            
            traders = traders_response.get('data', [])
            
            # Check each trader
            results = []
            for trader in traders:
                pair_id = trader.get('pair_id')
                result = self.check_trader(pair_id)
                results.append(result)
            
            # Return aggregated results
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "traders_checked": len(results),
                "traders_with_issues": sum(1 for r in results if r.get('issues_detected', False)),
                "results": results
            }
        
        except Exception as e:
            logger.error(f"Error monitoring traders: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_trader(self, pair_id):
        """
        Check a specific trader for issues
        
        Args:
            pair_id (int): ID of the trading pair
            
        Returns:
            dict: Trader check results
        """
        try:
            # Get trading pair details
            pair_response = self.trading_client.get_trading_pair(pair_id)
            if "error" in pair_response:
                logger.error(f"Error getting trading pair: {pair_response['error']}")
                return {"success": False, "error": pair_response['error']}
            
            pair = pair_response.get('data', {})
            pair_name = pair.get('pair_name')
            
            # Get trader status
            status_response = self.trading_client.get_trader_status(pair_id)
            if "error" in status_response:
                logger.error(f"Error getting trader status: {status_response['error']}")
                return {"success": False, "error": status_response['error']}
            
            trader_status = status_response.get('data', {})
            
            # Get trading history
            trades_response = self.trading_client.get_trades(pair_id=pair_id, limit=100)
            if "error" in trades_response:
                logger.error(f"Error getting trades: {trades_response['error']}")
                return {"success": False, "error": trades_response['error']}
            
            trades = trades_response.get('data', [])
            
            # Calculate key metrics for monitoring
            trader_data = self._calculate_trader_metrics(trader_status, trades)
            
            # Perform checks on the trader
            check_results = self._perform_trader_checks(trader_data, pair_name, pair)
            
            # Use LLM to detect complex issues if there are already some issues detected
            if check_results.get('basic_issues_detected', False):
                # Use OpenAI to perform deeper analysis
                llm_analysis = detect_trader_issues(pair_name, trader_data)
                
                # Merge basic checks with LLM analysis
                check_results['llm_analysis'] = llm_analysis
                check_results['issues_detected'] = llm_analysis.get('issues_detected', False) or check_results.get('basic_issues_detected', False)
                
                # Add recommended actions from LLM
                check_results['recommended_actions'] = llm_analysis.get('recommended_actions', [])
                check_results['severity'] = llm_analysis.get('severity', 'low')
            else:
                check_results['issues_detected'] = check_results.get('basic_issues_detected', False)
                check_results['recommended_actions'] = check_results.get('basic_recommended_actions', [])
                check_results['severity'] = 'low'
            
            # Clear redundant fields
            if 'basic_issues_detected' in check_results:
                del check_results['basic_issues_detected']
            if 'basic_recommended_actions' in check_results:
                del check_results['basic_recommended_actions']
            
            # Add pair information
            check_results['pair_id'] = pair_id
            check_results['pair_name'] = pair_name
            check_results['success'] = True
            
            return check_results
        
        except Exception as e:
            logger.error(f"Error checking trader {pair_id}: {str(e)}")
            return {
                "success": False,
                "pair_id": pair_id,
                "error": str(e),
                "issues_detected": True,
                "issue_summary": f"Error during trader check: {str(e)}",
                "severity": "medium",
                "recommended_actions": ["manual_investigation"]
            }
    
    def check_inactive_traders(self, inactivity_threshold_hours=24):
        """
        Check for inactive traders that haven't placed trades recently
        
        Args:
            inactivity_threshold_hours (int): Hours of inactivity to trigger a check
            
        Returns:
            dict: Results with inactive traders and recommendations
        """
        try:
            # Get all traders status
            traders_response = self.trading_client.get_all_traders_status()
            if "error" in traders_response:
                logger.error(f"Error getting traders status: {traders_response['error']}")
                return {"success": False, "error": traders_response['error']}
            
            traders = traders_response.get('data', [])
            
            inactive_traders = []
            for trader in traders:
                pair_id = trader.get('pair_id')
                pair_name = trader.get('pair_name')
                last_trade_time = trader.get('last_trade_time')
                
                # Check if trader is inactive
                is_inactive = False
                
                if not last_trade_time:
                    # No trades ever placed
                    is_inactive = True
                    inactivity_duration = "never active"
                else:
                    # Convert to datetime
                    last_trade_datetime = datetime.fromisoformat(last_trade_time.replace('Z', '+00:00'))
                    hours_since_last_trade = (datetime.utcnow() - last_trade_datetime).total_seconds() / 3600
                    
                    if hours_since_last_trade > inactivity_threshold_hours:
                        is_inactive = True
                        inactivity_duration = f"{int(hours_since_last_trade)} hours"
                
                if is_inactive:
                    # Check market conditions for this pair
                    market_conditions = self.market_analyzer.analyze_market_conditions(pair_name)
                    
                    trading_recommended = market_conditions.get('trading_recommended', False)
                    recommendation = "place_trade" if trading_recommended else "wait"
                    
                    inactive_traders.append({
                        "pair_id": pair_id,
                        "pair_name": pair_name,
                        "inactivity_duration": inactivity_duration,
                        "current_open_trades": trader.get('open_trades', 0),
                        "max_concurrent_trades": trader.get('max_concurrent_trades', 0),
                        "market_conditions": {
                            "trend": market_conditions.get('trend', {}).get('direction', 'unknown'),
                            "volatility": market_conditions.get('volatility', 0),
                            "trading_recommended": trading_recommended
                        },
                        "recommendation": recommendation,
                        "reasoning": market_conditions.get('reasoning', "No market analysis available")
                    })
            
            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "inactive_traders_count": len(inactive_traders),
                "inactive_traders": inactive_traders,
                "inactivity_threshold_hours": inactivity_threshold_hours
            }
        
        except Exception as e:
            logger.error(f"Error checking inactive traders: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def place_trade_for_inactive_trader(self, pair_id):
        """
        Place a trade for an inactive trader if market conditions are favorable
        
        Args:
            pair_id (int): ID of the trading pair
            
        Returns:
            dict: Results of the trade placement
        """
        try:
            # Get trading pair details
            pair_response = self.trading_client.get_trading_pair(pair_id)
            if "error" in pair_response:
                logger.error(f"Error getting trading pair: {pair_response['error']}")
                return {"success": False, "error": pair_response['error']}
            
            pair = pair_response.get('data', {})
            pair_name = pair.get('pair_name')
            
            # Get trader status
            status_response = self.trading_client.get_trader_status(pair_id)
            if "error" in status_response:
                logger.error(f"Error getting trader status: {status_response['error']}")
                return {"success": False, "error": status_response['error']}
            
            trader_status = status_response.get('data', {})
            
            # Check if trader has room for more trades
            open_trades = trader_status.get('open_trades', 0)
            max_trades = trader_status.get('max_concurrent_trades', 0)
            
            if open_trades >= max_trades:
                return {
                    "success": False,
                    "error": f"Trader for {pair_name} already has maximum trades open ({open_trades}/{max_trades})"
                }
            
            # Check market conditions
            market_conditions = self.market_analyzer.analyze_market_conditions(pair_name)
            
            if not market_conditions.get('trading_recommended', False):
                return {
                    "success": False,
                    "error": f"Market conditions for {pair_name} are not favorable for trading",
                    "market_conditions": market_conditions.get('trend', {}),
                    "reasoning": market_conditions.get('reasoning', "No market analysis available")
                }
            
            # Get trader configuration
            config_response = self.trading_client.get_trader_config(pair_id)
            if "error" in config_response:
                logger.error(f"Error getting trader config: {config_response['error']}")
                return {"success": False, "error": config_response['error']}
            
            trader_config = config_response.get('data', {})
            
            # Get current ticker
            ticker_response = self.market_analyzer.exchange_client.get_ticker(pair_name)
            if "error" in ticker_response:
                logger.error(f"Error getting ticker: {ticker_response['error']}")
                return {"success": False, "error": ticker_response['error']}
            
            # Get current price
            current_price = float(ticker_response.get('lastPrice', ticker_response.get('price', 0)))
            
            # Calculate target price based on profit margin
            profit_margin = trader_config.get('profit_margin', 0.5) / 100  # Convert to decimal
            target_price = current_price * (1 + profit_margin)
            
            # Prepare trade data
            trade_data = {
                "size": trader_config.get('trade_size', 0.01),
                "entry_price": current_price,
                "target_price": target_price,
                "ai_recommended": True,
                "recommendation_reason": f"Trade placed due to inactivity and favorable market conditions. {market_conditions.get('reasoning', '')}"
            }
            
            # Place the trade
            trade_response = self.trading_client.place_trade(pair_id, trade_data)
            
            if "error" in trade_response:
                logger.error(f"Error placing trade: {trade_response['error']}")
                return {"success": False, "error": trade_response['error']}
            
            return {
                "success": True,
                "message": f"Successfully placed trade for inactive trader {pair_name}",
                "trade_data": trade_response.get('data', {}),
                "market_conditions": {
                    "trend": market_conditions.get('trend', {}).get('direction', 'unknown'),
                    "volatility": market_conditions.get('volatility', 0),
                    "reasoning": market_conditions.get('reasoning', "No market analysis available")
                }
            }
        
        except Exception as e:
            logger.error(f"Error placing trade for inactive trader: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _calculate_trader_metrics(self, trader_status, trades):
        """
        Calculate key metrics for trader monitoring
        
        Args:
            trader_status (dict): Trader status information
            trades (list): Trade history
            
        Returns:
            dict: Calculated metrics
        """
        # Initialize metrics
        metrics = {
            "open_trades": trader_status.get('open_trades', 0),
            "max_concurrent_trades": trader_status.get('max_concurrent_trades', 0),
            "last_trade_date": trader_status.get('last_trade_time'),
            "recent_issues": trader_status.get('recent_issues', [])
        }
        
        # Process trades if available
        if trades:
            # Calculate success rate
            closed_trades = [t for t in trades if t.get('status') == 'closed']
            successful_trades = [t for t in closed_trades if t.get('profit_loss', 0) > 0]
            
            if closed_trades:
                metrics['success_rate'] = (len(successful_trades) / len(closed_trades)) * 100
                metrics['failed_rate'] = ((len(closed_trades) - len(successful_trades)) / len(closed_trades)) * 100
            else:
                metrics['success_rate'] = 0
                metrics['failed_rate'] = 0
            
            # Calculate average profit/loss
            if closed_trades:
                profit_losses = [t.get('profit_loss', 0) for t in closed_trades]
                metrics['avg_profit_loss'] = sum(profit_losses) / len(closed_trades)
            else:
                metrics['avg_profit_loss'] = 0
            
            # Calculate average trade duration
            durations = []
            for trade in closed_trades:
                if trade.get('opened_at') and trade.get('closed_at'):
                    opened = datetime.fromisoformat(trade.get('opened_at').replace('Z', '+00:00'))
                    closed = datetime.fromisoformat(trade.get('closed_at').replace('Z', '+00:00'))
                    duration_hours = (closed - opened).total_seconds() / 3600
                    durations.append(duration_hours)
            
            if durations:
                metrics['avg_duration'] = sum(durations) / len(durations)
            else:
                metrics['avg_duration'] = 0
            
            # Get recent trades data
            recent_trades = sorted(trades, key=lambda x: x.get('opened_at', ''), reverse=True)[:10]
            metrics['recent_trades'] = recent_trades
        
        return metrics
    
    def _perform_trader_checks(self, trader_data, pair_name, pair_info):
        """
        Perform basic checks to detect trader issues
        
        Args:
            trader_data (dict): Trader metrics and data
            pair_name (str): Name of the trading pair
            pair_info (dict): Additional information about the trading pair
            
        Returns:
            dict: Check results
        """
        issues = []
        recommended_actions = []
        
        # Check 1: No trade activity for a long time
        if trader_data.get('last_trade_date'):
            last_trade_datetime = datetime.fromisoformat(trader_data.get('last_trade_date').replace('Z', '+00:00'))
            hours_since_last_trade = (datetime.utcnow() - last_trade_datetime).total_seconds() / 3600
            
            if hours_since_last_trade > 72:  # 3 days
                issues.append(f"No trading activity for {int(hours_since_last_trade)} hours")
                recommended_actions.append("check_market_conditions")
                recommended_actions.append("consider_manual_trade")
        else:
            issues.append("No trading history found")
            recommended_actions.append("check_configuration")
        
        # Check 2: Low success rate
        if trader_data.get('success_rate', 100) < 30 and trader_data.get('recent_trades'):
            issues.append(f"Low success rate: {trader_data.get('success_rate', 0):.2f}%")
            recommended_actions.append("review_trading_parameters")
            recommended_actions.append("check_market_conditions")
        
        # Check 3: Negative average profit/loss
        if trader_data.get('avg_profit_loss', 0) < -1.0:
            issues.append(f"Negative average profit/loss: {trader_data.get('avg_profit_loss', 0):.2f}%")
            recommended_actions.append("optimize_parameters")
        
        # Check 4: Not using all available trade slots
        open_trades = trader_data.get('open_trades', 0)
        max_trades = trader_data.get('max_concurrent_trades', 0)
        
        if open_trades < max_trades and open_trades == 0:
            issues.append(f"No open trades (0/{max_trades} slots used)")
            recommended_actions.append("analyze_market_conditions")
        elif open_trades < max_trades * 0.5 and max_trades > 1:
            issues.append(f"Under-utilizing trade slots ({open_trades}/{max_trades} slots used)")
        
        # Check 5: Excessively long trade durations
        if trader_data.get('avg_duration', 0) > 48:  # 2 days
            issues.append(f"Long average trade duration: {trader_data.get('avg_duration', 0):.2f} hours")
            recommended_actions.append("adjust_profit_targets")
        
        # Prepare response
        checks_result = {
            "basic_issues_detected": len(issues) > 0,
            "issue_summary": "; ".join(issues) if issues else "No basic issues detected",
            "basic_recommended_actions": list(set(recommended_actions)),  # Remove duplicates
            "metrics": {
                "open_trades": trader_data.get('open_trades', 0),
                "max_concurrent_trades": trader_data.get('max_concurrent_trades', 0),
                "success_rate": trader_data.get('success_rate', 0),
                "avg_profit_loss": trader_data.get('avg_profit_loss', 0),
                "avg_duration": trader_data.get('avg_duration', 0),
                "last_trade_date": trader_data.get('last_trade_date')
            }
        }
        
        return checks_result
