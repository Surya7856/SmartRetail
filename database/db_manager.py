# database/db_manager.py
import sqlite3
from contextlib import contextmanager
import os
import threading
import time

# Lock to serialize database access
db_lock = threading.Lock()

DB_PATH = 'database/retail_db.db'

@contextmanager
def db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Add retry logic to handle potential locks
    retries = 5
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=30)  # Increased timeout
            conn.row_factory = sqlite3.Row
            
            # Enable Write-Ahead Logging for better concurrency
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA busy_timeout=30000')  # 30 second busy timeout
            
            try:
                yield conn
            finally:
                conn.close()
            break  # Success, exit retry loop
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < retries - 1:
                # Wait and retry with exponential backoff
                wait_time = 0.1 * (2 ** attempt)
                print(f"Database locked, retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
            else:
                # Last attempt failed, re-raise the exception
                raise

def initialize_db():
    """Initialize database if tables don't exist"""
    with db_connection() as conn:
        c = conn.cursor()
        
        # Create tables only if they don't exist
        # inventory table
        c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                     product_id INTEGER,
                     store_id INTEGER,
                     stock_level INTEGER,
                     last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     PRIMARY KEY (product_id, store_id))''')
        
        # sales_history table
        c.execute('''CREATE TABLE IF NOT EXISTS sales_history (
                     product_id INTEGER, 
                     store_id INTEGER,
                     date TEXT,
                     units_sold INTEGER)''')
                     
        # suppliers table
        c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
                     supplier_id INTEGER,
                     product_id INTEGER,
                     lead_time INTEGER,
                     cost REAL,
                     PRIMARY KEY (supplier_id, product_id))''')
                     
        # pricing table
        c.execute('''CREATE TABLE IF NOT EXISTS pricing (
                     product_id INTEGER PRIMARY KEY,
                     current_price REAL,
                     competitor_price REAL)''')
                     
        # customer_feedback table
        c.execute('''CREATE TABLE IF NOT EXISTS customer_feedback (
                     product_id INTEGER,
                     review_text TEXT,
                     sentiment_score REAL)''')
                     
        # restock_requests table (for our system)
        c.execute('''CREATE TABLE IF NOT EXISTS restock_requests (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     store_id INTEGER,
                     product_id INTEGER,
                     quantity INTEGER,
                     supplier_id INTEGER,
                     status TEXT,
                     request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.commit()