import datetime
from typing import Dict, List, Any, Optional
from database.db_manager import db_connection

class RetailDashboard:
    """Dashboard data generator for the retail optimization system"""
    
    def __init__(self):
        pass
    
    def generate_dashboard_data(self):
        """Generate data for the main dashboard"""
        return {
            "inventory_summary": self.get_inventory_summary(),
            "sales_trends": self.get_sales_trends(),
            "stockout_risk": self.get_stockout_risk_products(),
            "restock_status": self.get_restock_status(),
            "efficiency_metrics": self.get_efficiency_metrics()
        }
    
    def get_inventory_summary(self):
        """Get summary of current inventory levels"""
        with db_connection() as conn:
            c = conn.cursor()
            
            c.execute('''SELECT store_id, SUM(stock_level) as total_stock 
                         FROM inventory 
                         GROUP BY store_id''')
            store_inventory = c.fetchall()
            
            
            c.execute('''SELECT COUNT(*) as low_stock_count 
                         FROM inventory 
                         WHERE stock_level < 20''')
            low_stock = c.fetchone()
            
            
            c.execute('''SELECT COUNT(*) as healthy_stock_count 
                         FROM inventory 
                         WHERE stock_level BETWEEN 20 AND 200''')
            healthy_stock = c.fetchone()
            
            
            c.execute('''SELECT COUNT(*) as overstock_count 
                         FROM inventory 
                         WHERE stock_level > 200''')
            overstock = c.fetchone()
            
            return {
                "store_inventory": [
                    {"store_id": row["store_id"], "total_stock": row["total_stock"]}
                    for row in store_inventory
                ],
                "stock_health": {
                    "low_stock": low_stock["low_stock_count"] if low_stock else 0,
                    "healthy_stock": healthy_stock["healthy_stock_count"] if healthy_stock else 0,
                    "overstock": overstock["overstock_count"] if overstock else 0
                }
            }
    
    def get_sales_trends(self):
        """Get sales trends for the past 30 days"""
        with db_connection() as conn:
            c = conn.cursor()
            
            today = datetime.date.today()
            past_date = (today - datetime.timedelta(days=30)).isoformat()
            
            
            c.execute('''SELECT date, SUM(units_sold) as total_sales 
                         FROM sales_history 
                         WHERE date >= ? 
                         GROUP BY date 
                         ORDER BY date ASC''', (past_date,))
            daily_sales = c.fetchall()
            
            
            c.execute('''SELECT product_id, SUM(units_sold) as total_sales 
                         FROM sales_history 
                         WHERE date >= ? 
                         GROUP BY product_id 
                         ORDER BY total_sales DESC 
                         LIMIT 5''', (past_date,))
            top_products = c.fetchall()
            
            
            c.execute('''SELECT store_id, SUM(units_sold) as total_sales 
                         FROM sales_history 
                         WHERE date >= ? 
                         GROUP BY store_id''', (past_date,))
            store_sales = c.fetchall()
            
            return {
                "daily_sales": [
                    {"date": row["date"], "sales": row["total_sales"]}
                    for row in daily_sales
                ],
                "top_products": [
                    {"product_id": row["product_id"], "sales": row["total_sales"]}
                    for row in top_products
                ],
                "store_sales": [
                    {"store_id": row["store_id"], "sales": row["total_sales"]}
                    for row in store_sales
                ]
            }
    
    def get_stockout_risk_products(self):
        """Get products at risk of stockout"""
        with db_connection() as conn:
            c = conn.cursor()
            
            
            c.execute('''
                SELECT 
                    i.product_id, 
                    i.store_id, 
                    i.stock_level,
                    AVG(s.units_sold) as avg_daily_sales
                FROM 
                    inventory i
                JOIN 
                    sales_history s 
                    ON i.product_id = s.product_id AND i.store_id = s.store_id
                WHERE 
                    s.date >= date('now', '-7 days')
                GROUP BY 
                    i.product_id, i.store_id
                HAVING 
                    i.stock_level < (avg_daily_sales * 3)  -- Less than 3 days of stock
                ORDER BY 
                    (i.stock_level / avg_daily_sales) ASC  -- Days of inventory remaining
                LIMIT 10
            ''')
            
            at_risk_products = c.fetchall()
            
            return [
                {
                    "product_id": row["product_id"],
                    "store_id": row["store_id"],
                    "stock_level": row["stock_level"],
                    "avg_daily_sales": row["avg_daily_sales"],
                    "days_remaining": row["stock_level"] / row["avg_daily_sales"] if row["avg_daily_sales"] > 0 else float('inf')
                }
                for row in at_risk_products
            ]
    
    def get_restock_status(self):
        """Get status of recent restock requests"""
        with db_connection() as conn:
            c = conn.cursor()
            
            
            c.execute('''
                SELECT 
                    id, store_id, product_id, quantity, status, request_date
                FROM 
                    restock_requests
                WHERE 
                    request_date >= date('now', '-14 days')
                ORDER BY 
                    request_date DESC
                LIMIT 20
            ''')
            
            restock_requests = c.fetchall()
            
            
            c.execute('''
                SELECT 
                    status, COUNT(*) as count
                FROM 
                    restock_requests
                WHERE 
                    request_date >= date('now', '-14 days')
                GROUP BY 
                    status
            ''')
            
            status_summary = c.fetchall()
            
            return {
                "recent_requests": [
                    {
                        "id": row["id"],
                        "store_id": row["store_id"],
                        "product_id": row["product_id"],
                        "quantity": row["quantity"],
                        "status": row["status"],
                        "request_date": row["request_date"]
                    }
                    for row in restock_requests
                ],
                "status_summary": [
                    {"status": row["status"], "count": row["count"]}
                    for row in status_summary
                ]
            }
    
    def get_efficiency_metrics(self):
        """Calculate and return efficiency metrics"""
        with db_connection() as conn:
            c = conn.cursor()
            
            
            c.execute('''
                SELECT 
                    SUM(i.stock_level * s.cost) as inventory_value
                FROM 
                    inventory i
                JOIN 
                    suppliers s ON i.product_id = s.product_id
                GROUP BY 
                    s.product_id
            ''')
            
            inventory_value_result = c.fetchone()
            inventory_value = inventory_value_result["inventory_value"] if inventory_value_result else 0
            
            
            c.execute('''
                SELECT 
                    SUM(s.units_sold * p.current_price) as sales_value
                FROM 
                    sales_history s
                JOIN 
                    pricing p ON s.product_id = p.product_id
                WHERE 
                    s.date >= date('now', '-30 days')
            ''')
            
            sales_result = c.fetchone()
            sales_value = sales_result["sales_value"] if sales_result else 0
            
            
            inventory_turnover = (sales_value * 12) / inventory_value if inventory_value > 0 else 0
            
            
            c.execute('''
                SELECT 
                    COUNT(*) as stockout_count
                FROM 
                    inventory
                WHERE 
                    stock_level = 0
            ''')
            
            stockout_result = c.fetchone()
            stockout_count = stockout_result["stockout_count"] if stockout_result else 0
            
            c.execute('''
                SELECT 
                    COUNT(*) as total_inventory_records
                FROM 
                    inventory
            ''')
            
            total_result = c.fetchone()
            total_count = total_result["total_inventory_records"] if total_result else 1  
            
            stockout_rate = (stockout_count / total_count) * 100
            
            return {
                "inventory_turnover": round(inventory_turnover, 2),
                "stockout_rate": round(stockout_rate, 2),
                "inventory_value": round(inventory_value, 2),
                "sales_value_30d": round(sales_value, 2)
            }
        
if __name__ == "__main__":
    dashboard = RetailDashboard()
    data = dashboard.generate_dashboard_data()
    print(data)