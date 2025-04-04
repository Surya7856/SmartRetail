import numpy as np
import datetime
import time
from database.db_manager import db_connection

class WarehouseAgent:
    def __init__(self):
        self.replenishment_model = self.train_rl_model()
        
    def train_rl_model(self):
        """Train a simplified RL model for inventory optimization"""
        
        def model(current_stock, product_id, store_id):
            
            with db_connection() as conn:
                c = conn.cursor()
                
                c.execute('''SELECT AVG(units_sold) as avg_sales
                             FROM sales_history 
                             WHERE product_id=? AND store_id=?
                             AND date >= ?''', 
                         (product_id, store_id, 
                          (datetime.date.today() - datetime.timedelta(days=30)).isoformat()))
                avg_result = c.fetchone()
                avg_daily_sales = avg_result['avg_sales'] if avg_result and avg_result['avg_sales'] else 1
                
                
                c.execute('''SELECT MIN(lead_time) as lead_time
                             FROM suppliers
                             WHERE product_id=?''', (product_id,))
                lead_result = c.fetchone()
                lead_time = lead_result['lead_time'] if lead_result else 7
            
            
            safety_factor = 1.5
            safety_stock = avg_daily_sales * lead_time * safety_factor
            
            
            min_threshold = safety_stock
            max_threshold = safety_stock * 2
            
            if current_stock < min_threshold:
                return max_threshold - current_stock
            return 0
            
        return model
        
    def calculate_replenishment(self, product_id, store_id):
        """Calculate optimal replenishment quantity"""
        with db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT stock_level FROM inventory 
                         WHERE product_id=? AND store_id=?''', 
                      (product_id, store_id))
            result = c.fetchone()
            current_stock = result['stock_level'] if result else 0
            
        return self.replenishment_model(current_stock, product_id, store_id)
    
    def handle_restock_requests(self):
        """Process pending restock requests with higher priority"""
        try:
            
            request_ids = []
            with db_connection() as conn:
                c = conn.cursor()
                
                c.execute('''SELECT id FROM restock_requests 
                             WHERE status='pending' 
                             ORDER BY id ASC''')
                request_ids = [row['id'] for row in c.fetchall()]
                
            requests_processed = 0
                
            
            for req_id in request_ids:
                try:
                    with db_connection() as conn:
                        c = conn.cursor()
                        c.execute('''SELECT id, store_id, product_id, quantity, supplier_id 
                                    FROM restock_requests 
                                    WHERE id=? AND status='pending' ''', (req_id,))
                        request = c.fetchone()
                        
                        if not request:
                            continue  
                            
                        store_id = request['store_id']
                        product_id = request['product_id']
                        quantity = request['quantity']
                        supplier_id = request['supplier_id']
                        
                        
                        
                        
                        
                        c.execute('''UPDATE inventory 
                                    SET stock_level = stock_level + ?,
                                        last_updated = CURRENT_TIMESTAMP
                                    WHERE store_id=? AND product_id=?''',
                                (quantity, store_id, product_id))
                        
                        if c.rowcount == 0:
                            
                            c.execute('''INSERT INTO inventory 
                                        (product_id, store_id, stock_level, last_updated)
                                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
                                    (product_id, store_id, quantity))
                        
                        
                        c.execute('''UPDATE restock_requests 
                                    SET status='completed' 
                                    WHERE id=?''', (req_id,))
                        
                        conn.commit()
                        requests_processed += 1
                        print(f"Processed restock of {quantity} units for product {product_id} at store {store_id}")
                        
                except Exception as e:
                    print(f"Error processing restock request {req_id}: {e}")
                    
                    
            return requests_processed
        except Exception as e:
            print(f"Error in handle_restock_requests: {e}")
            return 0