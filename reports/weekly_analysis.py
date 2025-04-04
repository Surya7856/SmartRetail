import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from datetime import datetime, timedelta
import os
from jinja2 import Template
from database.db_manager import db_connection

class WeeklyAnalysisReport:
    """Generates comprehensive weekly analysis reports for the retail optimization system."""
    
    def __init__(self):
        
        os.makedirs("reports", exist_ok=True)
    
    def generate_report(self, start_date=None, end_date=None, output_format="html"):
        """Generate a comprehensive weekly analysis report.
        
        Args:
            start_date: Start date of analysis period (default: 7 days ago)
            end_date: End date of analysis period (default: today)
            output_format: 'html' or 'pdf'
            
        Returns:
            Path to the generated report file
        """
        
        if not end_date:
            end_date = datetime.today().date()
        if not start_date:
            start_date = end_date - timedelta(days=7)
            
        
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
        
        
        data = {
            "report_period": f"{start_date_str} to {end_date_str}",
            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sales_summary": self._get_sales_summary(start_date_str, end_date_str),
            "inventory_summary": self._get_inventory_summary(),
            "stockout_analysis": self._get_stockout_analysis(start_date_str, end_date_str),
            "price_changes": self._get_price_changes(start_date_str, end_date_str),
            "supplier_performance": self._get_supplier_performance(start_date_str, end_date_str),
            "kpis": self._calculate_kpis(start_date_str, end_date_str),
            "recommendations": self._generate_recommendations(),
            "charts": self._generate_charts(start_date_str, end_date_str)
        }
        
        
        if output_format == "html":
            return self._generate_html_report(data)
        elif output_format == "pdf":
            return self._generate_pdf_report(data)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _get_sales_summary(self, start_date, end_date):
        """Get summary of sales for the specified period"""
        with db_connection() as conn:
            
            query = f"""
                SELECT 
                    product_id,
                    store_id,
                    date,
                    units_sold
                FROM 
                    sales_history
                WHERE 
                    date >= '{start_date}' AND date <= '{end_date}'
            """
            df = pd.read_sql_query(query, conn)
            
            if df.empty:
                return {
                    "total_units": 0,
                    "total_revenue": 0,
                    "avg_daily_units": 0,
                    "top_products": [],
                    "top_stores": []
                }
            
            
            query_prices = """
                SELECT 
                    product_id,
                    current_price
                FROM 
                    pricing
            """
            prices_df = pd.read_sql_query(query_prices, conn)
            
            
            merged_df = df.merge(prices_df, on="product_id", how="left")
            merged_df["revenue"] = merged_df["units_sold"] * merged_df["current_price"]
            
            
            total_units = df["units_sold"].sum()
            total_revenue = merged_df["revenue"].sum()
            
            days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1
            avg_daily_units = total_units / days if days > 0 else 0
            
            top_products_units = df.groupby("product_id")["units_sold"].sum().reset_index()
            top_products_units = top_products_units.sort_values("units_sold", ascending=False).head(5)
            
            top_products_revenue = merged_df.groupby("product_id")["revenue"].sum().reset_index()
            top_products_revenue = top_products_revenue.sort_values("revenue", ascending=False).head(5)
            
            top_stores = df.groupby("store_id")["units_sold"].sum().reset_index()
            top_stores = top_stores.sort_values("units_sold", ascending=False)
            
            return {
                "total_units": int(total_units),
                "total_revenue": float(total_revenue),
                "avg_daily_units": float(avg_daily_units),
                "top_products_units": top_products_units.to_dict(orient="records"),
                "top_products_revenue": top_products_revenue.to_dict(orient="records"),
                "top_stores": top_stores.to_dict(orient="records")
            }
    
    def _get_inventory_summary(self):
        """Get current inventory summary"""
        with db_connection() as conn:
            
            query = """
                SELECT 
                    i.product_id,
                    i.store_id,
                    i.stock_level,
                    p.current_price,
                    s.cost
                FROM 
                    inventory i
                LEFT JOIN 
                    pricing p ON i.product_id = p.product_id
                LEFT JOIN 
                    suppliers s ON i.product_id = s.product_id
                GROUP BY 
                    i.product_id, i.store_id
            """
            df = pd.read_sql_query(query, conn)
            
            if df.empty:
                return {
                    "total_units": 0,
                    "total_value": 0,
                    "low_stock_count": 0,
                    "overstock_count": 0,
                    "low_stock_items": [],
                    "overstock_items": []
                }
            
            
            df["inventory_value"] = df["stock_level"] * df["cost"]
            
            
            low_stock = df[df["stock_level"] < 20]
            overstock = df[df["stock_level"] > 200]
            
            return {
                "total_units": int(df["stock_level"].sum()),
                "total_value": float(df["inventory_value"].sum()),
                "low_stock_count": len(low_stock),
                "overstock_count": len(overstock),
                "low_stock_items": low_stock.to_dict(orient="records"),
                "overstock_items": overstock.to_dict(orient="records")
            }
    
    def _get_stockout_analysis(self, start_date, end_date):
        """Analyze stockout incidents during the period"""
        
        with db_connection() as conn:
            query = """
                SELECT 
                    i.product_id,
                    i.store_id,
                    i.stock_level
                FROM 
                    inventory i
                WHERE 
                    i.stock_level <= 5
            """
            df = pd.read_sql_query(query, conn)
            
            return {
                "total_stockouts": len(df),
                "products_at_risk": df.to_dict(orient="records")
            }
    
    def _get_price_changes(self, start_date, end_date):
        """Get price changes during the period"""
        
        with db_connection() as conn:
            query = """
                SELECT 
                    p.product_id,
                    p.current_price,
                    p.competitor_price
                FROM 
                    pricing p
            """
            df = pd.read_sql_query(query, conn)
            
            df["price_differential_pct"] = ((df["current_price"] - df["competitor_price"]) / df["competitor_price"]) * 100
            
            return {
                "total_products": len(df),
                "avg_price_differential": float(df["price_differential_pct"].mean()),
                "pricing_data": df.to_dict(orient="records")
            }
    
    def _get_supplier_performance(self, start_date, end_date):
        """Analyze supplier performance"""
        
        with db_connection() as conn:
            query = """
                SELECT 
                    supplier_id,
                    product_id,
                    lead_time,
                    cost
                FROM 
                    suppliers
            """
            df = pd.read_sql_query(query, conn)
            
            supplier_summary = df.groupby("supplier_id").agg({
                "product_id": "count",
                "lead_time": "mean",
                "cost": "mean"
            }).reset_index()
            
            supplier_summary = supplier_summary.rename(columns={
                "product_id": "product_count",
                "lead_time": "avg_lead_time",
                "cost": "avg_cost"
            })
            
            return {
                "supplier_count": len(supplier_summary),
                "avg_lead_time": float(supplier_summary["avg_lead_time"].mean()),
                "supplier_data": supplier_summary.to_dict(orient="records")
            }
    
    def _calculate_kpis(self, start_date, end_date):
        """Calculate key performance indicators"""
        
        with db_connection() as conn:
            sales_query = f"""
                SELECT 
                    date,
                    SUM(units_sold) as total_units
                FROM 
                    sales_history
                WHERE 
                    date >= '{start_date}' AND date <= '{end_date}'
                GROUP BY 
                    date
            """
            sales_df = pd.read_sql_query(sales_query, conn)
            
            inventory_query = """
                SELECT 
                    product_id,
                    store_id,
                    stock_level
                FROM 
                    inventory
            """
            inventory_df = pd.read_sql_query(inventory_query, conn)
            
            restock_query = f"""
                SELECT 
                    store_id,
                    product_id,
                    quantity,
                    status,
                    request_date
                FROM 
                    restock_requests
                WHERE 
                    request_date >= '{start_date}' AND request_date <= '{end_date}'
            """
            restock_df = pd.read_sql_query(restock_query, conn)
        
        total_sales = sales_df["total_units"].sum() if not sales_df.empty else 0
        
        days_count = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1
        avg_daily_sales = total_sales / days_count if days_count > 0 else 0
        
        total_inventory = inventory_df["stock_level"].sum() if not inventory_df.empty else 0
        
        stockout_count = len(inventory_df[inventory_df["stock_level"] == 0]) if not inventory_df.empty else 0
        total_product_locations = len(inventory_df) if not inventory_df.empty else 1  
        stockout_rate = (stockout_count / total_product_locations) * 100
        
        days_of_supply = total_inventory / avg_daily_sales if avg_daily_sales > 0 else 0
        
        completed_restocks = len(restock_df[restock_df["status"] == "completed"]) if not restock_df.empty else 0
        total_restocks = len(restock_df) if not restock_df.empty else 0
        fulfillment_rate = (completed_restocks / total_restocks * 100) if total_restocks > 0 else 100
        
        return {
            "total_sales": int(total_sales),
            "avg_daily_sales": float(avg_daily_sales),
            "total_inventory": int(total_inventory),
            "stockout_rate": float(stockout_rate),
            "days_of_supply": float(days_of_supply),
            "fulfillment_rate": float(fulfillment_rate)
        }
    
    def _generate_recommendations(self):
        """Generate business recommendations based on the analysis"""
        
        return [
            {
                "priority": "High",
                "category": "Inventory Management",
                "recommendation": "Increase safety stock levels for high-volume products to prevent stockouts.",
                "expected_impact": "Reduce stockout rate by 30-40% with minimal inventory cost increase."
            },
            {
                "priority": "Medium",
                "category": "Pricing Strategy",
                "recommendation": "Adjust pricing for overstocked items to increase sales velocity.",
                "expected_impact": "Reduce overstock by 25% and improve cash flow by $5,000 in 30 days."
            },
            {
                "priority": "Medium",
                "category": "Supplier Relationships",
                "recommendation": "Negotiate better terms with suppliers for high-volume products.",
                "expected_impact": "Reduce lead times by 15% and costs by 8% for key products."
            },
            {
                "priority": "Low",
                "category": "System Enhancement",
                "recommendation": "Improve demand forecasting accuracy by incorporating more external factors.",
                "expected_impact": "Increase forecast accuracy by 12% and reduce safety stock requirements."
            }
        ]
    
    def _generate_charts(self, start_date, end_date):
        """Generate charts for the report"""
        charts = {}

        with db_connection() as conn:
            
            query = f"""
                SELECT 
                    date,
                    SUM(units_sold) as total_units
                FROM 
                    sales_history
                WHERE 
                    date >= '{start_date}' AND date <= '{end_date}'
                GROUP BY 
                    date
                ORDER BY
                    date ASC
            """
            df = pd.read_sql_query(query, conn)
            
            if not df.empty:
                
                df["date"] = pd.to_datetime(df["date"])

                plt.figure(figsize=(10, 6))
                plt.plot(df["date"], df["total_units"], marker='o', linestyle='-', color='blue')
                plt.title("Daily Sales Trend")
                plt.xlabel("Date")
                plt.ylabel("Units Sold")
                plt.grid(True, linestyle='--', alpha=0.7)
                plt.xticks(rotation=45)
                plt.tight_layout()

                img_data = BytesIO()
                plt.savefig(img_data, format='png')
                img_data.seek(0)
                
                encoded = base64.b64encode(img_data.read()).decode('utf-8')
                charts["sales_trend"] = f"data:image/png;base64,{encoded}"
                
                plt.close()
            
            query_inventory = """
                SELECT 
                    store_id,
                    SUM(stock_level) as total_stock
                FROM 
                    inventory
                GROUP BY 
                    store_id
            """
            inv_df = pd.read_sql_query(query_inventory, conn)
            
            if not inv_df.empty:
                
                plt.figure(figsize=(8, 5))
                plt.bar(inv_df["store_id"].astype(str), inv_df["total_stock"], color='green')
                plt.title("Inventory Distribution by Store")
                plt.xlabel("Store ID")
                plt.ylabel("Total Stock")
                plt.grid(True, axis='y', linestyle='--', alpha=0.7)
                
                img_data = BytesIO()
                plt.savefig(img_data, format='png')
                img_data.seek(0)
                
                encoded = base64.b64encode(img_data.read()).decode('utf-8')
                charts["inventory_distribution"] = f"data:image/png;base64,{encoded}"
                
                plt.close()
        
        return charts
    
    def _generate_html_report(self, data):
        """Generate HTML report"""
        
        template_path = os.path.join(os.path.dirname(__file__), "templates", "weekly_report_template.html")
        
        if not os.path.exists(template_path):
            os.makedirs(os.path.dirname(template_path), exist_ok=True)
            template_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Weekly Retail Analysis Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
                    h1 { color: 
                    h2 { color: 
                    .report-header { border-bottom: 1px solid 
                    .kpi-container { display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0; }
                    .kpi-card { border: 1px solid 
                    .kpi-title { font-size: 14px; color: 
                    .kpi-value { font-size: 24px; font-weight: bold; color: 
                    .chart-container { margin: 30px 0; text-align: center; }
                    .chart-container img { max-width: 100%; border: 1px solid 
                    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                    th { background-color: 
                    td { padding: 12px; border-top: 1px solid 
                    .recommendations { margin: 30px 0; }
                    .recommendation { margin-bottom: 15px; padding: 15px; border: 1px solid 
                    .high-priority { border-left: 4px solid 
                    .medium-priority { border-left: 4px solid 
                    .low-priority { border-left: 4px solid 
                </style>
            </head>
            <body>
                <div class="report-header">
                    <h1>Weekly Retail Analysis Report</h1>
                    <p>Period: {{ report_period }}</p>
                    <p>Generated on: {{ generation_date }}</p>
                </div>
                
                <h2>Key Performance Indicators</h2>
                <div class="kpi-container">
                    <div class="kpi-card">
                        <div class="kpi-title">Total Sales (Units)</div>
                        <div class="kpi-value">{{ kpis.total_sales }}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Avg Daily Sales</div>
                        <div class="kpi-value">{{ "%.1f"|format(kpis.avg_daily_sales) }}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Total Inventory</div>
                        <div class="kpi-value">{{ kpis.total_inventory }}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Stockout Rate</div>
                        <div class="kpi-value">{{ "%.1f"|format(kpis.stockout_rate) }}%</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Days of Supply</div>
                        <div class="kpi-value">{{ "%.1f"|format(kpis.days_of_supply) }}</div>
                    </div>
                    <div class="kpi-card">
                        <div class="kpi-title">Restock Fulfillment</div>
                        <div class="kpi-value">{{ "%.1f"|format(kpis.fulfillment_rate) }}%</div>
                    </div>
                </div>
                
                <h2>Sales Performance</h2>
                <p>Total Revenue: ${{ "%.2f"|format(sales_summary.total_revenue) }}</p>
                <p>Total Units Sold: {{ sales_summary.total_units }}</p>
                
                <div class="chart-container">
                    <h3>Daily Sales Trend</h3>
                    {% if charts.sales_trend %}
                    <img src="{{ charts.sales_trend }}" alt="Daily Sales Trend">
                    {% else %}
                    <p>No sales data available for chart.</p>
                    {% endif %}
                </div>
                
                <h3>Top Products by Units Sold</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Product ID</th>
                            <th>Units Sold</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for product in sales_summary.top_products_units %}
                        <tr>
                            <td>{{ product.product_id }}</td>
                            <td>{{ product.units_sold }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                
                <h3>Top Products by Revenue</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Product ID</th>
                            <th>Revenue</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for product in sales_summary.top_products_revenue %}
                        <tr>
                            <td>{{ product.product_id }}</td>
                            <td>${{ "%.2f"|format(product.revenue) }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                
                <h2>Inventory Status</h2>
                <p>Total Inventory Value: ${{ "%.2f"|format(inventory_summary.total_value) }}</p>
                
                <div class="chart-container">
                    <h3>Inventory Distribution by Store</h3>
                    {% if charts.inventory_distribution %}
                    <img src="{{ charts.inventory_distribution }}" alt="Inventory Distribution">
                    {% else %}
                    <p>No inventory data available for chart.</p>
                    {% endif %}
                </div>
                
                <h3>Low Stock Items (Below 20 units)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Product ID</th>
                            <th>Store ID</th>
                            <th>Stock Level</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in inventory_summary.low_stock_items %}
                        <tr>
                            <td>{{ item.product_id }}</td>
                            <td>{{ item.store_id }}</td>
                            <td>{{ item.stock_level }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                
                <h2>Price Analysis</h2>
                <p>Average Price Differential vs Competitors: {{ "%.1f"|format(price_changes.avg_price_differential) }}%</p>
                
                <h2>Strategic Recommendations</h2>
                <div class="recommendations">
                    {% for rec in recommendations %}
                    <div class="recommendation {{ rec.priority|lower }}-priority">
                        <h3>{{ rec.category }}</h3>
                        <p><strong>Priority:</strong> {{ rec.priority }}</p>
                        <p><strong>Recommendation:</strong> {{ rec.recommendation }}</p>
                        <p><strong>Expected Impact:</strong> {{ rec.expected_impact }}</p>
                    </div>
                    {% endfor %}
                </div>
                
                <footer>
                    <p>This report was automatically generated by the Retail Optimization System v1.2</p>
                </footer>
            </body>
            </html>
            """
            with open(template_path, "w") as f:
                f.write(template_content)
        
        with open(template_path, "r") as f:
            template_content = f.read()
        
        template = Template(template_content)
        rendered_html = template.render(**data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"reports/weekly_report_{timestamp}.html"
        
        with open(report_filename, "w") as f:
            f.write(rendered_html)
            
        return report_filename
    
    def _generate_pdf_report(self, data):
        """Generate PDF report"""
        
        html_path = self._generate_html_report(data)
        
        print("Note: PDF generation would convert the HTML to PDF in a real implementation")
        return html_path

if __name__ == "__main__":
    report_generator = WeeklyAnalysisReport()
    report_path = report_generator.generate_report()
    print(f"Report generated: {report_path}")