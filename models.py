from datetime import datetime
from app import db

class TradingPair(db.Model):
    """Model for cryptocurrency trading pairs"""
    id = db.Column(db.Integer, primary_key=True)
    pair_name = db.Column(db.String(20), nullable=False, unique=True)
    base_currency = db.Column(db.String(10), nullable=False)
    quote_currency = db.Column(db.String(10), nullable=False)
    max_concurrent_trades = db.Column(db.Integer, default=5)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with TraderConfig
    trader_config = db.relationship('TraderConfig', backref='trading_pair', uselist=False, cascade='all, delete-orphan')
    
    # Relationship with Trade
    trades = db.relationship('Trade', backref='trading_pair', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<TradingPair {self.pair_name}>"


class TraderConfig(db.Model):
    """Model for trader configuration parameters"""
    id = db.Column(db.Integer, primary_key=True)
    trading_pair_id = db.Column(db.Integer, db.ForeignKey('trading_pair.id'), nullable=False)
    profit_margin = db.Column(db.Float, nullable=False, default=0.5)  # Percentage
    trade_size = db.Column(db.Float, nullable=False, default=0.01)  # Base amount
    max_open_time = db.Column(db.Integer, default=48)  # Hours
    stop_loss = db.Column(db.Float, nullable=True)  # Percentage, optional
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # AI-optimized parameters
    ai_optimized = db.Column(db.Boolean, default=False)
    last_optimization = db.Column(db.DateTime, nullable=True)
    optimization_reason = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f"<TraderConfig for {self.trading_pair.pair_name}>"


class Trade(db.Model):
    """Model for individual trades"""
    id = db.Column(db.Integer, primary_key=True)
    trading_pair_id = db.Column(db.Integer, db.ForeignKey('trading_pair.id'), nullable=False)
    external_id = db.Column(db.String(50), nullable=True)  # ID from the trading platform
    entry_price = db.Column(db.Float, nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    size = db.Column(db.Float, nullable=False)  # Amount in base currency
    status = db.Column(db.String(20), nullable=False, default='open')  # open, closed, cancelled
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    profit_loss = db.Column(db.Float, nullable=True)  # Actual P/L when closed
    ai_recommended = db.Column(db.Boolean, default=False)  # Was this trade recommended by AI
    recommendation_reason = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f"<Trade {self.id} - {self.trading_pair.pair_name} - {self.status}>"


class MarketCondition(db.Model):
    """Model for storing market condition analysis"""
    id = db.Column(db.Integer, primary_key=True)
    trading_pair_id = db.Column(db.Integer, db.ForeignKey('trading_pair.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    price = db.Column(db.Float, nullable=False)
    volume_24h = db.Column(db.Float, nullable=False)
    volatility = db.Column(db.Float, nullable=True)  # Standard deviation of returns
    trend_direction = db.Column(db.String(10), nullable=True)  # up, down, sideways
    trend_strength = db.Column(db.Float, nullable=True)  # 0-1 scale
    trading_recommended = db.Column(db.Boolean, default=True)
    reasoning = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f"<MarketCondition for {self.trading_pair.pair_name} at {self.timestamp}>"


class AuditLog(db.Model):
    """Model for tracking AI agent actions"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action_type = db.Column(db.String(50), nullable=False)  # market_analysis, parameter_update, trade_recommendation, etc.
    description = db.Column(db.Text, nullable=False)
    trading_pair_id = db.Column(db.Integer, db.ForeignKey('trading_pair.id'), nullable=True)
    trade_id = db.Column(db.Integer, db.ForeignKey('trade.id'), nullable=True)
    
    def __repr__(self):
        return f"<AuditLog {self.action_type} at {self.timestamp}>"
