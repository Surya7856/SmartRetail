import numpy as np
from typing import Dict, List, Any, Optional
from database.db_manager import db_connection

class InventoryOptimizer:
    """Advanced inventory optimization using reinforcement learning principles."""
    
    def __init__(self):
        
        self.holding_cost_rate = 0.02  
        self.stockout_penalty = 0.10   
        self.ordering_cost = 15.00     
        self.learning_rate = 0.1       
        self.discount_factor = 0.9     
        self.exploration_rate = 0.2    
        
        
        self.q_values = {}
    
    def calculate_optimal_order_quantity(self, product_id: int, store_id: int) -> Dict[str, Any]:
        """Calculate the optimal order quantity using EOQ principles with adjustments"""
        try:
            
            with db_connection() as conn:
                c = conn.cursor()
                
                
                c.execute('''SELECT p.current_price, s.cost
                             FROM pricing p
                             JOIN suppliers s ON p.product_id = s.product_id
                             WHERE p.product_id = ?
                             ORDER BY s.cost ASC
                             LIMIT 1''', (product_id,))
                price_cost = c.fetchone()
                
                if not price_cost:
                    return {"order_quantity": 0, "reorder_point": 0, "message": "No pricing or supplier data"}
                    
                price = price_cost["current_price"]
                cost = price_cost["cost"]
                
                
                c.execute('''SELECT AVG(units_sold) as avg_demand
                             FROM sales_history
                             WHERE product_id = ? AND store_id = ?
                             AND date >= date('now', '-30 days')''', 
                         (product_id, store_id))
                demand_stats = c.fetchone()
                
                if not demand_stats or demand_stats["avg_demand"] is None:
                    return {"order_quantity": 0, "reorder_point": 0, "message": "Insufficient sales history"}
                    
                avg_demand = max(0.1, demand_stats["avg_demand"])  
                
                
                c.execute('''SELECT units_sold
                             FROM sales_history
                             WHERE product_id = ? AND store_id = ?
                             AND date >= date('now', '-30 days')''', 
                         (product_id, store_id))
                sales_data = [row["units_sold"] for row in c.fetchall()]
                
                
                std_demand = np.std(sales_data) if sales_data else max(1, avg_demand * 0.3)
                
                
                c.execute('''SELECT stock_level FROM inventory
                             WHERE product_id = ? AND store_id = ?''',
                         (product_id, store_id))
                inventory = c.fetchone()
                current_stock = inventory["stock_level"] if inventory else 0
                
                
                c.execute('''SELECT MIN(lead_time) as lead_time
                             FROM suppliers WHERE product_id = ?''',
                         (product_id,))
                lead_time_result = c.fetchone()
                lead_time = lead_time_result["lead_time"] if lead_time_result and lead_time_result["lead_time"] is not None else 7
            
            
            holding_cost = max(0.001, cost * self.holding_cost_rate)  
            annual_demand = avg_demand * 365  
            
            
            
            eoq = np.sqrt((2 * annual_demand * self.ordering_cost) / holding_cost)
            eoq = max(1, round(eoq))
            
            
            service_factor = 1.96  
            safety_stock = service_factor * std_demand * np.sqrt(lead_time)
            safety_stock = max(0, round(safety_stock))
            
            
            reorder_point = (avg_demand * lead_time) + safety_stock
            reorder_point = max(1, round(reorder_point))
            
            
            demand_level = "medium"  
            if avg_demand > 0:
                if std_demand / avg_demand > 0.5:
                    demand_level = "high"
                elif std_demand / avg_demand < 0.2:
                    demand_level = "low"
            
            price_ratio = "medium"  
            if cost > 0:
                if price / cost > 2:
                    price_ratio = "high"
                elif price / cost < 1.5:
                    price_ratio = "low"
            
            state_key = self.state_to_key(current_stock, demand_level, price_ratio)
            
            
            should_order = current_stock <= reorder_point
            
            
            if state_key in self.q_values and np.random.random() > self.exploration_rate:
                q_order = self.q_values[state_key].get("order", 0)
                q_wait = self.q_values[state_key].get("wait", 0)
                
                
                if q_order > q_wait + 10:  
                    should_order = True
                elif q_wait > q_order + 10:
                    should_order = False
            
            
            order_quantity = 0
            if should_order:
                
                order_quantity = max(0, eoq - current_stock + reorder_point)
            
            return {
                "order_quantity": int(order_quantity),
                "reorder_point": int(reorder_point),
                "economic_order_quantity": int(eoq),
                "safety_stock": int(safety_stock),
                "avg_demand": float(avg_demand),
                "lead_time": int(lead_time),
                "current_stock": int(current_stock),
                "should_order": should_order,
                "state_key": state_key
            }
        except Exception as e:
            
            return {"order_quantity": 0, "reorder_point": 0, "message": f"Error: {str(e)}"}
    
    def state_to_key(self, stock_level: int, demand_level: str, price_ratio: str) -> str:
        """Convert state to a key for the Q-value dictionary with finer granularity"""
        
        if stock_level < 5:
            stock_state = "very_low"
        elif stock_level < 20:
            stock_state = "low"
        elif stock_level < 50:
            stock_state = "medium_low"
        elif stock_level < 100:
            stock_state = "medium"
        elif stock_level < 200:
            stock_state = "medium_high"
        else:
            stock_state = "high"
            
        return f"{stock_state}_{demand_level}_{price_ratio}"
    
    def update_policy(self, state_key: str, action: str, reward: float, next_state_key: str) -> None:
        """Update Q-values using Q-learning"""
        
        if state_key not in self.q_values:
            self.q_values[state_key] = {"order": 0.0, "wait": 0.0}
            
        if next_state_key not in self.q_values:
            self.q_values[next_state_key] = {"order": 0.0, "wait": 0.0}
        
        
        current_q = self.q_values[state_key][action]
        max_next_q = max(self.q_values[next_state_key].values())
        
        
        updated_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
        
        self.q_values[state_key][action] = updated_q
    
    def simulate_policy(self, product_id: int, store_id: int, days: int = 30) -> Dict[str, Any]:
        """Simulate inventory policy for a product over time, now utilizing RL decisions"""
        try:
            
            with db_connection() as conn:
                c = conn.cursor()
                
                
                c.execute('''SELECT p.current_price, MIN(s.cost) as cost
                             FROM pricing p
                             JOIN suppliers s ON p.product_id = s.product_id
                             WHERE p.product_id = ?
                             GROUP BY p.product_id''', (product_id,))
                price_cost = c.fetchone()
                
                if not price_cost:
                    return {"error": "No pricing or supplier data available"}
                    
                price = price_cost["current_price"]
                cost = price_cost["cost"]
                
                
                c.execute('''SELECT units_sold FROM sales_history
                             WHERE product_id = ? AND store_id = ?
                             ORDER BY date DESC LIMIT 30''',
                         (product_id, store_id))
                demand_history = [row["units_sold"] for row in c.fetchall()]
                
                if not demand_history:
                    
                    mean_demand = 10
                    std_demand = 3
                else:
                    mean_demand = np.mean(demand_history) 
                    std_demand = max(1, np.std(demand_history))
                    
                
                c.execute('''SELECT stock_level FROM inventory
                             WHERE product_id = ? AND store_id = ?''',
                         (product_id, store_id))
                inventory = c.fetchone()
                current_stock = inventory["stock_level"] if inventory else 50  
                
                
                c.execute('''SELECT MIN(lead_time) as lead_time
                             FROM suppliers WHERE product_id = ?''',
                         (product_id,))
                lead_time_result = c.fetchone()
                lead_time = lead_time_result["lead_time"] if lead_time_result and lead_time_result["lead_time"] is not None else 7
                
            
            stock = current_stock
            total_profit = 0
            stockout_days = 0
            holding_cost_total = 0
            ordering_cost_total = 0
            revenue_total = 0
            days_to_delivery = 0
            pending_delivery = 0
            daily_results = []
            
            
            if len(demand_history) >= days:
                daily_demand = demand_history[:days]
            else:
                
                daily_demand = np.maximum(1, np.random.normal(mean_demand, std_demand, days)).astype(int)
            
            
            for day in range(days):
                
                demand = daily_demand[day]
                
                
                if days_to_delivery > 0:
                    days_to_delivery -= 1
                    if days_to_delivery == 0:
                        stock += pending_delivery
                        pending_delivery = 0
                
                
                demand_level = "high" if demand > mean_demand * 1.2 else "low" if demand < mean_demand * 0.8 else "medium"
                price_ratio = "high" if price > cost * 2 else "low" if price < cost * 1.5 else "medium"
                state_key = self.state_to_key(stock, demand_level, price_ratio)
                
                
                order_quantity = 0
                action = "wait"
                
                
                eoq_result = self.calculate_optimal_order_quantity(product_id, store_id)
                should_order_eoq = stock <= eoq_result.get("reorder_point", 0) and days_to_delivery == 0
                
                
                should_order = should_order_eoq
                if state_key in self.q_values:
                    
                    if np.random.random() > self.exploration_rate:
                        
                        q_order = self.q_values[state_key].get("order", 0)
                        q_wait = self.q_values[state_key].get("wait", 0)
                        should_order = q_order > q_wait
                    
                
                if should_order and days_to_delivery == 0:
                    order_quantity = eoq_result.get("economic_order_quantity", 0)
                    days_to_delivery = lead_time
                    pending_delivery = order_quantity
                    ordering_cost_total += self.ordering_cost
                    action = "order"
                
                
                sold = min(stock, demand)
                missed = demand - sold
                
                
                stock -= sold
                
                
                revenue = sold * price
                cogs = sold * cost
                holding_cost = stock * (cost * self.holding_cost_rate / 365)  
                stockout_cost = missed * (price * self.stockout_penalty)
                
                day_profit = revenue - cogs - holding_cost - stockout_cost
                if action == "order":
                    day_profit -= self.ordering_cost
                    
                
                total_profit += day_profit
                revenue_total += revenue
                holding_cost_total += holding_cost
                if missed > 0:
                    stockout_days += 1
                
                
                daily_results.append({
                    "day": day + 1,
                    "demand": int(demand),
                    "sold": int(sold),
                    "missed": int(missed),
                    "stock": int(stock),
                    "ordered": int(order_quantity) if action == "order" else 0,
                    "revenue": float(revenue),
                    "profit": float(day_profit),
                    "action": action,
                    "state": state_key
                })
                
                
                next_demand = daily_demand[min(day+1, days-1)]
                next_demand_level = "high" if next_demand > mean_demand * 1.2 else "low" if next_demand < mean_demand * 0.8 else "medium"
                next_state_key = self.state_to_key(stock, next_demand_level, price_ratio)
                
                
                reward = day_profit
                
                
                self.update_policy(state_key, action, reward, next_state_key)
            
            
            service_level = 1 - (stockout_days / days) if days > 0 else 0
            
            
            avg_inventory = (current_stock + stock) / 2 if (current_stock + stock) > 0 else 1
            inventory_turnover = revenue_total / (cost * avg_inventory) if cost > 0 and avg_inventory > 0 else 0
            
            return {
                "total_profit": float(total_profit),
                "revenue": float(revenue_total),
                "stockout_days": int(stockout_days),
                "service_level": float(service_level),
                "holding_cost": float(holding_cost_total),
                "ordering_cost": float(ordering_cost_total),
                "inventory_turnover": float(inventory_turnover),
                "final_stock": int(stock),
                "daily_results": daily_results
            }
        except Exception as e:
            
            return {"error": f"Simulation error: {str(e)}"}