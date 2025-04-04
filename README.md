# Multi-Agent Retail Inventory Optimization System

An intelligent inventory management solution that uses collaborative AI agents to optimize retail inventory, predict demand, and improve operational efficiency.

## 🌟 Project Overview

This system addresses critical challenges in retail inventory management by replacing manual, reactive processes with an intelligent multi-agent approach. The solution enables seamless collaboration between stores, warehouses, suppliers, and customers to maintain optimal inventory levels, prevent stockouts, and reduce holding costs.

## 🤖 Agent Architecture

The system consists of several specialized agents:

- **Store Agent**: Monitors inventory levels and initiates restock requests
- **Demand Forecaster**: Predicts future product demand using historical data
- **Inventory Optimizer**: Calculates EOQ (Economic Order Quantity) and safety stock levels
- **Warehouse Agent**: Processes restock requests and updates inventory
- **Customer Agent**: Analyzes customer feedback and sentiment
- **Pricing Agent**: Optimizes product pricing based on inventory, demand, and competition
- **Main Controller**: Coordinates operations between all agents
- **Analytics System**: Generates reports and visualizations

## 🛠️ Technology Stack

- **LLM Engine**: Ollama running Llama 3.2-1b
- **Database**: SQLite 3
- **Distributed Computing**: Ray
- **Frontend**: Dashboard for visualization and reporting

## 📊 Key Features

- Real-time demand forecasting
- Dynamic price optimization
- Automated restock recommendations
- Customer sentiment analysis
- Comprehensive analytics dashboard
- Cross-store inventory coordination

## 📈 Performance Metrics

The system tracks several KPIs:
- Sales volume
- Fill rate
- Stockout frequency
- Inventory turnover
- Price change impact

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Ollama
- SQLite 3
- Ray

### Running a Simulation

```bash
python main.py
```

## 📁 Project Structure

```
retail-inventory-optimization/
├── agents/                   # Agent implementations
│   ├── store_agent.py
│   ├── forecaster.py
│   ├── optimizer.py
│   └── ...
├── database/                 # Database setup and queries
├── models/                   # LLM integration
├── simulation/               # Simulation engine
├── analytics/                # Reporting and analytics
├── dashboard/                # Visualization frontend
├── main.py         # Main simulation runner
└── requirements.txt          # Dependencies
```

## 🔍 Simulation Example

The system simulates real-world retail scenarios, processing inventory data, generating forecasts, and making intelligent decisions:

```
=== Day 1 (2025-04-04) ===
Processing Store 1
Product 1002: Stock=67, Predicted demand=[8, 10, 7], Sentiment=0.45, Recommended order=0
Updating price from $39.99 to $38.99
...
Daily KPIs: Sales=105, Fill Rate=90.0%, Stockouts=1
```

## 📄 License

[MIT](LICENSE)
