import numpy as np
import datetime
from database.db_manager import db_connection
from typing import Dict, List, Tuple, Any, Optional
import math

class PricingAgent:
    """Agent responsible for optimizing pricing based on demand elasticity,
    competitor prices, and inventory levels."""
    
    def __init__(self, store_id: int):
        self.store_id = store_id
    
    def get_product_data(self, product_id: int) -> Dict[str, Any]:
        """Get comprehensive product data for price optimization"""
        with db_connection() as conn:
            c = conn.cursor()
            
            # Get current price information
            c.execute('''SELECT current_price, competitor_price 
                         FROM pricing WHERE product_id=?''', (product_id,))
            price_data = c.fetchone()
            
            # Get inventory information
            c.execute('''SELECT stock_level FROM inventory 
                         WHERE product_id=? AND store_id=?''', 
                      (product_id, self.store_id))
            inventory = c.fetchone()
            
            # Get sentiment data
            c.execute('''SELECT AVG(sentiment_score) as avg_sentiment 
                        FROM customer_feedback
                        WHERE product_id=?''', (product_id,))
            sentiment = c.fetchone()
            
            # Get recent sales history
            today = datetime.date.today()
            past_date = (today - datetime.timedelta(days=30)).isoformat()
            c.execute('''SELECT date, units_sold FROM sales_history 
                         WHERE product_id=? AND store_id=? AND date >= ?
                         ORDER BY date ASC''',
                      (product_id, self.store_id, past_date))
            sales_history = c.fetchall()
            
            return {
                "current_price": price_data["current_price"] if price_data else None,
                "competitor_price": price_data["competitor_price"] if price_data else None,
                "stock_level": inventory["stock_level"] if inventory else 0,
                "sentiment": sentiment["avg_sentiment"] if sentiment and sentiment["avg_sentiment"] is not None else 0.5,
                "sales_history": [(row["date"], row["units_sold"]) for row in sales_history] if sales_history else []
            }
    
    def calculate_price_elasticity(self, sales_history: List[Tuple[str, int]], price_history: List[Tuple[str, float]]) -> float:
        """Calculate price elasticity of demand based on historical data"""
        if len(sales_history) < 7 or len(price_history) < 7:
            return -1.0  # Default elasticity if not enough data
        
        # Find periods where price changed
        price_changes = []
        for i in range(1, len(price_history)):
            if price_history[i][1] != price_history[i-1][1]:
                # Find corresponding sales before and after
                price_date = price_history[i][0]
                old_price = price_history[i-1][1]
                new_price = price_history[i][1]
                
                # Get average sales before price change (7 days)
                sales_before = []
                sales_after = []
                
                for date, units in sales_history:
                    if date < price_date and len(sales_before) < 7:
                        sales_before.append(units)
                    elif date >= price_date and len(sales_after) < 7:
                        sales_after.append(units)
                
                if sales_before and sales_after:
                    avg_sales_before = np.mean(sales_before)
                    avg_sales_after = np.mean(sales_after)
                    
                    # Calculate elasticity: (% change in quantity) / (% change in price)
                    pct_change_quantity = (avg_sales_after - avg_sales_before) / avg_sales_before
                    pct_change_price = (new_price - old_price) / old_price
                    
                    if pct_change_price != 0:
                        elasticity = pct_change_quantity / pct_change_price
                        price_changes.append(elasticity)
        
        # Return average elasticity if we have data, otherwise default
        return np.mean(price_changes) if price_changes else -1.0
    
    def optimize_price(self, product_id: int) -> Optional[float]:
        """Determine optimal price based on inventory, competitor prices, and elasticity"""
        data = self.get_product_data(product_id)
        
        if not data["current_price"] or not data["competitor_price"]:
            return None
            
        # Get price history (Note: In a real system, you would store price history)
        # For this example, we'll simulate with current price
        price_history = [(datetime.date.today().isoformat(), data["current_price"])]
        
        # Calculate elasticity (using simulated data)
        elasticity = -1.0  # Default elasticity (negative means lower price = higher demand)
        
        current_price = data["current_price"]
        competitor_price = data["competitor_price"]
        stock_level = data["stock_level"]
        sentiment = data["sentiment"]
        
        # Define reference demand at current price (based on recent history)
        #  -- rm 3 down
        reference_demand = 0
        if data["sales_history"]:
            recent_sales = [units for _, units in data["sales_history"][-7:]]
            reference_demand = np.mean(recent_sales) if recent_sales else 0
        
        # Base price adjustment factors
        inventory_factor = 0
        sentiment_factor = 0
        competition_factor = 0
        
        # Inventory-based adjustment (lower prices when overstocked, higher when understocked)
        if stock_level > 200:  # High inventory
            inventory_factor = -0.05  # Reduce price to increase demand
        elif stock_level < 50:  # Low inventory
            inventory_factor = 0.03  # Increase price to slow demand
            
        # Sentiment-based adjustment
        if sentiment > 0.7:  # Strong positive sentiment
            sentiment_factor = 0.02  # Can charge premium for popular items
        elif sentiment < 0.3:  # Negative sentiment
            sentiment_factor = -0.03  # Reduce price to increase appeal
            
        # Competition-based adjustment
        if current_price > competitor_price * 1.1:  # Significantly higher than competitor
            competition_factor = -0.04  # Reduce to be more competitive
        elif current_price < competitor_price * 0.9:  # Significantly lower than competitor
            competition_factor = 0.02  # Can increase while staying competitive
            
        # Combined adjustment
        total_adjustment = inventory_factor + sentiment_factor + competition_factor
        
        # Calculate new price
        new_price = current_price * (1 + total_adjustment)
        
        # Ensure price remains within reasonable bounds
        min_price = current_price * 0.8
        max_price = current_price * 1.2
        
        new_price = max(min_price, min(max_price, new_price))
        
        # Round to appropriate price point (e.g., $19.99 instead of $20.00)
        new_price = math.floor(new_price) - 0.01
        
        return new_price
    
    def update_price(self, product_id: int, new_price: float) -> bool:
        """Update the price in the database"""
        try:
            with db_connection() as conn:
                c = conn.cursor()
                c.execute('''UPDATE pricing SET current_price=? WHERE product_id=?''',
                         (new_price, product_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating price: {e}")
            return False