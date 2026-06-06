# services/product-api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router as product_router

app = FastAPI(
    title="Olist Big Data API Service",
    description="API lấy dữ liệu sản phẩm đã tinh lọc từ tầng Gold của hệ thống Big Data Pipeline",
    version="1.0.0"
)

# Cấu hình CORS để Frontend (React, Vue, v.v.) ở máy ngoài gọi vào được
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các Router API đã viết
app.include_router(product_router)

@app.get("/")
def root():
    return {"message": "Product API Service đang chạy ổn định. Truy cập /docs để xem tài liệu chi tiết!"}