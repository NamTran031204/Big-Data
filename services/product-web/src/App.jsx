// services/product-web/src/App.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/products';

function App() {
    // Trạng thái lưu dữ liệu từ Database thật
    const [productsList, setProductsList] = useState([]);
    const [selectedProduct, setSelectedProduct] = useState(null);

    // Trạng thái phân trang động
    const [currentPage, setCurrentPage] = useState(1);
    const [totalProducts, setTotalProducts] = useState(0);
    const pageSize = 8; // Số lượng sản phẩm hiển thị trên mỗi trang

    // Trạng thái Loading / Error
    const [loadingList, setLoadingList] = useState(false);
    const [loadingDetail, setLoadingDetail] = useState(false);
    const [error, setError] = useState(null);

    // LUỒNG 1: TỰ ĐỘNG GỌI API GETPAGE KHI ĐỔI TRANG HOẶC VỪA VÀO WEB
    const fetchProductsPage = async (page) => {
        setLoadingList(true);
        setError(null);
        try {
            const response = await axios.get(API_BASE_URL, {
                params: { page: page, size: pageSize }
            });
            setProductsList(response.data.data);
            setTotalProducts(response.data.total);
            setCurrentPage(response.data.page);
        } catch (err) {
            setError('Lỗi kết nối API danh sách! Hãy chắc chắn Docker Backend đang chạy.');
        } finally {
            setLoadingList(false);
        }
    };

    useEffect(() => {
        fetchProductsPage(1); // Mặc định mở trang 1 lên trước
    }, []);

    // LUỒNG 2: CLICK VÀO SẢN PHẨM KHỞI CHẠY API GETBYID CHI TIẾT THẬT
    const handleProductClick = async (productId) => {
        setLoadingDetail(true);
        setSelectedProduct(null);
        try {
            const response = await axios.get(`${API_BASE_URL}/${productId}`);
            setSelectedProduct(response.data);
        } catch (err) {
            alert(err.response?.data?.detail || 'Không thể lấy thông tin chi tiết sản phẩm!');
        } finally {
            setLoadingDetail(false);
        }
    };

    return (
        <div className="container">
            <header>
                <h1>Olist Production Real-time Database Viewer</h1>
                <p className="subtitle">Dữ liệu thật kết nối trực tiếp PostgreSQL Tầng Gold qua FastAPI</p>
            </header>

            {error && <div className="error-box">⚠️ {error}</div>}

            <div className="main-layout">
                {/* CỘT TRÁI: HIỂN THỊ DANH SÁCH SẢN PHẨM PHÂN TRANG THẬT TỪ DB */}
                <div className="sidebar">
                    <h2>📦 Danh sách sản phẩm (Tổng: {totalProducts})</h2>

                    {loadingList ? (
                        <div className="loading">🔄 Đang đọc dữ liệu từ PostgreSQL...</div>
                    ) : (
                        <div className="list-buttons">
                            {productsList.map((product) => (
                                <button
                                    key={product.product_id}
                                    onClick={() => handleProductClick(product.product_id)}
                                    className={`product-btn ${selectedProduct?.product_id === product.product_id ? 'active' : ''}`}
                                    style={{ borderColor: selectedProduct?.product_id === product.product_id ? '#2563eb' : '' }}
                                >
                                    <div className="btn-title">🏷️ {product.product_category_name || 'Chưa phân loại'}</div>
                                    <div className="btn-id">{product.product_id}</div>
                                </button>
                            ))}
                        </div>
                    )}

                    {/* THANH ĐIỀU HƯỚNG PHÂN TRANG ĐỘNG */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px', alignItems: 'center' }}>
                        <button
                            disabled={currentPage <= 1 || loadingList}
                            onClick={() => fetchProductsPage(currentPage - 1)}
                            style={{ padding: '8px 15px', cursor: 'pointer' }}
                        >
                            ⬅️ Trang trước
                        </button>
                        <span>Trang <b>{currentPage}</b> / {Math.ceil(totalProducts / pageSize)}</span>
                        <button
                            disabled={currentPage >= Math.ceil(totalProducts / pageSize) || loadingList}
                            onClick={() => fetchProductsPage(currentPage + 1)}
                            style={{ padding: '8px 15px', cursor: 'pointer' }}
                        >
                            Trang sau ➡️
                        </button>
                    </div>
                </div>

                {/* CỘT PHẢI: XEM CHI TIẾT KHI CLICK SẢN PHẨM QUA API GETBYID */}
                <div className="content">
                    <div className="section-box" style={{ minHeight: '300px' }}>
                        <h2>🔍 Chi tiết sản phẩm lấy từ API getById</h2>

                        {loadingDetail && <div className="loading">🔄 Đang thực hiện Query SQL tìm kiếm bản ghi...</div>}

                        {!loadingDetail && selectedProduct ? (
                            <div className="detail-card">
                                <p><b>Mã sản phẩm (Product ID):</b> <span className="highlight" style={{ fontSize: '15px' }}>{selectedProduct.product_id}</span></p>
                                <p><b>Tên danh mục (Category):</b> <span style={{ textTransform: 'uppercase', color: '#1e293b', fontWeight: 'bold' }}>{selectedProduct.product_category_name || 'N/A'}</span></p>
                                <p><b>Độ dài ký tự của tên (Name Length):</b> {selectedProduct.product_name_lenght} ký tự</p>
                                <p><b>Độ dài ký tự mô tả (Description Length):</b> {selectedProduct.product_description_length} ký tự</p>
                            </div>
                        ) : (
                            !loadingDetail && (
                                <div style={{ textAlign: 'center', color: '#94a3b8', marginTop: '60px' }}>
                                    <span style={{ fontSize: '40px' }}>👉</span>
                                    <p>Bấm chọn vào một mã sản phẩm ở danh sách bên trái.<br />Hệ thống sẽ gọi API chi tiết dựa vào ID để hiển thị thông tin.</p>
                                </div>
                            )
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default App;