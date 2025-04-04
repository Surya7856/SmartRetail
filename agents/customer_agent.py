import ollama
import datetime
import numpy as np
from database.db_manager import db_connection
from typing import Dict, List, Any, Optional

class CustomerAgent:
    """Agent that analyzes customer feedback and predicts customer behavior."""
    
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
            print("Using fallback methods for customer analysis")
            return False
    
    def analyze_feedback(self, product_id: int) -> Dict[str, Any]:
        """Analyze customer feedback for a product"""
        with db_connection() as conn:
            c = conn.cursor()
            
            
            c.execute('''SELECT review_text, sentiment_score 
                         FROM customer_feedback 
                         WHERE product_id = ? 
                         ORDER BY ROWID DESC LIMIT 20''', (product_id,))
            
            feedback = c.fetchall()
            
        if not feedback:
            return {
                "sentiment_score": 0.5,
                "key_themes": [],
                "summary": "No customer feedback available"
            }
            
        
        sentiment_scores = [f["sentiment_score"] for f in feedback if f["sentiment_score"] is not None]
        avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0.5
        
        
        key_themes = []
        summary = ""
        
        if self.llm_available:
            review_texts = [f["review_text"] for f in feedback if f["review_text"]]
            
            if review_texts:
                
                prompt = f"""Analyze these customer reviews for product 
                    {review_texts[:10]}

                    1. What are the 3-5 key themes mentioned by customers?
                    2. Provide a brief summary of overall customer sentiment.

                    Format your response as:
                    KEY THEMES:
                    - First theme
                    - Second theme
                    - etc.

                    SUMMARY:
                    Brief summary here.
                    """
                try:
                    
                    response = ollama.chat(model=self.model_name, messages=[
                        {'role': 'user', 'content': prompt}
                    ])
                    
                    response_text = response['message']['content'].strip()
                    
                    
                    parts = response_text.split("KEY THEMES:")
                    if len(parts) > 1:
                        themes_and_summary = parts[1].split("SUMMARY:")
                        
                        
                        themes_text = themes_and_summary[0].strip()
                        themes_lines = [line.strip()[2:] for line in themes_text.split("\n") if line.strip().startswith("-")]
                        key_themes = themes_lines
                        
                        
                        if len(themes_and_summary) > 1:
                            summary = themes_and_summary[1].strip()
                except Exception as e:
                    print(f"Error analyzing feedback with LLM: {e}")
                    
                    summary = f"Average sentiment score: {avg_sentiment:.2f}"
                    
                    
                    if review_texts:
                        
                        all_text = " ".join(review_texts).lower()
                        
                        words = all_text.split()
                        
                        word_counts = {}
                        for word in words:
                            if len(word) > 3:  
                                word_counts[word] = word_counts.get(word, 0) + 1
                        
                        
                        top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                        key_themes = [word for word, _ in top_words]
        else:
            
            summary = f"Average sentiment score: {avg_sentiment:.2f}"
            
            
            positive_count = sum(1 for s in sentiment_scores if s > 0.7)
            negative_count = sum(1 for s in sentiment_scores if s < 0.3)
            
            if positive_count > len(sentiment_scores) / 2:
                key_themes.append("Mostly positive reviews")
            elif negative_count > len(sentiment_scores) / 2:
                key_themes.append("Mostly negative reviews")
            else:
                key_themes.append("Mixed reviews")
        
        return {
            "sentiment_score": float(avg_sentiment),
            "key_themes": key_themes,
            "summary": summary,
            "review_count": len(feedback)
        }
    
    def predict_response_to_price_change(self, product_id: int, price_change_percent: float) -> Dict[str, Any]:
        """Predict customer response to a price change"""
        
        with db_connection() as conn:
            c = conn.cursor()
            
            c.execute('''SELECT current_price, competitor_price 
                         FROM pricing 
                         WHERE product_id = ?''', (product_id,))
            
            price_data = c.fetchone()
            
            if not price_data:
                return {"error": "No pricing data available for this product"}
                
            current_price = price_data["current_price"]
            competitor_price = price_data["competitor_price"]
            
            
            c.execute('''SELECT date, units_sold 
                         FROM sales_history 
                         WHERE product_id = ? 
                         ORDER BY date DESC 
                         LIMIT 30''', (product_id,))
            
            sales_history = c.fetchall()
            
            
            c.execute('''SELECT AVG(sentiment_score) as avg_sentiment 
                         FROM customer_feedback 
                         WHERE product_id = ?''', (product_id,))
            
            sentiment_result = c.fetchone()
            sentiment = sentiment_result["avg_sentiment"] if sentiment_result and sentiment_result["avg_sentiment"] is not None else 0.5
        
        if not sales_history:
            return {"error": "No sales history available for this product"}
            
        
        avg_sales = np.mean([s["units_sold"] for s in sales_history])
        
        
        price_elasticity = -1.5  
        
        
        if sentiment > 0.7:
            
            price_elasticity *= 0.7
        elif sentiment < 0.4:
            
            price_elasticity *= 1.3
            
        
        if current_price < competitor_price and price_change_percent > 0:
            
            price_elasticity *= 0.8  
        elif current_price > competitor_price and price_change_percent > 0:
            
            price_elasticity *= 1.4  
            
        
        demand_change_percent = price_change_percent * price_elasticity
        
        
        new_expected_sales = avg_sales * (1 + demand_change_percent / 100)
        
        
        new_price = current_price * (1 + price_change_percent / 100)
        
        
        current_daily_revenue = avg_sales * current_price
        new_daily_revenue = new_expected_sales * new_price
        revenue_change = new_daily_revenue - current_daily_revenue
        
        
        if demand_change_percent < -20:
            assessment = "Highly negative customer response expected with significant sales reduction"
        elif demand_change_percent < -10:
            assessment = "Moderate negative customer response with noticeable sales reduction"
        elif demand_change_percent < -5:
            assessment = "Slight negative customer response expected"
        elif demand_change_percent < 5:
            assessment = "Minimal impact on customer behavior expected"
        else:
            assessment = "Positive customer response with increased sales expected"
            
        return {
            "current_price": float(current_price),
            "new_price": float(new_price),
            "price_change_percent": float(price_change_percent),
            "estimated_elasticity": float(price_elasticity),
            "expected_demand_change_percent": float(demand_change_percent),
            "current_avg_daily_sales": float(avg_sales),
            "new_expected_daily_sales": float(new_expected_sales),
            "daily_revenue_change": float(revenue_change),
            "assessment": assessment
        }