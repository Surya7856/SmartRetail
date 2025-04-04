
import ollama
import numpy as np
import datetime
import re
from typing import List, Dict, Any, Optional
from database.db_manager import db_connection

class DemandForecaster:
    def __init__(self):
        self.model_name = 'llama3.2:1b'
        
        self.llm_available = self._check_llm_available()
        
    def _check_llm_available(self) -> bool:
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
        
    def get_product_context(self, product_id: int) -> Dict[str, Any]:
        """Get comprehensive product context for better forecasting"""
        context = {}
        
        with db_connection() as conn:
            c = conn.cursor()
            
            
            c.execute('''SELECT current_price, competitor_price 
                         FROM pricing WHERE product_id=?''', (product_id,))
            price_data = c.fetchone()
            if price_data:
                context["price"] = price_data["current_price"]
                context["competitor_price"] = price_data["competitor_price"]
                context["price_difference"] = price_data["current_price"] - price_data["competitor_price"]
            
            
            c.execute('''SELECT AVG(sentiment_score) as avg_sentiment
                         FROM customer_feedback WHERE product_id=?''', (product_id,))
            sentiment = c.fetchone()
            if sentiment and sentiment["avg_sentiment"] is not None:
                context["sentiment"] = sentiment["avg_sentiment"]
                
            
            c.execute('''SELECT review_text FROM customer_feedback 
                         WHERE product_id=? ORDER BY ROWID DESC LIMIT 5''', (product_id,))
            reviews = c.fetchall()
            if reviews:
                context["recent_reviews"] = [r["review_text"] for r in reviews]
                
        return context
        
    def generate_forecast(self, product_id: int, store_id: int, days_ahead: int = 3) -> List[int]:
        """Generate demand forecast using LLM with comprehensive context"""
        
        with db_connection() as conn:
            c = conn.cursor()
            today = datetime.date.today()
            past_date = (today - datetime.timedelta(days=30)).isoformat()
            
            c.execute('''SELECT date, units_sold FROM sales_history 
                         WHERE product_id=? AND store_id=? AND date >= ?
                         ORDER BY date ASC''',
                      (product_id, store_id, past_date))
            sales_data = c.fetchall()
        
        if not sales_data:
            return [0] * days_ahead
            
        
        history = [row["units_sold"] for row in sales_data]
        dates = [row["date"] for row in sales_data]
        
        
        if not self.llm_available:
            return self._statistical_forecast(history, days_ahead)
        
        
        context = self.get_product_context(product_id)
        
        
        prompt = f"""Sales history for product {product_id} at store {store_id}:
        
Dates: {dates[-14:]}
Units sold: {history[-14:]}

"""
        
        if "price" in context and "competitor_price" in context:
            prompt += f"Our price: ${context['price']}, Competitor price: ${context['competitor_price']}\n"
            
        if "sentiment" in context:
            prompt += f"Customer sentiment score (0-1 scale): {context['sentiment']:.2f}\n"
            
        if "recent_reviews" in context and context["recent_reviews"]:
            prompt += f"Recent customer feedback: {context['recent_reviews'][0]}\n"
            
        prompt += f"\nBased on this data, predict sales for the next {days_ahead} days."
        prompt += "\nProvide ONLY numbers separated by commas, with no additional text."
            
        try:
            
            response = ollama.chat(model=self.model_name, messages=[
                {'role': 'user', 'content': prompt}
            ])
            
            prediction_text = response['message']['content'].strip()
            
            
            numbers = re.findall(r'\d+', prediction_text)
            predictions = [int(x) for x in numbers[:days_ahead]]
            
            
            while len(predictions) < days_ahead:
                
                if predictions:
                    predictions.append(predictions[-1])
                else:
                    predictions.append(int(np.mean(history[-7:])))
                
            return predictions[:days_ahead]
        except Exception as e:
            print(f"Forecast error: {e}")
            
            return self._statistical_forecast(history, days_ahead)
            
    def _statistical_forecast(self, history: List[int], days_ahead: int) -> List[int]:
        """Statistical forecasting as a fallback method"""
        if len(history) >= 14:
            
            recent_avg = np.mean(history[-7:])
            older_avg = np.mean(history[-14:-7])
            trend = recent_avg - older_avg
            
            
            forecast = []
            for i in range(days_ahead):
                forecast.append(int(max(0, recent_avg + trend * min(1.0, (i+1)/days_ahead))))
            return forecast
        else:
            
            avg = int(np.mean(history[-7:]) if len(history) >= 7 else np.mean(history))
            return [avg] * days_ahead