from flask import Blueprint, render_template, request, jsonify
import logging
from services.trading_api import TradingApiClient
from services.market_analyzer import MarketAnalyzer
from models import AuditLog, db

logger = logging.getLogger(__name__)

# Create Blueprint
main_bp = Blueprint('main', __name__)

# Initialize services
trading_client = TradingApiClient()
market_analyzer = MarketAnalyzer()

@main_bp.route('/')
def index():
    """Render the main dashboard page"""
    try:
        # Get basic stats for the dashboard
        trading_pairs = trading_client.get_trading_pairs().get('data', [])
        
        # Get all traders status
        traders_status = trading_client.get_all_traders_status().get('data', [])
        
        # Get recent actions
        recent_actions = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
        
        # Calculate summary stats
        open_trades = sum(trader.get('open_trades', 0) for trader in traders_status)
        active_pairs = len(trading_pairs)
        
        # Render template with data
        return render_template(
            'index.html',
            active_pairs=active_pairs,
            open_trades=open_trades,
            trading_pairs=trading_pairs,
            traders_status=traders_status,
            recent_actions=recent_actions
        )
    except Exception as e:
        logger.error(f"Error rendering index page: {str(e)}")
        return render_template('error.html', error=str(e))

@main_bp.route('/trader/<int:pair_id>')
def trader_detail(pair_id):
    """Render the trader detail page"""
    try:
        # Get trading pair details
        pair_response = trading_client.get_trading_pair(pair_id)
        if "error" in pair_response:
            return render_template('error.html', error=pair_response['error'])
        
        pair = pair_response.get('data', {})
        
        # Get trader configuration
        config_response = trading_client.get_trader_config(pair_id)
        trader_config = config_response.get('data', {})
        
        # Get trader status
        status_response = trading_client.get_trader_status(pair_id)
        trader_status = status_response.get('data', {})
        
        # Get trades for this pair
        trades_response = trading_client.get_trades(pair_id=pair_id)
        trades = trades_response.get('data', [])
        
        # Get market conditions
        pair_name = pair.get('pair_name')
        market_conditions = market_analyzer.analyze_market_conditions(pair_name)
        
        # Get recent actions for this pair
        pair_actions = AuditLog.query.filter_by(trading_pair_id=pair_id).order_by(AuditLog.timestamp.desc()).limit(20).all()
        
        # Render template with data
        return render_template(
            'trader_detail.html',
            pair=pair,
            trader_config=trader_config,
            trader_status=trader_status,
            trades=trades,
            market_conditions=market_conditions,
            pair_actions=pair_actions
        )
    except Exception as e:
        logger.error(f"Error rendering trader detail page: {str(e)}")
        return render_template('error.html', error=str(e))

@main_bp.route('/market')
def market_dashboard():
    """Render the market dashboard page"""
    try:
        # Get trading pairs
        trading_pairs = trading_client.get_trading_pairs().get('data', [])
        
        # Get market conditions for selected pairs (limit to 5 for performance)
        market_data = []
        for pair in trading_pairs[:5]:
            pair_name = pair.get('pair_name')
            market_conditions = market_analyzer.analyze_market_conditions(pair_name)
            
            if market_conditions.get('success', False):
                market_data.append({
                    'pair': pair,
                    'conditions': market_conditions
                })
        
        # Render template with data
        return render_template(
            'market_dashboard.html',
            trading_pairs=trading_pairs,
            market_data=market_data
        )
    except Exception as e:
        logger.error(f"Error rendering market dashboard page: {str(e)}")
        return render_template('error.html', error=str(e))

@main_bp.route('/chat')
def chat_interface():
    """Render the chat interface page"""
    try:
        # Get basic stats for context
        trading_pairs = trading_client.get_trading_pairs().get('data', [])
        traders_status = trading_client.get_all_traders_status().get('data', [])
        
        # Calculate summary stats
        open_trades = sum(trader.get('open_trades', 0) for trader in traders_status)
        active_pairs = len(trading_pairs)
        
        # Get recent actions
        recent_actions = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
        
        # Render template with data
        return render_template(
            'chat.html',
            active_pairs=active_pairs,
            open_trades=open_trades,
            recent_actions=recent_actions
        )
    except Exception as e:
        logger.error(f"Error rendering chat interface page: {str(e)}")
        return render_template('error.html', error=str(e))

@main_bp.route('/actions')
def action_log():
    """Render the action log page"""
    try:
        # Get page parameter for pagination
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        # Get paginated actions
        actions_pagination = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Convert AuditLog objects to dictionaries for JSON serialization
        actions_data = []
        for action in actions_pagination.items:
            actions_data.append({
                'id': action.id,
                'timestamp': action.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'action_type': action.action_type,
                'description': action.description,
                'trading_pair_id': action.trading_pair_id,
                'trade_id': action.trade_id
            })
        
        # Render template with data
        return render_template(
            'action_log.html',
            actions=actions_pagination.items,  # For template iteration
            actions_data=actions_data,  # For JSON serialization
            pagination=actions_pagination
        )
    except Exception as e:
        logger.error(f"Error rendering action log page: {str(e)}")
        return render_template('error.html', error=str(e))
