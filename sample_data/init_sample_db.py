"""Database seeding script for live EXPLAIN and benchmark testing.

Creates sample tables: customers, orders, and products with mock records.
"""

import sys
import os
import random
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import DatabaseManager


def setup_sample_database(host="localhost", port=3306, user="root", password="", db_name="sql_optimizer_bench"):
    """Creates benchmark schema and seeds realistic data for live EXPLAIN analysis."""
    print(f"Connecting to MySQL ({host}:{port}) as {user}...")
    db_mgr = DatabaseManager(host=host, port=port, user=user, password=password, database=db_name)
    is_connected, msg, db_type = db_mgr.test_connection()

    if not is_connected or db_type != "mysql":
        print(f"Connection notice: {msg}")
        print("Note: If MySQL credentials require a password, specify it via parameters or .env.")
        return False

    conn = db_mgr._get_mysql_connection(create_db_if_missing=True)
    with conn.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
        cursor.execute(f"USE `{db_name}`;")

        # 1. Customers
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL,
                country VARCHAR(50) NOT NULL,
                created_at DATETIME NOT NULL,
                KEY idx_customers_country (country)
            );
        """)

        # 2. Orders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT NOT NULL,
                total_amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(20) NOT NULL,
                order_date DATETIME NOT NULL,
                KEY idx_orders_customer (customer_id),
                KEY idx_orders_status_date (status, order_date)
            );
        """)

        # 3. Products
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_name VARCHAR(150) NOT NULL,
                category VARCHAR(50) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                is_active TINYINT(1) DEFAULT 1,
                KEY idx_products_cat_price (category, price)
            );
        """)
        
        # 4. Flipkart Products
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flipkart_products (
                product_id INT AUTO_INCREMENT PRIMARY KEY,
                product_name VARCHAR(150) NOT NULL,
                category VARCHAR(100),
                price DECIMAL(10,2),
                is_available TINYINT(1) DEFAULT 1
            );
        """)

        # 5. Flipkart Orders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS flipkart_orders (
                order_id INT AUTO_INCREMENT PRIMARY KEY,
                payment_status VARCHAR(30) NOT NULL,
                order_date DATETIME NOT NULL,
                total_amount DECIMAL(10,2)
            );
        """)

        # 6. Cart Items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                cart_id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT,
                product_id INT,
                status VARCHAR(30) NOT NULL
            );
        """)

        # 7. Inactive Accounts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inactive_accounts (
                account_id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT
            );
        """)

        # 8. User Accounts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_accounts (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100),
                is_verified TINYINT(1) DEFAULT 1
            );
        """)

        # Check existing row counts
        cursor.execute("SELECT COUNT(*) AS cnt FROM customers;")
        cust_cnt = cursor.fetchone()["cnt"]

        if cust_cnt < 500:
            print("Seeding mock data for performance benchmarks...")
            first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley", "Casey", "Jamie"]
            last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Wilson"]
            countries = ["US", "CA", "UK", "DE", "FR", "IN", "JP", "AU"]

            # Seed customers
            cust_rows = []
            for i in range(1000):
                name = f"{random.choice(first_names)} {random.choice(last_names)} {i}"
                email = f"user{i}@example.com"
                country = random.choice(countries)
                created = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 600), seconds=random.randint(0, 86400))
                cust_rows.append((name, email, country, created))

            cursor.executemany("INSERT INTO customers (name, email, country, created_at) VALUES (%s, %s, %s, %s)", cust_rows)

            # Seed orders
            statuses = ["COMPLETED", "PENDING", "CANCELLED", "PROCESSING"]
            order_rows = []
            for i in range(3000):
                cid = random.randint(1, 1000)
                amt = round(random.uniform(15.0, 1500.0), 2)
                st = random.choice(statuses)
                odate = datetime(2023, 1, 1) + timedelta(days=random.randint(0, 600), seconds=random.randint(0, 86400))
                order_rows.append((cid, amt, st, odate))

            cursor.executemany("INSERT INTO orders (customer_id, total_amount, status, order_date) VALUES (%s, %s, %s, %s)", order_rows)

            # Seed products
            categories = ["Electronics", "Books", "Apparel", "Home", "Sports"]
            prod_rows = []
            for i in range(300):
                pname = f"Smart Product Model {i} {random.choice(['Pro', 'Max', 'Lite', 'Plus'])}"
                cat = random.choice(categories)
                prc = round(random.uniform(5.0, 999.0), 2)
                prod_rows.append((pname, cat, prc, 1))

            cursor.executemany("INSERT INTO products (product_name, category, price, is_active) VALUES (%s, %s, %s, %s)", prod_rows)

            conn.commit()
            print("Sample data populated: 1,000 customers, 3,000 orders, 300 products.")
        else:
            print(f"Sample data already present ({cust_cnt} customers).")

    conn.close()
    return True


if __name__ == "__main__":
    setup_sample_database(password="MySQL@1234")
