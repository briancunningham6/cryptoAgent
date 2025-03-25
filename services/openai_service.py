import json
import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
MODEL = "gpt-4o"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)


def generate_market_analysis(market_data):
    """
    Generate a market analysis using OpenAI based on provided market data
    
    Args:
        market_data (dict): Dictionary containing market data including price history,
                          volume, indicators, etc.
    
    Returns:
        dict: Analysis results including trend, recommendation, and reasoning
    """
    try:
        # Prepare the prompt with market data
        prompt = f"""
        Analyze the following cryptocurrency market data and provide a detailed analysis:
        
        Trading Pair: {market_data.get('pair', 'Unknown')}
        Current Price: {market_data.get('current_price', 'Unknown')}
        24h Volume: {market_data.get('volume_24h', 'Unknown')}
        
        Price History (Last 24 hours): {market_data.get('price_history', [])}
        
        Technical Indicators:
        - RSI: {market_data.get('rsi', 'N/A')}
        - MACD: {market_data.get('macd', 'N/A')}
        - Bollinger Bands: {market_data.get('bollinger_bands', 'N/A')}
        
        Based on this data:
        1. What is the current market trend?
        2. Would you recommend placing new trades in this market?
        3. What is the volatility assessment?
        
        Return your analysis in JSON format with the following structure:
        {
            "trend": "up|down|sideways",
            "trend_strength": float between 0 and 1,
            "volatility": float between 0 and 1,
            "trading_recommended": boolean,
            "reasoning": "detailed explanation",
            "suggested_actions": ["action1", "action2"]
        }
        """
        
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a crypto trading analysis expert. Provide detailed market analysis based on given data."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse and return the JSON response
        analysis = json.loads(response.choices[0].message.content)
        logger.info(f"Generated market analysis for {market_data.get('pair')}")
        return analysis
        
    except Exception as e:
        logger.error(f"Error generating market analysis: {str(e)}")
        return {
            "trend": "unknown",
            "trend_strength": 0,
            "volatility": 0,
            "trading_recommended": False,
            "reasoning": f"Error analyzing market: {str(e)}",
            "suggested_actions": ["manual_review"]
        }


def optimize_trading_parameters(trading_pair, current_config, trade_history, market_conditions):
    """
    Optimize trading parameters using OpenAI based on historical performance
    
    Args:
        trading_pair (str): The trading pair to optimize for
        current_config (dict): Current trading parameters
        trade_history (list): List of past trades and their performance
        market_conditions (dict): Current market conditions
    
    Returns:
        dict: Optimized parameters with reasoning
    """
    try:
        # Prepare the prompt with current configuration and history
        prompt = f"""
        Optimize the trading parameters for {trading_pair} based on the following information:
        
        Current Configuration:
        - Profit Margin: {current_config.get('profit_margin', 'Unknown')}%
        - Trade Size: {current_config.get('trade_size', 'Unknown')}
        - Max Open Time: {current_config.get('max_open_time', 'Unknown')} hours
        - Stop Loss: {current_config.get('stop_loss', 'None')}%
        
        Trade History Summary:
        - Total Trades: {len(trade_history)}
        - Successful Trades: {sum(1 for t in trade_history if t.get('profit_loss', 0) > 0)}
        - Average Profit/Loss: {sum(t.get('profit_loss', 0) for t in trade_history) / max(1, len(trade_history))}%
        - Average Time to Close: {sum(t.get('duration_hours', 0) for t in trade_history) / max(1, len(trade_history))} hours
        
        Current Market Conditions:
        - Trend: {market_conditions.get('trend', 'Unknown')}
        - Volatility: {market_conditions.get('volatility', 'Unknown')}
        
        Provide optimized trading parameters to improve performance. Return in JSON format with the following structure:
        {
            "profit_margin": float percentage,
            "trade_size": float,
            "max_open_time": integer hours,
            "stop_loss": float percentage or null,
            "reasoning": "detailed explanation",
            "expected_improvement": "explanation of expected improvement"
        }
        """
        
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a crypto trading parameter optimization expert. Provide optimized parameters based on performance history and market conditions."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse and return the JSON response
        optimized_params = json.loads(response.choices[0].message.content)
        logger.info(f"Generated optimized parameters for {trading_pair}")
        return optimized_params
        
    except Exception as e:
        logger.error(f"Error optimizing trading parameters: {str(e)}")
        return {
            "profit_margin": current_config.get('profit_margin'),
            "trade_size": current_config.get('trade_size'),
            "max_open_time": current_config.get('max_open_time'),
            "stop_loss": current_config.get('stop_loss'),
            "reasoning": f"Error optimizing parameters: {str(e)}",
            "expected_improvement": "None due to optimization failure"
        }


def detect_trader_issues(trading_pair, trader_data):
    """
    Detect issues with a trader using OpenAI
    
    Args:
        trading_pair (str): The trading pair to analyze
        trader_data (dict): Data about the trader including history and status
    
    Returns:
        dict: Analysis of issues and recommended actions
    """
    try:
        # Prepare the prompt with trader data
        prompt = f"""
        Analyze the following crypto trader's performance and identify potential issues:
        
        Trading Pair: {trading_pair}
        Last Trade Date: {trader_data.get('last_trade_date', 'Unknown')}
        Current Open Trades: {trader_data.get('open_trades', 0)}
        Max Concurrent Trades: {trader_data.get('max_concurrent_trades', 0)}
        Success Rate: {trader_data.get('success_rate', 'Unknown')}%
        
        Recent Issues:
        {trader_data.get('recent_issues', 'None reported')}
        
        Performance Metrics:
        - Average Profit/Loss: {trader_data.get('avg_profit_loss', 'Unknown')}%
        - Average Trade Duration: {trader_data.get('avg_duration', 'Unknown')} hours
        - Failed Trade Rate: {trader_data.get('failed_rate', 'Unknown')}%
        
        Detect any potential issues with this trader and recommend actions. Return in JSON format with the following structure:
        {
            "issues_detected": boolean,
            "issue_summary": "brief summary of issues",
            "detailed_analysis": "detailed explanation",
            "recommended_actions": ["action1", "action2"],
            "severity": "low|medium|high"
        }
        """
        
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a crypto trading system diagnostic expert. Detect issues and recommend fixes for trader performance problems."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse and return the JSON response
        analysis = json.loads(response.choices[0].message.content)
        logger.info(f"Generated trader issue analysis for {trading_pair}")
        return analysis
        
    except Exception as e:
        logger.error(f"Error detecting trader issues: {str(e)}")
        return {
            "issues_detected": True,
            "issue_summary": f"Error analyzing trader: {str(e)}",
            "detailed_analysis": "System error prevented proper analysis of trader issues.",
            "recommended_actions": ["manual_review"],
            "severity": "medium"
        }


def process_user_query(query, trading_data=None, market_data=None, recent_actions=None):
    """
    Process a natural language query from a user using OpenAI
    
    Args:
        query (str): The user's query
        trading_data (dict): Current trading data
        market_data (dict): Current market data
        recent_actions (list): Recent actions taken by the AI agent
    
    Returns:
        str: Response to the user's query
    """
    try:
        # Prepare system context with available data
        system_context = """
        You are an AI assistant for crypto trading operations. You help manage a crypto trading system by 
        analyzing market conditions, optimizing trading parameters, and monitoring trading operations.
        
        When responding to user queries:
        1. Be concise but informative
        2. If you don't have specific data, acknowledge that limitation
        3. Provide actionable insights when possible
        4. When discussing market trends, avoid making specific price predictions
        5. Focus on factual analysis based on available data
        """
        
        # Add available context to user prompt
        context = "Here is the available context for your query:\n\n"
        
        if trading_data:
            context += f"Trading Data:\n- Active Pairs: {trading_data.get('active_pairs', 'Unknown')}\n"
            context += f"- Open Trades: {trading_data.get('open_trades', 'Unknown')}\n"
            context += f"- Recent Performance: {trading_data.get('recent_performance', 'Unknown')}\n\n"
            
        if market_data:
            context += f"Market Data:\n- Market Trends: {market_data.get('market_trends', 'Unknown')}\n"
            context += f"- Market Volatility: {market_data.get('market_volatility', 'Unknown')}\n\n"
            
        if recent_actions:
            context += "Recent AI Actions:\n"
            for action in recent_actions[:5]:  # Limit to 5 most recent actions
                context += f"- {action.get('timestamp', '')} - {action.get('action_type', '')}: {action.get('description', '')}\n"
        
        # Combine user query with context
        user_message = f"{query}\n\n{context}"
        
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_message}
            ]
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error processing user query: {str(e)}")
        return f"I'm sorry, I encountered an error while processing your query: {str(e)}. Please try again later or rephrase your question."
