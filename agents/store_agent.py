import ollama
import numpy as np
import datetime
from database.db_manager import db_connection

class StoreAgent:
    def __init__(self, store_id):
        self.store_id = store_id
        self.model_name = 'llama3.2:1b'
        
        self.llm_available = self._check_llm_available()
        
    def _check_llm_available(self):
        """Check if Ollama LLM is available"""
        try:
            
            ollama.chat(model=self.model_name, messages=[
                {'role': 'user', 'content': 'ping'}
            ])
            return True
        except Exception as e:
            print(f"Warning: Ollama LLM not available - {e}")
            print("Using fallback methods for predictions")
            return False
            
    def check_stock(self, product_id):
        """Check current stock level for a product"""
        with db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT stock_level FROM inventory 
                         WHERE product_id=? AND store_id=?''',
                      (product_id, self.store_id))
            result = c.fetchone()
            return result['stock_level'] if result else 0
            
    def get_sales_history(self, product_id, days=30):
        """Get sales history for a product over the last n days"""
        today = datetime.date.today()
        start_date = (today - datetime.timedelta(days=days)).isoformat()
        
        with db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT date, units_sold FROM sales_history 
                         WHERE product_id=? AND store_id=? AND date >= ?
                         ORDER BY date ASC''',
                      (product_id, self.store_id, start_date))
            return c.fetchall()
    
    def predict_demand(self, product_id):
        """Predict demand for next 3 days using LLM or fallback methods"""
        
        sales_history = self.get_sales_history(product_id)
        sales_data = [row['units_sold'] for row in sales_history]
        
        if not sales_data:
            return [0, 0, 0]  
        
        
        if not self.llm_available:
            return self._statistical_forecast(sales_data)
            
        
        with db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT current_price, competitor_price FROM pricing 
                         WHERE product_id=?''', (product_id,))
            price_data = c.fetchone()
        
        price_info = ""
        if price_data:
            price_info = f"Our price: ${price_data['current_price']}, Competitor price: ${price_data['competitor_price']}"
            
        
        prompt = f"""Product sales history for the last {len(sales_data)} days: {sales_data[-7:]}
        {price_info}
        Predict next 3 days demand. Consider trends, seasonality and price differences if available.
        Respond only with numbers separated by commas."""
        
        try:
            
            response = ollama.chat(model=self.model_name, messages=[
                {'role': 'user', 'content': prompt}
            ])
            
            prediction_text = response['message']['content'].strip()
            
            
            import re
            numbers = re.findall(r'\d+', prediction_text)
            predictions = [int(x) for x in numbers[:3]]
            
            
            while len(predictions) < 3:
                
                predictions.append(predictions[-1] if predictions else 0)
                
            return predictions[:3]
        except Exception as e:
            print(f"Forecast error: {e}")
            
            return self._statistical_forecast(sales_data)
    
    def _statistical_forecast(self, sales_data):
        """Simple statistical forecast as fallback"""
        if len(sales_data) >= 14:
            
            recent_avg = np.mean(sales_data[-7:])
            older_avg = np.mean(sales_data[-14:-7])
            trend = recent_avg - older_avg
            
            
            forecast = [
                int(max(0, recent_avg + trend * 0.5)),
                int(max(0, recent_avg + trend * 0.8)),
                int(max(0, recent_avg + trend))
            ]
            return forecast
        else:
            
            avg = int(np.mean(sales_data[-7:]) if len(sales_data) >= 7 else np.mean(sales_data))
            return [avg, avg, avg]
    
    def get_optimal_supplier(self, product_id, quantity_needed):
        """Find the best supplier based on cost and lead time"""
        with db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT supplier_id, lead_time, cost FROM suppliers 
                         WHERE product_id=?''', (product_id,))
            suppliers = c.fetchall()
        
        if not suppliers:   
            return None
        
        
        best_supplier = min(suppliers, 
                           key=lambda s: s['cost'] * quantity_needed + s['lead_time'] * 10)
        return best_supplier['supplier_id']
    
    def request_restock(self, product_id, quantity):
        """Request product restock"""
        supplier_id = self.get_optimal_supplier(product_id, quantity)
        
        if not supplier_id:
            print(f"No supplier found for product {product_id}")
            return False
            
        with db_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO restock_requests 
                        (store_id, product_id, quantity, supplier_id, status) 
                        VALUES (?, ?, ?, ?, 'pending')''',
                     (self.store_id, product_id, quantity, supplier_id))
            conn.commit()
        return True
    
    def analyze_sentiment(self, product_id):
        """Get customer sentiment for a product"""
        with db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT AVG(sentiment_score) as avg_sentiment 
                         FROM customer_feedback
                         WHERE product_id=?''', (product_id,))
            result = c.fetchone()
            
        return result['avg_sentiment'] if result and result['avg_sentiment'] is not None else 0
    
    def calculate_recommended_order(self, product_id):
        """Calculate recommended order based on predicted demand vs current stock"""
        current_stock = self.check_stock(product_id)
        predicted_demand = self.predict_demand(product_id)
        
        
        total_predicted_demand = sum(predicted_demand)
        
        
        if total_predicted_demand > current_stock:
            
            buffer_factor = 1.5
            recommended_quantity = int((total_predicted_demand - current_stock) * buffer_factor)
            
            
            recommended_quantity = max(10, recommended_quantity)
            
            
            self.request_restock(product_id, recommended_quantity)
            
            return recommended_quantity
        
        return 0  