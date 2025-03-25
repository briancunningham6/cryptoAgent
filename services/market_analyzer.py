import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
import math
from .exchange_api import ExchangeApiClient

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """Class for analyzing cryptocurrency market conditions"""
    
    def __init__(self, exchange_name="binance"):
        self.exchange_client = ExchangeApiClient(exchange_name)
    
    def analyze_market_conditions(self, symbol, lookback_periods=168):
        """
        Analyze market conditions for a trading pair
        
        Args:
            symbol (str): Trading pair symbol (e.g., "BTCUSDT")
            lookback_periods (int): Number of hours to look back
            
        Returns:
            dict: Market analysis results
        """
        try:
            # Get candle data
            candles = self.exchange_client.get_klines(symbol, interval="1h", limit=lookback_periods)
            
            if not candles or len(candles) < 24:  # Need at least 24 candles for analysis
                logger.warning(f"Insufficient candle data for {symbol}")
                return {
                    "success": False,
                    "error": "Insufficient historical data"
                }
            
            # Convert to pandas DataFrame
            df = pd.DataFrame(candles)
            
            # Calculate market metrics
            analysis = self._calculate_market_metrics(df, symbol)
            
            # Get recent trades
            recent_trades = self.exchange_client.get_recent_trades(symbol, limit=100)
            
            # Get order book
            order_book = self.exchange_client.get_order_book(symbol, limit=50)
            
            # Add additional analysis
            analysis.update(self._analyze_trade_activity(recent_trades))
            analysis.update(self._analyze_order_book(order_book))
            
            # Add current price and volume
            ticker = self.exchange_client.get_ticker(symbol)
            analysis['current_price'] = float(ticker.get('lastPrice', ticker.get('price', 0)))
            analysis['volume_24h'] = float(ticker.get('volume', ticker.get('quoteVolume', 0)))
            
            # Add trading pair
            analysis['pair'] = symbol
            
            # Add success flag
            analysis['success'] = True
            
            return analysis
        
        except Exception as e:
            logger.error(f"Error analyzing market conditions for {symbol}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_market_metrics(self, df, symbol):
        """
        Calculate technical indicators and market metrics
        
        Args:
            df (DataFrame): Candle data in pandas DataFrame
            symbol (str): Trading pair symbol
            
        Returns:
            dict: Market metrics and indicators
        """
        # Extract price data
        close_prices = np.array([float(candle['close']) for candle in df.to_dict('records')])
        high_prices = np.array([float(candle['high']) for candle in df.to_dict('records')])
        low_prices = np.array([float(candle['low']) for candle in df.to_dict('records')])
        volumes = np.array([float(candle['volume']) for candle in df.to_dict('records')])
        
        # Calculate basic metrics
        current_price = close_prices[-1]
        price_change_24h = ((close_prices[-1] / close_prices[-24]) - 1) * 100 if len(close_prices) >= 24 else 0
        
        # Calculate price history for last 24 hours
        price_history = [float(close_prices[-i]) for i in range(24, 0, -1)] if len(close_prices) >= 24 else []
        
        # Calculate moving averages
        ma_7 = np.mean(close_prices[-7:]) if len(close_prices) >= 7 else None
        ma_25 = np.mean(close_prices[-25:]) if len(close_prices) >= 25 else None
        ma_99 = np.mean(close_prices[-99:]) if len(close_prices) >= 99 else None
        
        # Calculate RSI
        rsi = self._calculate_rsi(close_prices)
        
        # Calculate MACD
        macd, macd_signal, macd_histogram = self._calculate_macd(close_prices)
        
        # Calculate Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(close_prices)
        
        # Calculate volatility (standard deviation of returns)
        returns = np.diff(close_prices) / close_prices[:-1]
        volatility = np.std(returns) * 100 * math.sqrt(24)  # Annualized to 24 hours
        
        # Determine trend
        trend_direction, trend_strength = self._determine_trend(close_prices, ma_7, ma_25, ma_99)
        
        # Trading recommendation
        trading_recommended = self._recommend_trading(trend_direction, trend_strength, volatility, rsi, macd_histogram)
        
        return {
            "current_price": current_price,
            "price_change_24h": price_change_24h,
            "price_history": price_history,
            "ma_7": ma_7,
            "ma_25": ma_25,
            "ma_99": ma_99,
            "rsi": rsi,
            "macd": {
                "macd_line": macd[-1] if macd is not None else None,
                "signal_line": macd_signal[-1] if macd_signal is not None else None,
                "histogram": macd_histogram[-1] if macd_histogram is not None else None
            },
            "bollinger_bands": {
                "upper": bb_upper[-1] if bb_upper is not None else None,
                "middle": bb_middle[-1] if bb_middle is not None else None,
                "lower": bb_lower[-1] if bb_lower is not None else None
            },
            "volatility": volatility,
            "trend": {
                "direction": trend_direction,
                "strength": trend_strength
            },
            "trading_recommended": trading_recommended,
            "reasoning": self._generate_reasoning(trend_direction, trend_strength, volatility, rsi, 
                                                 macd, macd_signal, macd_histogram, trading_recommended)
        }
    
    def _calculate_rsi(self, prices, window=14):
        """Calculate Relative Strength Index"""
        if len(prices) < window + 1:
            return None
        
        # Calculate price changes
        deltas = np.diff(prices)
        
        # Calculate seed values
        seed = deltas[:window+1]
        up = seed[seed >= 0].sum() / window
        down = -seed[seed < 0].sum() / window
        
        # Calculate smoothed values
        rs = up / down if down != 0 else float('inf')
        rsi = np.zeros_like(prices)
        rsi[:window] = 100. - 100. / (1. + rs)
        
        # Calculate RSI
        for i in range(window, len(prices)):
            delta = deltas[i - 1]
            
            if delta > 0:
                upval = delta
                downval = 0
            else:
                upval = 0
                downval = -delta
                
            up = (up * (window - 1) + upval) / window
            down = (down * (window - 1) + downval) / window
            
            rs = up / down if down != 0 else float('inf')
            rsi[i] = 100. - 100. / (1. + rs)
            
        return rsi[-1]
    
    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < slow + signal:
            return None, None, None
        
        # Calculate EMAs
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        # Calculate MACD line
        macd_line = ema_fast - ema_slow
        
        # Calculate signal line
        signal_line = self._calculate_ema(macd_line, signal)
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_ema(self, prices, window):
        """Calculate Exponential Moving Average"""
        weights = np.exp(np.linspace(-1., 0., window))
        weights /= weights.sum()
        
        # Calculate EMA using convolution
        ema = np.convolve(prices, weights, mode='full')[:len(prices)]
        ema[:window] = ema[window]
        
        return ema
    
    def _calculate_bollinger_bands(self, prices, window=20, num_std=2):
        """Calculate Bollinger Bands"""
        if len(prices) < window:
            return None, None, None
        
        # Calculate middle band (SMA)
        middle_band = np.convolve(prices, np.ones(window)/window, mode='valid')
        
        # Pad the beginning to match length
        pad_length = len(prices) - len(middle_band)
        middle_band = np.pad(middle_band, (pad_length, 0), 'edge')
        
        # Calculate standard deviation
        rolling_std = np.array([np.std(prices[i-window:i]) if i >= window else np.std(prices[:i+1]) for i in range(len(prices))])
        
        # Calculate upper and lower bands
        upper_band = middle_band + (rolling_std * num_std)
        lower_band = middle_band - (rolling_std * num_std)
        
        return upper_band, middle_band, lower_band
    
    def _determine_trend(self, prices, ma_7, ma_25, ma_99):
        """
        Determine market trend direction and strength
        
        Returns:
            tuple: (trend_direction, trend_strength)
                trend_direction: "up", "down", or "sideways"
                trend_strength: float between 0 and 1
        """
        # Check if we have enough data
        if ma_7 is None or ma_25 is None:
            return "unknown", 0
        
        # Calculate short term trend
        short_term = "up" if prices[-1] > ma_7 else "down"
        
        # Calculate medium term trend
        medium_term = "up" if ma_7 > ma_25 else "down"
        
        # Calculate long term trend if available
        if ma_99 is not None:
            long_term = "up" if ma_25 > ma_99 else "down"
        else:
            long_term = medium_term
        
        # Determine overall trend
        if short_term == medium_term == long_term:
            # Strong trend
            trend_direction = short_term
            trend_strength = 0.9
        elif short_term == medium_term:
            # Moderate trend
            trend_direction = short_term
            trend_strength = 0.7
        elif medium_term == long_term:
            # Established trend with possible reversal
            trend_direction = medium_term
            trend_strength = 0.6
        elif short_term != medium_term and medium_term != long_term:
            # Mixed signals
            trend_direction = "sideways"
            trend_strength = 0.3
        else:
            # Unclear trend
            trend_direction = "sideways"
            trend_strength = 0.5
        
        # Adjust strength based on price distance from moving averages
        distance_from_ma = abs((prices[-1] / ma_25) - 1)
        if distance_from_ma > 0.05:  # More than 5% away from MA25
            # Price far from moving average could indicate stronger trend or potential reversal
            if (trend_direction == "up" and prices[-1] > ma_25) or (trend_direction == "down" and prices[-1] < ma_25):
                # Confirm trend
                trend_strength = min(1.0, trend_strength + 0.1)
            else:
                # Potential reversal
                trend_strength = max(0.1, trend_strength - 0.1)
        
        return trend_direction, trend_strength
    
    def _recommend_trading(self, trend_direction, trend_strength, volatility, rsi, macd_histogram):
        """
        Determine if trading is recommended based on market conditions
        
        Returns:
            bool: True if trading is recommended, False otherwise
        """
        # Default to not recommended
        recommended = False
        
        # Check for strong uptrend
        if trend_direction == "up" and trend_strength > 0.6:
            recommended = True
        
        # Check for sideways trend with acceptable volatility
        if trend_direction == "sideways" and volatility < 15:
            recommended = True
        
        # Avoid strong downtrends
        if trend_direction == "down" and trend_strength > 0.6:
            recommended = False
        
        # Check RSI for overbought/oversold conditions
        if rsi is not None:
            if rsi < 30:  # Oversold
                recommended = True
            elif rsi > 70:  # Overbought
                recommended = False
        
        # Check MACD histogram
        if macd_histogram is not None and len(macd_histogram) > 1:
            # Positive momentum (histogram increasing)
            if macd_histogram[-1] > macd_histogram[-2] and macd_histogram[-1] > 0:
                recommended = True
            # Negative momentum (histogram decreasing)
            elif macd_histogram[-1] < macd_histogram[-2] and macd_histogram[-1] < 0:
                recommended = False
        
        # Extreme volatility check - avoid extremely volatile markets
        if volatility > 30:
            recommended = False
        
        return recommended
    
    def _analyze_trade_activity(self, recent_trades):
        """
        Analyze recent trade activity
        
        Args:
            recent_trades (list): List of recent trades
            
        Returns:
            dict: Trade activity analysis
        """
        if not recent_trades or "error" in recent_trades:
            return {"trade_activity": "unknown"}
        
        try:
            # Calculate buy/sell ratio
            buys = sum(1 for trade in recent_trades if trade.get('isBuyerMaker', False) is False)
            sells = sum(1 for trade in recent_trades if trade.get('isBuyerMaker', False) is True)
            
            total_trades = len(recent_trades)
            buy_ratio = buys / total_trades if total_trades > 0 else 0.5
            
            # Determine buy/sell pressure
            if buy_ratio > 0.6:
                pressure = "buying"
                pressure_strength = (buy_ratio - 0.5) * 2  # Scale to 0-1
            elif buy_ratio < 0.4:
                pressure = "selling"
                pressure_strength = (0.5 - buy_ratio) * 2  # Scale to 0-1
            else:
                pressure = "neutral"
                pressure_strength = 0.0
            
            return {
                "trade_activity": {
                    "buys": buys,
                    "sells": sells,
                    "total": total_trades,
                    "buy_ratio": buy_ratio,
                    "pressure": pressure,
                    "pressure_strength": pressure_strength
                }
            }
        
        except Exception as e:
            logger.error(f"Error analyzing trade activity: {str(e)}")
            return {"trade_activity": "error"}
    
    def _analyze_order_book(self, order_book):
        """
        Analyze order book to assess market depth
        
        Args:
            order_book (dict): Order book data
            
        Returns:
            dict: Order book analysis
        """
        if not order_book or "error" in order_book:
            return {"order_book_analysis": "unknown"}
        
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return {"order_book_analysis": "insufficient_data"}
            
            # Calculate total volume at top 10 levels
            bid_volume = sum(float(bid[1]) for bid in bids[:10]) if len(bids) >= 10 else 0
            ask_volume = sum(float(ask[1]) for ask in asks[:10]) if len(asks) >= 10 else 0
            
            # Calculate bid/ask ratio
            volume_ratio = bid_volume / ask_volume if ask_volume > 0 else float('inf')
            
            # Calculate price range to measure depth
            top_bid = float(bids[0][0]) if bids else 0
            top_ask = float(asks[0][0]) if asks else 0
            spread = ((top_ask / top_bid) - 1) * 100 if top_bid > 0 else 0
            
            # Calculate 5% price impact
            bid_depth = 0
            for bid in bids:
                price = float(bid[0])
                if (top_bid - price) / top_bid <= 0.05:  # Within 5% of top bid
                    bid_depth += float(bid[1])
            
            ask_depth = 0
            for ask in asks:
                price = float(ask[0])
                if (price - top_ask) / top_ask <= 0.05:  # Within 5% of top ask
                    ask_depth += float(ask[1])
            
            return {
                "order_book_analysis": {
                    "bid_ask_ratio": volume_ratio,
                    "spread": spread,
                    "bid_depth": bid_depth,
                    "ask_depth": ask_depth,
                    "market_depth_balance": bid_depth / ask_depth if ask_depth > 0 else float('inf')
                }
            }
        
        except Exception as e:
            logger.error(f"Error analyzing order book: {str(e)}")
            return {"order_book_analysis": "error"}
    
    def _generate_reasoning(self, trend_direction, trend_strength, volatility, rsi, 
                           macd, macd_signal, macd_histogram, trading_recommended):
        """
        Generate a human-readable explanation for the market analysis
        
        Returns:
            str: Reasoning behind the market analysis
        """
        reasons = []
        
        # Trend explanation
        if trend_direction == "up":
            if trend_strength > 0.8:
                reasons.append(f"Market is in a strong uptrend (strength: {trend_strength:.2f}).")
            elif trend_strength > 0.5:
                reasons.append(f"Market is in a moderate uptrend (strength: {trend_strength:.2f}).")
            else:
                reasons.append(f"Market is in a weak uptrend (strength: {trend_strength:.2f}).")
        elif trend_direction == "down":
            if trend_strength > 0.8:
                reasons.append(f"Market is in a strong downtrend (strength: {trend_strength:.2f}).")
            elif trend_strength > 0.5:
                reasons.append(f"Market is in a moderate downtrend (strength: {trend_strength:.2f}).")
            else:
                reasons.append(f"Market is in a weak downtrend (strength: {trend_strength:.2f}).")
        else:
            reasons.append(f"Market is moving sideways with no clear trend (strength: {trend_strength:.2f}).")
        
        # Volatility explanation
        if volatility > 25:
            reasons.append(f"Market volatility is very high ({volatility:.2f}%), indicating potential for large price swings.")
        elif volatility > 15:
            reasons.append(f"Market volatility is moderate ({volatility:.2f}%).")
        else:
            reasons.append(f"Market volatility is low ({volatility:.2f}%), indicating relative stability.")
        
        # RSI explanation
        if rsi is not None:
            if rsi > 70:
                reasons.append(f"RSI is overbought ({rsi:.2f}), suggesting potential for a downward correction.")
            elif rsi < 30:
                reasons.append(f"RSI is oversold ({rsi:.2f}), suggesting potential for an upward correction.")
            else:
                reasons.append(f"RSI is in neutral territory ({rsi:.2f}).")
        
        # MACD explanation
        if macd is not None and macd_signal is not None and macd_histogram is not None:
            if macd_histogram[-1] > 0 and macd_histogram[-1] > macd_histogram[-2]:
                reasons.append("MACD histogram is positive and increasing, indicating strengthening bullish momentum.")
            elif macd_histogram[-1] > 0 and macd_histogram[-1] < macd_histogram[-2]:
                reasons.append("MACD histogram is positive but decreasing, indicating weakening bullish momentum.")
            elif macd_histogram[-1] < 0 and macd_histogram[-1] < macd_histogram[-2]:
                reasons.append("MACD histogram is negative and decreasing, indicating strengthening bearish momentum.")
            elif macd_histogram[-1] < 0 and macd_histogram[-1] > macd_histogram[-2]:
                reasons.append("MACD histogram is negative but increasing, indicating weakening bearish momentum.")
        
        # Trading recommendation explanation
        if trading_recommended:
            reasons.append("Based on the overall analysis, market conditions appear favorable for trading.")
        else:
            reasons.append("Based on the overall analysis, market conditions suggest caution before placing trades.")
        
        return " ".join(reasons)
