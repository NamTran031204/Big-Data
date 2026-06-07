# services/product-api/app/database.py
import os
import psycopg2
from psycopg2 import pool
from contextlib import contextmanager

# Đọc cấu hình từ biến môi trường của Docker
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = os.getenv("DB_NAME", "olist")

try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    print("Khởi tạo Database Connection Pool thành công!")
except Exception as e:
    print(f"Lỗi khởi tạo Database Pool: {e}")
    connection_pool = None

@contextmanager
def get_db_cursor():
    if connection_pool is None:
        raise Exception("Database connection pool không khả dụng.")
    
    connection = connection_pool.getconn()
    cursor = connection.cursor()
    try:
        yield cursor
        connection.commit()
    except Exception as e:
        connection.rollback()
        raise e
    finally:
        cursor.close()
        connection_pool.putconn(connection)