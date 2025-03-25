from flask import Blueprint, jsonify, request
from datetime import datetime
import logging
from services.market_analyzer import MarketAnalyzer
from services.trading_api import TradingApiClient
from services.parameter_optimizer import ParameterOptimizer
from services.trader_monitor import TraderMonitor
from services.openai_service import process_user_query
from models import AuditLog, db

logger = logging.getLogger(__name__)

# Create Blueprint
api_bp = Blueprint('api', __name__)

# Initialize services
market_analyzer = MarketAnalyzer()
trading_client = TradingApiClient()
parameter_optimizer = ParameterOptimizer()
trader_monitor = TraderMonitor()

# Helper function to log agent actions
def log_action(action_type, description, trading_pair_id=None, trade_id=None):
    try:
        audit_log = AuditLog(
            action_type=action_type,
            description=description,
            trading_pair_id=trading_pair_id,
            trade_id=trade_id
        )
        db.session.add(audit_log)
        db.session.commit()
        return audit_log.id
    except Exception as e:
        logger.error(f"Error logging action: {str(e)}")
        db.session.rollback()
        return None

# Routes
@api_bp.route('/market/analyze', methods=['GET'])
def analyze_market():
    """Analyze market conditions for a trading pair"""
    symbol = request.args.get('symbol')
    
    if not symbol:
        return jsonify({"success": False, "error": "Symbol parameter is required"}), 400
    
    try:
        analysis = market_analyzer.analyze_market_conditions(symbol)
        
        # Log the action
        log_action(
            action_type="market_analysis",
            description=f"Analyzed market conditions for {symbol}"
        )
        
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Error analyzing market: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/trader/optimize/<int:pair_id>', methods=['POST'])
def optimize_trader(pair_id):
    """Optimize trading parameters for a specific pair"""
    try:
        # Get trading pair details from trading API
        pair_response = trading_client.get_trading_pair(pair_id)
        if "error" in pair_response:
            return jsonify({"success": False, "error": pair_response['error']}), 400
        
        pair_name = pair_response.get('data', {}).get('pair_name', f"pair_{pair_id}")
        
        # Optimize parameters
        result = parameter_optimizer.optimize_trader_parameters(pair_id)
        
        # Log the action if successful
        if result.get('success'):
            log_action(
                action_type="parameter_optimization",
                description=f"Optimized trading parameters for {pair_name}: {result.get('reasoning', 'No reasoning provided')}",
                trading_pair_id=pair_id
            )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error optimizing trader parameters: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/trader/monitor/<int:pair_id>', methods=['GET'])
def monitor_trader(pair_id):
    """Monitor a specific trader and detect issues"""
    try:
        result = trader_monitor.check_trader(pair_id)
        
        # Log the action if issues were detected
        if result.get('issues_detected'):
            log_action(
                action_type="trader_monitoring",
                description=f"Detected issues with trader for {result.get('pair_name', f'pair_{pair_id}')}: {result.get('issue_summary', 'Unknown issues')}",
                trading_pair_id=pair_id
            )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error monitoring trader: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/trader/monitor/all', methods=['GET'])
def monitor_all_traders():
    """Monitor all traders and detect issues"""
    try:
        result = trader_monitor.monitor_all_traders()
        
        # Log the action
        log_action(
            action_type="trader_monitoring_all",
            description=f"Monitored all traders, detected issues in {result.get('traders_with_issues', 0)} out of {result.get('traders_checked', 0)} traders"
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error monitoring all traders: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/trader/inactive', methods=['GET'])
def check_inactive_traders():
    """Check for inactive traders"""
    try:
        # Get inactivity threshold from query parameter, default to 24 hours
        threshold = request.args.get('threshold', 24, type=int)
        
        result = trader_monitor.check_inactive_traders(inactivity_threshold_hours=threshold)
        
        # Log the action
        log_action(
            action_type="inactive_trader_check",
            description=f"Checked for inactive traders, found {result.get('inactive_traders_count', 0)} traders inactive for more than {threshold} hours"
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error checking inactive traders: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/trader/place-trade/<int:pair_id>', methods=['POST'])
def place_trade(pair_id):
    """Place a trade for a trader if market conditions are favorable"""
    try:
        result = trader_monitor.place_trade_for_inactive_trader(pair_id)
        
        # Log the action based on result
        if result.get('success'):
            log_action(
                action_type="trade_placement",
                description=f"Placed trade for pair {pair_id} based on market analysis",
                trading_pair_id=pair_id,
                trade_id=result.get('trade_data', {}).get('id')
            )
        else:
            log_action(
                action_type="trade_placement_failed",
                description=f"Failed to place trade for pair {pair_id}: {result.get('error', 'Unknown error')}",
                trading_pair_id=pair_id
            )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error placing trade: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/chat/query', methods=['POST'])
def process_chat_query():
    """Process a natural language query from the user"""
    data = request.json
    
    if not data or 'query' not in data:
        return jsonify({"success": False, "error": "Query is required"}), 400
    
    query = data.get('query')
    
    try:
        # Get recent actions for context
        recent_actions = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
        actions_data = [
            {
                "timestamp": action.timestamp.isoformat(),
                "action_type": action.action_type,
                "description": action.description
            }
            for action in recent_actions
        ]
        
        # Get trading data for context (simplified)
        trading_data = {
            "active_pairs": len(trading_client.get_trading_pairs().get('data', [])),
            "open_trades": sum(
                trader.get('open_trades', 0) 
                for trader in trading_client.get_all_traders_status().get('data', [])
            )
        }
        
        # Process the query
        response = process_user_query(query, trading_data, None, actions_data)
        
        # Log the action
        log_action(
            action_type="chat_query",
            description=f"Processed user query: {query[:50]}{'...' if len(query) > 50 else ''}"
        )
        
        return jsonify({"success": True, "response": response})
    except Exception as e:
        logger.error(f"Error processing chat query: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route('/actions/recent', methods=['GET'])
def get_recent_actions():
    """Get recent actions taken by the AI agent"""
    try:
        # Get limit from query parameter, default to 20
        limit = request.args.get('limit', 20, type=int)
        
        # Get recent actions
        recent_actions = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
        
        actions_data = [
            {
                "id": action.id,
                "timestamp": action.timestamp.isoformat(),
                "action_type": action.action_type,
                "description": action.description,
                "trading_pair_id": action.trading_pair_id,
                "trade_id": action.trade_id
            }
            for action in recent_actions
        ]
        
        return jsonify({"success": True, "actions": actions_data})
    except Exception as e:
        logger.error(f"Error getting recent actions: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
