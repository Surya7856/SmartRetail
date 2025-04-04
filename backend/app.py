from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import datetime
import json
from pathlib import Path
from contextlib import asynccontextmanager
from database.db_manager import db_connection, initialize_db
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_db()
    yield

app = FastAPI(lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class KpiData(BaseModel):
    revenue: float
    revenueChange: float
    conversionRate: float
    conversionRateChange: float
    orders: int
    ordersChange: float
    inventoryCount: int
    inventoryCountChange: float

class SalesData(BaseModel):
    date: str
    revenue: float
    orders: int

class SalesTrends(BaseModel):
    dailySales: List[SalesData]

class StockHealth(BaseModel):
    low_stock: int
    healthy_stock: int
    overstock: int

class StoreInventory(BaseModel):
    store_id: int
    total_stock: int

class InventorySummary(BaseModel):
    stockHealth: StockHealth
    storeInventory: List[StoreInventory]

class ProductSales(BaseModel):
    name: str
    sales: int

class ProductPerformance(BaseModel):
    topProducts: List[ProductSales]

class Alert(BaseModel):
    type: str
    title: str
    message: str

class DashboardData(BaseModel):
    kpis: KpiData
    salesTrends: SalesTrends
    inventorySummary: InventorySummary
    productPerformance: ProductPerformance
    alerts: List[Alert]

# Routes
@app.get("/")
async def root():
    return {"message": "Retail Dashboard API is running"}

@app.get("/api/dashboard/data", response_model=DashboardData)
async def get_dashboard_data():
    """Get all dashboard data"""
    try:
        logger.info("Fetching dashboard data...")
        logger.info("Fetching KPIs...")
        logger.info("Fetching sales trends...")
        logger.info("Fetching inventory summary...")
        kpis = await get_kpis()
        sales_trends = await get_sales_trends()
        inventory_summary = await get_inventory_summary()
        product_performance = await get_product_performance()
        alerts = await get_alerts()
        
        return {
            "kpis": kpis,
            "salesTrends": sales_trends,
            "inventorySummary": inventory_summary,
            "productPerformance": product_performance,
            "alerts": alerts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard data: {str(e)}")

@app.get("/api/dashboard/kpis", response_model=KpiData)
async def get_kpis():
    """Get KPI data from database"""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # Get total inventory count
            cursor.execute("SELECT SUM(stock_level) FROM inventory")
            inventory_count = cursor.fetchone()[0] or 0
            
            # Get previous inventory count (approximate by subtracting recent sales)
            cursor.execute("""
                SELECT SUM(units_sold) 
                FROM sales_history 
                WHERE date >= date('now', '-7 days')
            """)
            recent_sales = cursor.fetchone()[0] or 0
            print(recent_sales)
            prev_inventory = inventory_count + recent_sales
            inventory_change = (inventory_count - prev_inventory) / prev_inventory * 100 if prev_inventory else 0
            
            # Get current orders (last 30 days)
            cursor.execute("""
                SELECT COUNT(DISTINCT product_id || '-' || store_id || '-' || date) 
                FROM sales_history 
                WHERE date >= date('now', '-30 days')
            """)
            orders = cursor.fetchone()[0] or 0
            
            # Get previous period orders
            cursor.execute("""
                SELECT COUNT(DISTINCT product_id || '-' || store_id || '-' || date) 
                FROM sales_history 
                WHERE date BETWEEN date('now', '-60 days') AND date('now', '-31 days')
            """)
            prev_orders = cursor.fetchone()[0] or 1  # Avoid division by zero
            orders_change = (orders - prev_orders) / prev_orders * 100
            
            # Calculate revenue
            cursor.execute("""
                SELECT SUM(s.units_sold * p.current_price) 
                FROM sales_history s
                JOIN pricing p ON s.product_id = p.product_id
                WHERE s.date >= date('now', '-30 days')
            """)
            revenue = cursor.fetchone()[0] or 0
            
            # Calculate previous period revenue
            cursor.execute("""
                SELECT SUM(s.units_sold * p.current_price) 
                FROM sales_history s
                JOIN pricing p ON s.product_id = p.product_id
                WHERE s.date BETWEEN date('now', '-60 days') AND date('now', '-31 days')
            """)
            prev_revenue = cursor.fetchone()[0] or 1  # Avoid division by zero
            revenue_change = (revenue - prev_revenue) / prev_revenue * 100
            
            # Calculate conversion rate (assuming 10x as many views as sales - placeholder for real data)
            cursor.execute("""
                SELECT SUM(units_sold) 
                FROM sales_history 
                WHERE date >= date('now', '-30 days')
            """)
            total_sales = cursor.fetchone()[0] or 0
            total_views = total_sales * 10  # Placeholder for real view data
            conversion_rate = (total_sales / total_views * 100) if total_views else 0
            
            # Previous conversion
            cursor.execute("""
                SELECT SUM(units_sold) 
                FROM sales_history 
                WHERE date BETWEEN date('now', '-60 days') AND date('now', '-31 days')
            """)
            prev_sales = cursor.fetchone()[0] or 0
            prev_views = prev_sales * 10  # Placeholder for real view data
            prev_conversion_rate = (prev_sales / prev_views * 100) if prev_views else 0
            conversion_change = conversion_rate - prev_conversion_rate
            
            return {
                "revenue": round(revenue, 2),
                "revenueChange": round(revenue_change, 1),
                "conversionRate": round(conversion_rate, 1),
                "conversionRateChange": round(conversion_change, 1),
                "orders": orders,
                "ordersChange": round(orders_change, 1),
                "inventoryCount": inventory_count,
                "inventoryCountChange": round(inventory_change, 1)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving KPI data: {str(e)}")

@app.get("/api/dashboard/sales", response_model=SalesTrends)
async def get_sales_trends():
    """Get sales trends data from database"""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # Get daily sales for the last 30 days
            cursor.execute("""
                SELECT 
                    date, 
                    SUM(s.units_sold * p.current_price) as revenue,
                    COUNT(DISTINCT s.product_id || '-' || s.store_id || '-' || s.date) as orders
                FROM sales_history s
                JOIN pricing p ON s.product_id = p.product_id
                WHERE date >= date('now', '-30 days')
                GROUP BY date
                ORDER BY date
            """)
            
            daily_sales = []
            for row in cursor.fetchall():
                daily_sales.append({
                    "date": row[0],
                    "revenue": float(row[1]) if row[1] else 0,
                    "orders": int(row[2]) if row[2] else 0
                })
            
            # If there's no data, provide sample data for the last 30 days
            
            return {"dailySales": daily_sales}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sales data: {str(e)}")

@app.get("/api/dashboard/inventory", response_model=InventorySummary)
async def get_inventory_summary():
    """Get inventory summary from database"""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # Stock health calculation
            # This assumes you have some business logic for what's considered low/healthy/overstock
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN stock_level < 10 THEN 'low_stock'
                        WHEN stock_level BETWEEN 10 AND 50 THEN 'healthy_stock'
                        ELSE 'overstock'
                    END as stock_status,
                    COUNT(*) as count
                FROM inventory
                GROUP BY stock_status
            """)
            
            stock_health = {"low_stock": 0, "healthy_stock": 0, "overstock": 0}
            for row in cursor.fetchall():
                stock_health[row[0]] = row[1]
            
            # Store inventory totals
            cursor.execute("""
                SELECT 
                    store_id, 
                    SUM(stock_level) as total_stock
                FROM inventory
                GROUP BY store_id
            """)
            
            store_inventory = []
            for row in cursor.fetchall():
                store_inventory.append({
                    "store_id": row[0],
                    "total_stock": row[1]
                })
            
            return {
                "stockHealth": stock_health,
                "storeInventory": store_inventory
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving inventory data: {str(e)}")

@app.get("/api/dashboard/products", response_model=ProductPerformance)
async def get_product_performance():
    """Get product performance data from database"""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # Get top products by sales over the last 30 days
            cursor.execute("""
                SELECT 
                    p.product_id,
                    SUM(s.units_sold) as total_sales
                FROM sales_history s
                JOIN pricing p ON s.product_id = p.product_id
                WHERE s.date >= date('now', '-30 days')
                GROUP BY p.product_id
                ORDER BY total_sales DESC
                LIMIT 5
            """)
            
            # Since we don't have a products table with names,
            # we'll use product_id and add "Product" prefix
            top_products = []
            for row in cursor.fetchall():
                top_products.append({
                    "name": f"Product {row[0]}",
                    "sales": row[1]
                })
            
            # If no data, add sample data
            
            return {"topProducts": top_products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving product data: {str(e)}")

@app.get("/api/dashboard/alerts", response_model=List[Alert])
async def get_alerts():
    """Get alerts based on database conditions"""
    try:
        alerts = []
        
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # Low stock alerts
            cursor.execute("""
                SELECT product_id, store_id, stock_level
                FROM inventory
                WHERE stock_level < 5
                LIMIT 5
            """)
            
            for row in cursor.fetchall():
                alerts.append({
                    "type": "warning",
                    "title": "Low Stock Alert",
                    "message": f"Product {row[0]} is running low in Store #{row[1]} ({row[2]} units remaining)"
                })
            
            # Restock request status alerts
            cursor.execute("""
                SELECT product_id, store_id, status, request_date
                FROM restock_requests
                WHERE status = 'approved'
                ORDER BY request_date DESC
                LIMIT 3
            """)
            
            for row in cursor.fetchall():
                alerts.append({
                    "type": "success",
                    "title": "Restock Approved",
                    "message": f"Restock request for Product {row[0]} at Store #{row[1]} was approved on {row[3]}"
                })
            
            # Inventory discrepancy alerts (placeholder - in real app, would compare physical counts)
            cursor.execute("""
                SELECT store_id, COUNT(*) as discrepancy_count
                FROM inventory
                WHERE stock_level < 0
                GROUP BY store_id
                LIMIT 3
            """)
            
            for row in cursor.fetchall():
                alerts.append({
                    "type": "error",
                    "title": "Inventory Discrepancy",
                    "message": f"Negative stock detected for {row[1]} products in Store #{row[0]}"
                })
            
        # If no alerts, add a sample message
        if not alerts:
            alerts.append({
                "type": "success",
                "title": "All Systems Normal",
                "message": "No urgent alerts at this time."
            })
            
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")

# Advanced routes for data updates
class KpiUpdate(BaseModel):
    revenue: Optional[float] = None
    conversionRate: Optional[float] = None
    orders: Optional[int] = None
    inventoryCount: Optional[int] = None

@app.post("/api/dashboard/kpis/update")
async def update_kpis(update_data: KpiUpdate):
    """This endpoint is primarily for simulation purposes since 
    real KPIs are calculated from actual data"""
    return {"message": "KPI updates should be done by modifying the underlying data"}

class NewAlert(BaseModel):
    type: str  # success, warning, error
    title: str
    message: str

@app.post("/api/dashboard/alerts/add")
async def add_alert(alert: NewAlert):
    """Add a new alert - this would likely be stored in a separate alerts table 
    in a production system, but for simplicity we're just returning the alert"""
    return {"message": "Alert would be added to the system", "alert": alert}

class SalesDataUpdate(BaseModel):
    date: str
    store_id: int
    product_id: int
    units_sold: int
    price: float

@app.post("/api/dashboard/sales/add")
async def add_sales_data(sales_data: SalesDataUpdate):
    """Add new sales data point"""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # Add to sales_history
            cursor.execute("""
                INSERT INTO sales_history (product_id, store_id, date, units_sold)
                VALUES (?, ?, ?, ?)
            """, (
                sales_data.product_id,
                sales_data.store_id,
                sales_data.date,
                sales_data.units_sold
            ))
            
            # Update product price if needed
            cursor.execute("""
                INSERT OR REPLACE INTO pricing (product_id, current_price, competitor_price)
                VALUES (?, ?, (SELECT competitor_price FROM pricing WHERE product_id = ? LIMIT 1))
            """, (
                sales_data.product_id,
                sales_data.price,
                sales_data.product_id
            ))
            
            # Update inventory
            cursor.execute("""
                UPDATE inventory
                SET stock_level = stock_level - ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE product_id = ? AND store_id = ?
            """, (
                sales_data.units_sold,
                sales_data.product_id,
                sales_data.store_id
            ))
            
            conn.commit()
            
            return {"message": "Sales data added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding sales data: {str(e)}")

# Integration with the simulation system
@app.post("/api/simulation/update-dashboard")
async def update_dashboard_from_simulation(payload: Dict[str, Any]):
    """Update dashboard data from simulation results"""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # Update inventory if provided
            if "inventory" in payload:
                for item in payload["inventory"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO inventory (product_id, store_id, stock_level, last_updated)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        item["product_id"],
                        item["store_id"],
                        item["stock_level"]
                    ))
            
            # Add sales data if provided
            if "sales" in payload:
                for sale in payload["sales"]:
                    cursor.execute("""
                        INSERT INTO sales_history (product_id, store_id, date, units_sold)
                        VALUES (?, ?, ?, ?)
                    """, (
                        sale["product_id"],
                        sale["store_id"],
                        sale["date"],
                        sale["units_sold"]
                    ))
            
            # Update pricing if provided
            if "pricing" in payload:
                for price in payload["pricing"]:
                    cursor.execute("""
                        INSERT OR REPLACE INTO pricing (product_id, current_price, competitor_price)
                        VALUES (?, ?, ?)
                    """, (
                        price["product_id"],
                        price["current_price"],
                        price.get("competitor_price", None)
                    ))
            
            # Add restock requests if provided
            if "restock_requests" in payload:
                for request in payload["restock_requests"]:
                    cursor.execute("""
                        INSERT INTO restock_requests (
                            store_id, product_id, quantity, supplier_id, status, request_date
                        ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        request["store_id"],
                        request["product_id"],
                        request["quantity"],
                        request.get("supplier_id", None),
                        request.get("status", "pending")
                    ))
            
            conn.commit()
            
            return {"message": "Dashboard data updated from simulation successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating dashboard from simulation: {str(e)}")

# Data seeding utility endpoint
@app.post("/api/seed-database")
async def seed_database():
    """Seed the database with sample data for testing"""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # Clear existing data
            tables = ["inventory", "sales_history", "suppliers", "pricing", "customer_feedback", "restock_requests"]
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
            
            # Seed inventory data for two stores and 20 products
            for store_id in range(1, 3):
                for product_id in range(1, 21):
                    stock_level = 20 + (product_id % 5) * 10
                    if product_id < 5:  # Make some low stock
                        stock_level = 3
                    
                    cursor.execute("""
                        INSERT INTO inventory (product_id, store_id, stock_level)
                        VALUES (?, ?, ?)
                    """, (product_id, store_id, stock_level))
            
            # Seed pricing data
            for product_id in range(1, 21):
                price = 9.99 + (product_id % 10) * 5
                comp_price = price * (0.9 + (product_id % 5) * 0.05)
                
                cursor.execute("""
                    INSERT INTO pricing (product_id, current_price, competitor_price)
                    VALUES (?, ?, ?)
                """, (product_id, price, comp_price))
            
            # Seed supplier data
            for supplier_id in range(1, 4):
                for product_id in range(1, 21):
                    if product_id % 3 == supplier_id % 3:  # Distribute products among suppliers
                        lead_time = 2 + supplier_id
                        cost = (9.99 + (product_id % 10) * 5) * 0.6  # 60% of retail price
                        
                        cursor.execute("""
                            INSERT INTO suppliers (supplier_id, product_id, lead_time, cost)
                            VALUES (?, ?, ?, ?)
                        """, (supplier_id, product_id, lead_time, cost))
            
            # Seed sales history - 60 days of data
            today = datetime.date.today()
            for day in range(60):
                date_str = (today - datetime.timedelta(days=60-day)).strftime("%Y-%m-%d")
                
                # More sales on weekends
                is_weekend = (today - datetime.timedelta(days=60-day)).weekday() >= 5
                sale_factor = 1.5 if is_weekend else 1.0
                
                for store_id in range(1, 3):
                    for product_id in range(1, 21):
                        # Not all products sell every day
                        if day % product_id == 0 or product_id < 5:
                            units_sold = max(1, int((product_id % 5 + 1) * sale_factor))
                            
                            cursor.execute("""
                                INSERT INTO sales_history (product_id, store_id, date, units_sold)
                                VALUES (?, ?, ?, ?)
                            """, (product_id, store_id, date_str, units_sold))
            
            # Seed restock requests
            for i in range(5):
                product_id = i + 1
                store_id = (i % 2) + 1
                supplier_id = (i % 3) + 1
                status = ["pending", "approved", "shipped", "completed"][i % 4]
                
                cursor.execute("""
                    INSERT INTO restock_requests (
                        store_id, product_id, quantity, supplier_id, status, request_date
                    ) VALUES (?, ?, ?, ?, ?, date('now', ?))
                """, (
                    store_id, 
                    product_id, 
                    30, 
                    supplier_id, 
                    status, 
                    f"-{i*2} days"
                ))
            
            # Seed customer feedback
            sentiments = [
                (1, "Great product, very satisfied!", 0.9),
                (2, "It's okay, but a bit expensive", 0.3),
                (3, "Terrible quality, will not buy again", -0.8),
                (4, "Perfect for my needs", 0.8),
                (5, "Decent product for the price", 0.5)
            ]
            
            for product_id, review, sentiment in sentiments:
                cursor.execute("""
                    INSERT INTO customer_feedback (product_id, review_text, sentiment_score)
                    VALUES (?, ?, ?)
                """, (product_id, review, sentiment))
            
            conn.commit()
            
            return {"message": "Database seeded successfully with sample data"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding database: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)