// services/product-web/src/App.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8085/api';

function App() {
    // ── Product list ──────────────────────────────────────────────────────────
    const [productsList, setProductsList] = useState([]);
    const [selectedProduct, setSelectedProduct] = useState(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalProducts, setTotalProducts] = useState(0);
    const pageSize = 8;

    // ── Recommendation ────────────────────────────────────────────────────────
    const [userId, setUserId] = useState('');
    const [userIdInput, setUserIdInput] = useState('');
    const [recommendations, setRecommendations] = useState([]);
    const [recSource, setRecSource] = useState('');

    // ── Loading / Error ───────────────────────────────────────────────────────
    const [loadingList, setLoadingList] = useState(false);
    const [loadingDetail, setLoadingDetail] = useState(false);
    const [loadingRec, setLoadingRec] = useState(false);
    const [error, setError] = useState(null);

    // LUỒNG 1: Danh sách sản phẩm phân trang
    const fetchProductsPage = async (page) => {
        setLoadingList(true);
        setError(null);
        try {
            const response = await axios.get(`${API_BASE}/products`, {
                params: { page, size: pageSize }
            });
            setProductsList(response.data.data);
            setTotalProducts(response.data.total);
            setCurrentPage(response.data.page);
        } catch (err) {
            setError('Lỗi kết nối API danh sách! Hãy chắc chắn Spring Boot đang chạy ở port 8085.');
        } finally {
            setLoadingList(false);
        }
    };

    useEffect(() => {
        fetchProductsPage(1);
    }, []);

    // LUỒNG 2: Chi tiết sản phẩm theo ID
    const handleProductClick = async (productId) => {
        setLoadingDetail(true);
        setSelectedProduct(null);
        try {
            const response = await axios.get(`${API_BASE}/products/${productId}`);
            setSelectedProduct(response.data);
        } catch (err) {
            alert(err.response?.data?.detail || 'Không thể lấy thông tin chi tiết sản phẩm!');
        } finally {
            setLoadingDetail(false);
        }
    };

    // LUỒNG 3: Gợi ý sản phẩm theo userId (personalized hoặc cold-start)
    const fetchRecommendations = async (uid) => {
        if (!uid.trim()) return;
        setLoadingRec(true);
        setRecommendations([]);
        setRecSource('');
        try {
            const response = await axios.get(`${API_BASE}/recommend`, {
                params: { userId: uid.trim() }
            });
            setRecommendations(response.data.recommendations || []);
            setRecSource(response.data.source || '');
            setUserId(uid.trim());
        } catch (err) {
            alert('Không thể lấy danh sách gợi ý!');
        } finally {
            setLoadingRec(false);
        }
    };

    const handleRecSubmit = (e) => {
        e.preventDefault();
        fetchRecommendations(userIdInput);
    };

    return (
        <div className="container">
            <header>
                <h1>Olist Recommendation Demo</h1>
                <p className="subtitle">Dữ liệu thật từ PostgreSQL — Speed Layer qua Spring Boot</p>
            </header>

            {error && <div className="error-box">⚠️ {error}</div>}

            <div className="main-layout">
                {/* CỘT TRÁI: Danh sách sản phẩm phân trang */}
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

                {/* CỘT PHẢI: Gợi ý + Chi tiết */}
                <div className="content">

                    {/* SECTION 1: Gợi ý sản phẩm */}
                    <div className="section-box">
                        <h2>🤖 Gợi ý sản phẩm (Recommendation)</h2>

                        <form onSubmit={handleRecSubmit} style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
                            <input
                                type="text"
                                placeholder="Nhập User ID (customer_id thật hoặc bất kỳ)..."
                                value={userIdInput}
                                onChange={(e) => setUserIdInput(e.target.value)}
                                style={{
                                    flex: 1, padding: '8px 12px', borderRadius: '8px',
                                    border: '1px solid #e2e8f0', fontSize: '13px'
                                }}
                            />
                            <button
                                type="submit"
                                disabled={loadingRec}
                                style={{
                                    padding: '8px 16px', borderRadius: '8px', cursor: 'pointer',
                                    background: '#2563eb', color: 'white', border: 'none', fontWeight: '600'
                                }}
                            >
                                {loadingRec ? '...' : 'Lấy gợi ý'}
                            </button>
                        </form>

                        {loadingRec && <div className="loading">🔄 Đang truy vấn recommendations...</div>}

                        {!loadingRec && recommendations.length > 0 && (
                            <>
                                <div style={{ marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <span style={{ fontSize: '13px', color: '#64748b' }}>
                                        User: <b>{userId}</b>
                                    </span>
                                    <span className={`rec-badge ${recSource === 'personalized' ? 'rec-badge-personal' : 'rec-badge-cold'}`}>
                                        {recSource === 'personalized' ? '✨ Cá nhân hóa' : '🔥 Phổ biến (Cold-start)'}
                                    </span>
                                </div>
                                <div className="grid-recommendations">
                                    {recommendations.map((rec) => (
                                        <div
                                            key={rec.product_id}
                                            className="rec-card"
                                            onClick={() => handleProductClick(rec.product_id)}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            <span className="rec-icon">🛍️</span>
                                            <span className="rec-category">
                                                {rec.category_english || rec.category || 'N/A'}
                                            </span>
                                            <span className="rec-id">{rec.product_id}</span>
                                            {rec.score != null && (
                                                <span style={{ fontSize: '11px', color: '#16a34a', fontWeight: '600' }}>
                                                    score: {rec.score.toFixed(1)}
                                                </span>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </>
                        )}

                        {!loadingRec && recommendations.length === 0 && userId && (
                            <p style={{ color: '#94a3b8', fontSize: '13px' }}>Không có gợi ý nào.</p>
                        )}

                        {!userId && !loadingRec && (
                            <p style={{ color: '#94a3b8', fontSize: '13px' }}>
                                Nhập một customer_id thật để xem gợi ý cá nhân hóa, hoặc bất kỳ ID mới để xem cold-start.
                            </p>
                        )}
                    </div>

                    {/* SECTION 2: Chi tiết sản phẩm */}
                    <div className="section-box" style={{ minHeight: '200px' }}>
                        <h2>🔍 Chi tiết sản phẩm</h2>

                        {loadingDetail && <div className="loading">🔄 Đang thực hiện Query SQL tìm kiếm bản ghi...</div>}

                        {!loadingDetail && selectedProduct ? (
                            <div className="detail-card">
                                <p><b>Mã sản phẩm:</b> <span className="highlight" style={{ fontSize: '15px' }}>{selectedProduct.product_id}</span></p>
                                <p><b>Danh mục (VI):</b> <span style={{ textTransform: 'uppercase', color: '#1e293b', fontWeight: 'bold' }}>{selectedProduct.product_category_name || 'N/A'}</span></p>
                                {selectedProduct.product_category_name_english && (
                                    <p><b>Danh mục (EN):</b> <span style={{ color: '#2563eb', fontWeight: '600' }}>{selectedProduct.product_category_name_english}</span></p>
                                )}
                                <p><b>Độ dài tên (Name Length):</b> {selectedProduct.product_name_lenght ?? 'N/A'} ký tự</p>
                                <p><b>Độ dài mô tả (Description Length):</b> {selectedProduct.product_description_length ?? 'N/A'} ký tự</p>
                                {selectedProduct.product_photos_qty != null && (
                                    <p><b>Số ảnh:</b> {selectedProduct.product_photos_qty}</p>
                                )}
                                {selectedProduct.product_weight_g != null && (
                                    <p><b>Trọng lượng:</b> {selectedProduct.product_weight_g} g</p>
                                )}
                            </div>
                        ) : (
                            !loadingDetail && (
                                <div style={{ textAlign: 'center', color: '#94a3b8', marginTop: '40px' }}>
                                    <span style={{ fontSize: '40px' }}>👉</span>
                                    <p>Bấm chọn một sản phẩm từ danh sách hoặc từ ô gợi ý để xem chi tiết.</p>
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
