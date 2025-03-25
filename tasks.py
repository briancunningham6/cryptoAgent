import logging
from apscheduler.schedulers.background import BackgroundScheduler
from services.market_analyzer import MarketAnalyzer
from services.trading_api import TradingApiClient
from services.parameter_optimizer import ParameterOptimizer
from services.trader_monitor import TraderMonitor
from models import AuditLog, db
from app import app

logger = logging.getLogger(__name__)

# Initialize services
market_analyzer = MarketAnalyzer()
trading_client = TradingApiClient()
parameter_optimizer = ParameterOptimizer()
trader_monitor = TraderMonitor()

def initialize_scheduled_tasks(scheduler):
    """
    Initialize all scheduled tasks
    
    Args:
        scheduler: BackgroundScheduler instance
    """
    # Schedule task to monitor all traders (every 2 hours)
    scheduler.add_job(
        monitor_all_traders,
        'interval',
        hours=2,
        id='monitor_all_traders'
    )
    
    # Schedule task to check for inactive traders (every 6 hours)
    scheduler.add_job(
        check_inactive_traders,
        'interval',
        hours=6,
        id='check_inactive_traders'
    )
    
    # Schedule task to optimize parameters for all traders (daily)
    scheduler.add_job(
        optimize_all_traders,
        'interval',
        days=1,
        id='optimize_all_traders'
    )
    
    # Schedule task to monitor market conditions (hourly)
    scheduler.add_job(
        monitor_market_conditions,
        'interval',
        hours=1,
        id='monitor_market_conditions'
    )
    
    logger.info("Scheduled tasks initialized")

def log_action(action_type, description, trading_pair_id=None, trade_id=None):
    """
    Helper function to log actions
    
    Args:
        action_type (str): Type of action
        description (str): Description of the action
        trading_pair_id (int, optional): ID of related trading pair
        trade_id (int, optional): ID of related trade
    """
    with app.app_context():
        try:
            audit_log = AuditLog(
                action_type=action_type,
                description=description,
                trading_pair_id=trading_pair_id,
                trade_id=trade_id
            )
            db.session.add(audit_log)
            db.session.commit()
        except Exception as e:
            logger.error(f"Error logging action: {str(e)}")
            db.session.rollback()

def monitor_all_traders():
    """
    Scheduled task to monitor all traders
    """
    logger.info("Running scheduled task: monitor_all_traders")
    
    try:
        result = trader_monitor.monitor_all_traders()
        
        # Log the action
        log_action(
            action_type="scheduled_trader_monitoring",
            description=f"Monitored all traders, detected issues in {result.get('traders_with_issues', 0)} out of {result.get('traders_checked', 0)} traders"
        )
        
        # Take action for traders with issues
        if result.get('success') and result.get('traders_with_issues', 0) > 0:
            for trader_result in result.get('results', []):
                if trader_result.get('issues_detected', False):
                    pair_id = trader_result.get('pair_id')
                    pair_name = trader_result.get('pair_name', f"pair_{pair_id}")
                    severity = trader_result.get('severity', 'low')
                    
                    # For high severity issues, attempt parameter optimization
                    if severity == 'high' and 'optimize_parameters' in trader_result.get('recommended_actions', []):
                        logger.info(f"Optimizing parameters for trader with issues: {pair_name}")
                        optimization_result = parameter_optimizer.optimize_trader_parameters(pair_id)
                        
                        if optimization_result.get('success'):
                            log_action(
                                action_type="scheduled_parameter_optimization",
                                description=f"Optimized parameters for {pair_name} due to detected issues: {optimization_result.get('reasoning', 'No reasoning provided')}",
                                trading_pair_id=pair_id
                            )
    
    except Exception as e:
        logger.error(f"Error in scheduled task monitor_all_traders: {str(e)}")
        log_action(
            action_type="scheduled_task_error",
            description=f"Error in monitor_all_traders task: {str(e)}"
        )

def check_inactive_traders():
    """
    Scheduled task to check for inactive traders
    """
    logger.info("Running scheduled task: check_inactive_traders")
    
    try:
        result = trader_monitor.check_inactive_traders(inactivity_threshold_hours=24)
        
        # Log the action
        log_action(
            action_type="scheduled_inactive_trader_check",
            description=f"Checked for inactive traders, found {result.get('inactive_traders_count', 0)} traders inactive for more than 24 hours"
        )
        
        # Place trades for inactive traders in favorable market conditions
        if result.get('success') and result.get('inactive_traders', []):
            for trader in result.get('inactive_traders', []):
                if trader.get('recommendation') == 'place_trade':
                    pair_id = trader.get('pair_id')
                    pair_name = trader.get('pair_name')
                    
                    logger.info(f"Placing trade for inactive trader: {pair_name}")
                    trade_result = trader_monitor.place_trade_for_inactive_trader(pair_id)
                    
                    if trade_result.get('success'):
                        log_action(
                            action_type="scheduled_trade_placement",
                            description=f"Placed trade for inactive trader {pair_name} based on favorable market conditions",
                            trading_pair_id=pair_id,
                            trade_id=trade_result.get('trade_data', {}).get('id')
                        )
                    else:
                        log_action(
                            action_type="scheduled_trade_placement_failed",
                            description=f"Failed to place trade for inactive trader {pair_name}: {trade_result.get('error', 'Unknown error')}",
                            trading_pair_id=pair_id
                        )
    
    except Exception as e:
        logger.error(f"Error in scheduled task check_inactive_traders: {str(e)}")
        log_action(
            action_type="scheduled_task_error",
            description=f"Error in check_inactive_traders task: {str(e)}"
        )

def optimize_all_traders():
    """
    Scheduled task to optimize parameters for all traders
    """
    logger.info("Running scheduled task: optimize_all_traders")
    
    try:
        # Get all trading pairs
        pairs_response = trading_client.get_trading_pairs()
        
        if "error" in pairs_response:
            logger.error(f"Error getting trading pairs: {pairs_response['error']}")
            log_action(
                action_type="scheduled_task_error",
                description=f"Error in optimize_all_traders task: {pairs_response['error']}"
            )
            return
        
        pairs = pairs_response.get('data', [])
        
        # Optimize parameters for each active pair
        optimized_count = 0
        for pair in pairs:
            if pair.get('active', True):
                pair_id = pair.get('id')
                pair_name = pair.get('pair_name')
                
                logger.info(f"Optimizing parameters for: {pair_name}")
                optimization_result = parameter_optimizer.optimize_trader_parameters(pair_id)
                
                if optimization_result.get('success'):
                    optimized_count += 1
                    log_action(
                        action_type="scheduled_parameter_optimization",
                        description=f"Optimized parameters for {pair_name}: {optimization_result.get('reasoning', 'No reasoning provided')}",
                        trading_pair_id=pair_id
                    )
        
        # Log summary
        log_action(
            action_type="scheduled_optimization_summary",
            description=f"Optimized parameters for {optimized_count} out of {len(pairs)} trading pairs"
        )
    
    except Exception as e:
        logger.error(f"Error in scheduled task optimize_all_traders: {str(e)}")
        log_action(
            action_type="scheduled_task_error",
            description=f"Error in optimize_all_traders task: {str(e)}"
        )

def monitor_market_conditions():
    """
    Scheduled task to monitor market conditions for all pairs
    """
    logger.info("Running scheduled task: monitor_market_conditions")
    
    try:
        # Get all trading pairs
        pairs_response = trading_client.get_trading_pairs()
        
        if "error" in pairs_response:
            logger.error(f"Error getting trading pairs: {pairs_response['error']}")
            log_action(
                action_type="scheduled_task_error",
                description=f"Error in monitor_market_conditions task: {pairs_response['error']}"
            )
            return
        
        pairs = pairs_response.get('data', [])
        
        # Monitor market conditions for each active pair
        favorable_markets = 0
        unfavorable_markets = 0
        
        for pair in pairs:
            if pair.get('active', True):
                pair_id = pair.get('id')
                pair_name = pair.get('pair_name')
                
                logger.info(f"Analyzing market conditions for: {pair_name}")
                market_conditions = market_analyzer.analyze_market_conditions(pair_name)
                
                if market_conditions.get('success'):
                    trading_recommended = market_conditions.get('trading_recommended', False)
                    
                    if trading_recommended:
                        favorable_markets += 1
                    else:
                        unfavorable_markets += 1
        
        # Log summary
        log_action(
            action_type="scheduled_market_analysis_summary",
            description=f"Market analysis: {favorable_markets} favorable markets, {unfavorable_markets} unfavorable markets out of {len(pairs)} pairs"
        )
    
    except Exception as e:
        logger.error(f"Error in scheduled task monitor_market_conditions: {str(e)}")
        log_action(
            action_type="scheduled_task_error",
            description=f"Error in monitor_market_conditions task: {str(e)}"
        )
