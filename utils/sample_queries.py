"""Categorized SQL Queries representing real-world query patterns.

Organized by categories: Flipkart / E-Commerce, Numerical Functions, Subqueries, Date & Sargability.
"""

CATEGORIZED_QUERIES = {
    "Flipkart (E-Commerce)": {
        "Flipkart Product Catalog Search": {
            "title": "Unindexed Leading Wildcard Search",
            "description": "Searching products using LIKE '%laptop%' invalidates B-Tree index seeks on product title.",
            "sql": """SELECT *
FROM flipkart_products
WHERE product_name LIKE '%laptop%'
  AND is_available = 1;"""
        },
        "Flipkart Order & Customer Cart Details": {
            "title": "Comma Separated Tables Without Join Condition",
            "description": "Cross join between customer cart and products causing Cartesian multiplication (M x N).",
            "sql": """SELECT *
FROM customers, cart_items
WHERE status = 'PENDING';"""
        },
        "Flipkart High Value Orders": {
            "title": "Unbounded SELECT * on Orders Table",
            "description": "Retrieves all columns and all rows without LIMIT on a high-velocity orders table.",
            "sql": """SELECT *
FROM flipkart_orders
WHERE payment_status = 'SUCCESS'
ORDER BY order_date DESC;"""
        }
    },
    "Numerical Functions": {
        "Rounding on Predicate Column": {
            "title": "Non-Sargable Arithmetic on Column",
            "description": "Wrapping the price column in mathematical functions disables index usage.",
            "sql": """SELECT id, product_name, price
FROM products
WHERE ROUND(price * 0.8) > 500
  AND category = 'Electronics';"""
        },
        "Redundant DISTINCT with Aggregate": {
            "title": "Redundant DISTINCT on Grouped Output",
            "description": "Wasteful deduplication pass on rows already guaranteed unique by GROUP BY.",
            "sql": """SELECT DISTINCT
category,
COUNT(id) AS total_products,
AVG(price) AS avg_price
FROM products
GROUP BY category;"""
        },
        "Random Product Sampling Filesort": {
            "title": "ORDER BY RAND() Full Table Filesort",
            "description": "Assigns random float to every row in the table, sorting millions of rows in memory.",
            "sql": """SELECT *
FROM products
ORDER BY RAND()
LIMIT 5;"""
        }
    },
    "Subqueries": {
        "Suboptimal IN (SELECT ...) Subquery": {
            "title": "Inefficient Subquery with IN Operator",
            "description": "Evaluates inner SELECT repeatedly or materializes unindexed sets instead of short-circuiting.",
            "sql": """SELECT id, name, email
FROM customers
WHERE id IN (
    SELECT customer_id
    FROM orders
    WHERE total_amount > 1000
);"""
        },
        "NOT IN Predicate with NULL Risk": {
            "title": "Unindexed NOT IN Predicate",
            "description": "NOT IN evaluates to NULL if any inner record is NULL, causing performance and correctness issues.",
            "sql": """SELECT id, name
FROM customers
WHERE id NOT IN (
    SELECT customer_id
    FROM inactive_accounts
);"""
        }
    },
    "Date & Sargability": {
        "Non-Sargable YEAR() Function": {
            "title": "YEAR() Function on Date Column",
            "description": "Forces full table scan because YEAR() cannot utilize B-Tree index range scans.",
            "sql": """SELECT *
FROM orders
WHERE YEAR(order_date) = 2024
  AND status = 'COMPLETED';"""
        },
        "Destructive Statement Missing WHERE": {
            "title": "UPDATE Statement Without Filter",
            "description": "Critical table lock and data wipe risk without WHERE condition.",
            "sql": """UPDATE user_accounts
SET is_verified = 0;"""
        }
    }
}

# Flat dictionary for backward compatibility
SAMPLE_QUERIES = {}
for cat, queries in CATEGORIZED_QUERIES.items():
    for name, data in queries.items():
        SAMPLE_QUERIES[f"[{cat}] {name}"] = data
