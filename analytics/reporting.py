import datetime
import pandas as pd
import numpy as np
from database.db_manager import db_connection
from typing import Dict, List, Any, Optional

class RetailAnalytics:
    """Analytics and reporting system for the retail optimization framework."""
    
    def __init__(self):
        pass
        
    def generate_weekly_report(self, start_date=None, end_date=None):
        """Generate a comprehensive weekly performance report"""
        
        if not end_date:
            end_date = datetime.date.today()
        if not start_date:
            start_date = end_date - datetime.timedelta(days=7)
            
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
        
        
        sales_data = self._get_sales_data(start_date_str, end_date_str)
        inventory_data = self._get_inventory_data()
        stockout_data = self._get_stockout_incidents(start_date_str, end_date_str)
        restock_data = self._get_restock_data(start_date_str, end_date_str)
        
        
        kpis = self._calculate_kpis(sales_data, inventory_data, stockout_data, restock_data)
        
        
        report = {
            "report_period": f"{start_date_str} to {end_date_str}",
            "generation_date": datetime.date.today().isoformat(),
            "kpis": kpis,
            "sales_summary": self._summarize_sales(sales_data),
            "inventory_summary": self._summarize_inventory(inventory_data),
            "stockout_summary": self._summarize_stockouts(stockout_data),
            "restock_summary": self._summarize_restocks(restock_data),
            "recommendations": self._generate_recommendations(kpis, sales_data, inventory_data)
        }
        
        return report
    
    def _get_sales_data(self, start_date, end_date):
        """Retrieve sales data for the specified period"""
        with db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT product_id, store_id, date, units_sold FROM sales_history
                         WHERE date >= ? AND date <= ?''',
                     (start_date, end_date))
            return c.fetchall()
    
    def _get_inventory_data(self):
        """Get current inventory levels"""
        with db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT product_id, store_id, stock_level, last_updated 
                         FROM inventory''')
            return c.fetchall()
    
    def _get_stockout_incidents(self, start_date, end_date):
        """Get stockout incidents (where stock_level was 0 or near 0)"""
        with db_connection() as conn:
            c = conn.cursor()
            
            c.execute('''SELECT product_id, store_id, last_updated
                         FROM inventory
                         WHERE stock_level <= 5''')
            return c.fetchall()
    
    def _get_restock_data(self, start_date, end_date):
        """Get restock request data"""
        with db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT id, store_id, product_id, quantity, supplier_id, status, request_date
                         FROM restock_requests
                         WHERE request_date >= ? AND request_date <= ?''',
                     (start_date, end_date))
            return c.fetchall()
    
    def _calculate_kpis(self, sales_data, inventory_data, stockout_data, restock_data):
        """Calculate key performance indicators"""
        
        sales_df = pd.DataFrame(sales_data, columns=['product_id', 'store_id', 'date', 'units_sold'])
        inventory_df = pd.DataFrame(inventory_data, columns=['product_id', 'store_id', 'stock_level', 'last_updated'])
        
        
        total_units_sold = sales_df['units_sold'].sum() if not sales_df.empty else 0
        
        
        avg_inventory = inventory_df['stock_level'].mean() if not inventory_df.empty else 0
        
        
        stockout_count = len(stockout_data)
        
        
        inventory_turnover = total_units_sold / avg_inventory if avg_inventory > 0 else 0
        
        
        
        
        total_product_store_combinations = len(inventory_df[['product_id', 'store_id']].drop_duplicates())
        stockout_percentage = (stockout_count / total_product_store_combinations) if total_product_store_combinations > 0 else 0
        fill_rate = (1 - stockout_percentage) * 100
        
        
        restock_df = pd.DataFrame(restock_data, columns=['id', 'store_id', 'product_id', 'quantity', 'supplier_id', 'status', 'request_date'])
        completed_restocks = len(restock_df[restock_df['status'] == 'completed']) if not restock_df.empty else 0
        total_restocks = len(restock_df) if not restock_df.empty else 0
        restock_completion_rate = (completed_restocks / total_restocks * 100) if total_restocks > 0 else 100
        
        return {
            "total_units_sold": int(total_units_sold),
            "average_inventory_level": round(float(avg_inventory), 2),
            "stockout_count": stockout_count,
            "fill_rate_percentage": round(fill_rate, 2),
            "inventory_turnover": round(inventory_turnover, 2),
            "restock_completion_rate": round(restock_completion_rate, 2)
        }
    
    def _summarize_sales(self, sales_data):
        """Create a summary of sales data"""
        if not sales_data:
            return {"message": "No sales data available for this period"}
            
        sales_df = pd.DataFrame(sales_data, columns=['product_id', 'store_id', 'date', 'units_sold'])
        
        
        product_sales = sales_df.groupby('product_id')['units_sold'].sum().to_dict()
        
        
        store_sales = sales_df.groupby('store_id')['units_sold'].sum().to_dict()
        
        
        sales_df['date'] = pd.to_datetime(sales_df['date'])
        daily_sales = sales_df.groupby(sales_df['date'].dt.date)['units_sold'].sum()
        
        
        top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_sales": int(sales_df['units_sold'].sum()),
            "sales_by_product": {str(k): int(v) for k, v in product_sales.items()},
            "sales_by_store": {str(k): int(v) for k, v in store_sales.items()},
            "top_selling_products": [{"product_id": p[0], "units_sold": int(p[1])} for p in top_products],
            "daily_sales_trend": [{
                "date": str(date),
                "units_sold": int(units)
            } for date, units in daily_sales.items()]
        }
    
    def _summarize_inventory(self, inventory_data):
        """Create a summary of inventory data"""
        if not inventory_data:
            return {"message": "No inventory data available"}
            
        inventory_df = pd.DataFrame(inventory_data, columns=['product_id', 'store_id', 'stock_level', 'last_updated'])
        
        
        total_inventory = inventory_df['stock_level'].sum()
        
        
        store_inventory = inventory_df.groupby('store_id')['stock_level'].sum().to_dict()
        
        
        low_stock = inventory_df[inventory_df['stock_level'] < 20]
        low_stock_items = [
            {"product_id": int(row['product_id']), 
             "store_id": int(row['store_id']), 
             "stock_level": int(row['stock_level'])}
            for _, row in low_stock.iterrows()
        ]
        
        
        overstock = inventory_df[inventory_df['stock_level'] > 200]
        overstocked_items = [
            {"product_id": int(row['product_id']), 
             "store_id": int(row['store_id']), 
             "stock_level": int(row['stock_level'])}
            for _, row in overstock.iterrows()
        ]
        
        return {
            "total_inventory": int(total_inventory),
            "inventory_by_store": {str(k): int(v) for k, v in store_inventory.items()},
            "low_stock_items": low_stock_items,
            "overstocked_items": overstocked_items
        }
    
    def _summarize_stockouts(self, stockout_data):
        """Summarize stockout incidents"""
        if not stockout_data:
            return {"message": "No stockout incidents recorded"}
            
        stockout_df = pd.DataFrame(stockout_data, columns=['product_id', 'store_id', 'last_updated'])
        
        
        product_stockouts = stockout_df.groupby('product_id').size().to_dict()
        
        
        store_stockouts = stockout_df.groupby('store_id').size().to_dict()
        
        return {
            "total_stockouts": len(stockout_data),
            "stockouts_by_product": {str(k): int(v) for k, v in product_stockouts.items()},
            "stockouts_by_store": {str(k): int(v) for k, v in store_stockouts.items()}
        }
    
    def _summarize_restocks(self, restock_data):
        """Summarize restock requests"""
        if not restock_data:
            return {"message": "No restock requests recorded for this period"}
            
        restock_df = pd.DataFrame(restock_data, columns=['id', 'store_id', 'product_id', 'quantity', 'supplier_id', 'status', 'request_date'])
        
        
        status_counts = restock_df['status'].value_counts().to_dict()
        
        
        avg_quantity = restock_df['quantity'].mean()
        
        return {
            "total_restocks": len(restock_data),
            "status_summary": {str(k): int(v) for k, v in status_counts.items()},
            "average_restock_quantity": round(float(avg_quantity), 2) if not np.isnan(avg_quantity) else 0
        }
    
    def _generate_recommendations(self, kpis, sales_data, inventory_data):
        """Generate business recommendations based on the analysis"""
        recommendations = []
        
        
        if kpis.get("fill_rate_percentage", 100) < 95:
            recommendations.append({
                "priority": "High",
                "issue": "Low Fill Rate",
                "recommendation": "Increase safety stock levels or improve demand forecasting to prevent stockouts."
            })
        
        
        if kpis.get("inventory_turnover", 0) < 2:
            recommendations.append({
                "priority": "Medium",
                "issue": "Low Inventory Turnover",
                "recommendation": "Reduce overall inventory levels for slow-moving products to improve capital efficiency."
            })
            
        
        if kpis.get("restock_completion_rate", 100) < 90:
            recommendations.append({
                "priority": "High",
                "issue": "Incomplete Restocks",
                "recommendation": "Investigate supplier performance and consider alternate suppliers for more reliable replenishment."
            })
            
        
        inventory_df = pd.DataFrame(inventory_data, columns=['product_id', 'store_id', 'stock_level', 'last_updated'])
        overstock_count = len(inventory_df[inventory_df['stock_level'] > 200])
        if overstock_count > 0:
            recommendations.append({
                "priority": "Medium",
                "issue": "Excessive Inventory",
                "recommendation": f"Consider promotions or price adjustments for {overstock_count} overstocked items to reduce holding costs."
            })
            
        
        if not recommendations:
            recommendations.append({
                "priority": "Low",
                "issue": "System Optimization",
                "recommendation": "Continue monitoring system performance and refine forecasting models."
            })
            
        return recommendations
    
if __name__ == "__main__":
    analytics = RetailAnalytics()
    report = analytics.generate_weekly_report()
    print(report)