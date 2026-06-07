# services/product-api/app/routes.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Any
from app.database import get_db_cursor

router = APIRouter(prefix="/api/products", tags=["Products"])

# Dùng kiểu dữ liệu linh hoạt (Any) để nhận mọi tên cột trả về từ DB thật
class PaginatedProductResponse(BaseModel):
    total: int
    page: int
    size: int
    data: List[Any]

# --- 1. API: getPage (Lấy danh sách phân trang an toàn) ---
@router.get("", response_model=PaginatedProductResponse)
def get_page(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100)
):
    offset = (page - 1) * size
    
    try:
        with get_db_cursor() as cursor:
            # 1. Đếm tổng số lượng dòng thật
            cursor.execute("SELECT COUNT(*) FROM products;")
            total_count = cursor.fetchone()[0]
            
            # 2. Dùng SELECT * để lấy toàn bộ cột mà không sợ sai tên trường
            query = "SELECT * FROM products LIMIT %s OFFSET %s;"
            cursor.execute(query, (size, offset))
            rows = cursor.fetchall()
            
            # Lấy danh sách tên cột thực tế từ DB để map chính xác thành Dictionary
            colnames = [desc[0] for desc in cursor.description]
            
            products = []
            for row in rows:
                # Tự động bắt cặp tên cột thật với giá trị tương ứng
                product_dict = dict(zip(colnames, row))
                products.append(product_dict)
                
        return {
            "total": total_count,
            "page": page,
            "size": size,
            "data": products
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Error List: {str(e)}")


# --- 2. API: Lấy chi tiết theo productId an toàn ---
@router.get("/{product_id}")
def get_product_by_id(product_id: str):
    try:
        with get_db_cursor() as cursor:
            # Dùng SELECT * tìm theo product_id
            query = "SELECT * FROM products WHERE product_id = %s;"
            cursor.execute(query, (product_id,))
            row = cursor.fetchone()
            
            if row is None:
                raise HTTPException(status_code=404, detail=f"Không tìm thấy sản phẩm có mã ID: {product_id}")
                
            # Tự động map tên cột thật của bảng chi tiết
            colnames = [desc[0] for desc in cursor.description]
            return dict(zip(colnames, row))
            
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database Error Detail: {str(e)}")