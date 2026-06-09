import psycopg2
from collections import defaultdict


class DataLoader:

    def __init__(self):

        self.conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="postgres",
            user="postgres",
            password="postgres"
        )

    def load_customers(self):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT customer_id
            FROM customer
            ORDER BY customer_id
            LIMIT 3
        """)

        customers = [
            row[0]
            for row in cur.fetchall()
        ]

        cur.close()

        return customers

    def load_products(self):

        cur = self.conn.cursor()

        cur.execute("""
            SELECT
                product_id,
                product_category_name
            FROM product
            WHERE product_category_name IS NOT NULL
        """)

        rows = cur.fetchall()

        cur.close()

        product_category_map = {}

        products_by_category = defaultdict(list)

        all_products = []

        for product_id, category in rows:

            product_category_map[
                product_id
            ] = category

            products_by_category[
                category
            ].append(product_id)

            all_products.append(product_id)

        return (
            product_category_map,
            products_by_category,
            all_products
        )