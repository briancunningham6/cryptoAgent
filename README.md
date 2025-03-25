# Crypto Trading AI Agent

An AI-powered agent to manage cryptocurrency trading operations through automated market analysis, parameter optimization, and natural language interaction.

## Features

- **Market Analysis**: Statistical analysis of market conditions before placing trades
- **Trader Monitoring**: Monitors inactive traders and decides when to allocate funds based on market conditions
- **Parameter Optimization**: Dynamically optimizes trader parameters (profit margin, trade size, etc.)
- **System Monitoring**: Reports faults and issues in the trading system
- **Natural Language Interface**: Chat with the AI agent about market conditions and trading decisions

## Technical Stack

- **Backend**: Flask (Python)
- **Database**: SQLAlchemy with PostgreSQL
- **AI Integration**: OpenAI API
- **Frontend**: HTML/CSS/JavaScript with Bootstrap
- **Data Visualization**: Chart.js

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL database
- OpenAI API key

### Installation

1. Clone the repository
```bash
git clone https://github.com/your-username/cryptoAgent.git
cd cryptoAgent
```

2. Install dependencies
There are three ways to install dependencies:

Option 1: Using the standard requirements.txt file:
```bash
pip install -r requirements.txt
```

Option 2: Using the dependencies.txt file (identical content to requirements.txt):
```bash
pip install -r dependencies.txt
```

Option 3: Install each package individually:
```bash
pip install apscheduler email-validator flask flask-sqlalchemy gunicorn matplotlib numpy openai pandas psycopg2-binary python-dotenv requests scikit-learn sqlalchemy
```

3. Configure environment variables
```bash
# Create a .env file with the following variables
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://username:password@localhost/dbname
```

4. Run the application
```bash
# For development
python main.py

# For production (using gunicorn)
gunicorn --bind 0.0.0.0:5000 main:app
```

> **Note:** When running the application, you may see connection errors related to the trading API. This is expected behavior if you don't have a trading platform running locally. The application will still function for demonstration purposes, but some features that depend on real-time trading data will be limited.

## Architecture

The application follows a service-oriented architecture with the following components:

- **Market Analyzer**: Analyzes cryptocurrency market conditions
- **Trader Monitor**: Monitors trading activities and detects issues
- **Parameter Optimizer**: Optimizes trading parameters based on performance
- **Trading API Client**: Interacts with cryptocurrency exchanges
- **OpenAI Service**: Handles integration with OpenAI for AI capabilities

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational purposes only. Trading cryptocurrencies involves significant risk. Use at your own risk.