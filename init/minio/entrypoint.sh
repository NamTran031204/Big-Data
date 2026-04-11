#!/bin/bash
# filepath: e:\DaiCuongBK\Project3\FileSharing\server\minio\entrypoint.sh

# ============================================================
# ENTRYPOINT SCRIPT CHO CUSTOM MINIO VỚI NETWORK THROTTLING
# ============================================================

set -e

# ============================================================
# FUNCTION: Hiển thị banner và cấu hình
# ============================================================
print_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║           MinIO with Network Throttling                    ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📊 Network Configuration:"
    echo "   ├─ THROTTLE_ENABLED:    ${THROTTLE_ENABLED}"
    echo "   ├─ BANDWIDTH_LIMIT:     ${BANDWIDTH_LIMIT}"
    echo "   ├─ LATENCY_MS:          ${LATENCY_MS}ms"
    echo "   ├─ LATENCY_JITTER_MS:   ${LATENCY_JITTER_MS}ms"
    echo "   ├─ PACKET_LOSS_PERCENT: ${PACKET_LOSS_PERCENT}%"
    echo "   └─ NETWORK_INTERFACE:   ${NETWORK_INTERFACE}"
    echo ""
}

# ============================================================
# FUNCTION: Xóa tc rules cũ
# ============================================================
cleanup_tc() {
    echo "🧹 Cleaning up existing tc rules..."
    tc qdisc del dev ${NETWORK_INTERFACE} root 2>/dev/null || true
    echo "   ✅ Done"
}

# ============================================================
# FUNCTION: Áp dụng Traffic Control rules
# ============================================================
#
# CẤU TRÚC TC:
#
#     root qdisc (1:) - HTB
#           │
#           ▼
#     class (1:1) - Bandwidth limit
#           │
#           ▼
#     netem qdisc - Latency, Jitter, Packet Loss
#
# ============================================================
apply_tc() {
    echo "⚙️  Applying Traffic Control rules..."

    # ----------------------------------------------------------
    # BƯỚC 1: Kiểm tra interface tồn tại
    # ----------------------------------------------------------
    if ! ip link show ${NETWORK_INTERFACE} &>/dev/null; then
        echo "   ❌ Interface ${NETWORK_INTERFACE} not found!"
        echo "   Available interfaces:"
        ip link show | grep -E "^[0-9]+" | awk '{print "      - " $2}' | tr -d ':'
        echo "   ⚠️  Skipping tc configuration..."
        return 1
    fi

    # ----------------------------------------------------------
    # BƯỚC 2: Tạo root qdisc với HTB
    # ----------------------------------------------------------
    # HTB (Hierarchical Token Bucket):
    # - Thuật toán quản lý băng thông theo cấu trúc phân cấp
    # - Cho phép chia sẻ băng thông giữa các class
    # - default 10: Traffic không match rule nào vào class 1:10
    # ----------------------------------------------------------
    echo "   📌 Creating root HTB qdisc..."
    tc qdisc add dev ${NETWORK_INTERFACE} root handle 1: htb default 10

    # ----------------------------------------------------------
    # BƯỚC 3: Tạo class với bandwidth limit
    # ----------------------------------------------------------
    # Giải thích các tham số:
    # - rate: Băng thông được đảm bảo (guaranteed)
    # - ceil: Băng thông tối đa có thể dùng (nếu có thừa)
    # - burst: Lượng data có thể gửi burst (32kb là hợp lý)
    # ----------------------------------------------------------
    echo "   📌 Creating bandwidth-limited class (${BANDWIDTH_LIMIT})..."
    tc class add dev ${NETWORK_INTERFACE} parent 1: classid 1:10 htb \
        rate ${BANDWIDTH_LIMIT} \
        ceil ${BANDWIDTH_LIMIT} \
        burst 32k

    # ----------------------------------------------------------
    # BƯỚC 4: Thêm netem để giả lập network conditions
    # ----------------------------------------------------------
    # netem (Network Emulator) cho phép:
    # - delay: Thêm latency
    # - loss: Mô phỏng packet loss
    # - reorder: Mô phỏng packet reordering
    # - corrupt: Mô phỏng data corruption
    # ----------------------------------------------------------
    echo "   📌 Adding netem for latency/loss simulation..."

    # Xây dựng netem command
    NETEM_OPTS=""

    # Thêm delay nếu LATENCY_MS > 0
    if [ "${LATENCY_MS:-0}" -gt 0 ]; then
        NETEM_OPTS="${NETEM_OPTS} delay ${LATENCY_MS}ms"

        # Thêm jitter nếu LATENCY_JITTER_MS > 0
        if [ "${LATENCY_JITTER_MS:-0}" -gt 0 ]; then
            # distribution normal: Phân phối chuẩn (realistic)
            NETEM_OPTS="${NETEM_OPTS} ${LATENCY_JITTER_MS}ms distribution normal"
        fi
    fi

    # Thêm packet loss nếu PACKET_LOSS_PERCENT > 0
    if [ "${PACKET_LOSS_PERCENT:-0}" -gt 0 ]; then
        NETEM_OPTS="${NETEM_OPTS} loss ${PACKET_LOSS_PERCENT}%"
    fi

    # Áp dụng netem (hoặc pfifo nếu không có options)
    if [ -n "${NETEM_OPTS}" ]; then
        tc qdisc add dev ${NETWORK_INTERFACE} parent 1:10 handle 10: netem ${NETEM_OPTS}
        echo "   📌 netem options: ${NETEM_OPTS}"
    else
        # Không có delay/loss, dùng pfifo đơn giản
        tc qdisc add dev ${NETWORK_INTERFACE} parent 1:10 handle 10: pfifo limit 1000
        echo "   📌 Using simple pfifo (no delay/loss configured)"
    fi

    echo "   ✅ Traffic Control rules applied successfully!"
}

# ============================================================
# FUNCTION: Hiển thị tc rules đã áp dụng
# ============================================================
show_tc_rules() {
    echo ""
    echo "📋 Active TC Rules:"
    echo "─────────────────────────────────────────────────────────"
    echo "Qdiscs:"
    tc qdisc show dev ${NETWORK_INTERFACE} 2>/dev/null || echo "   (none)"
    echo ""
    echo "Classes:"
    tc class show dev ${NETWORK_INTERFACE} 2>/dev/null || echo "   (none)"
    echo "─────────────────────────────────────────────────────────"
}

# ============================================================
# FUNCTION: Hiển thị thông tin băng thông dễ hiểu
# ============================================================
show_bandwidth_info() {
    echo ""
    echo "📈 Bandwidth Translation:"
    echo "─────────────────────────────────────────────────────────"

    # Parse bandwidth value
    BW_VALUE=$(echo ${BANDWIDTH_LIMIT} | grep -oE '[0-9]+')
    BW_UNIT=$(echo ${BANDWIDTH_LIMIT} | grep -oE '[a-zA-Z]+')

    case ${BW_UNIT} in
        kbit|Kbit)
            BW_KBPS=$(echo "scale=2; ${BW_VALUE} / 8" | bc 2>/dev/null || echo "N/A")
            echo "   ${BANDWIDTH_LIMIT} ≈ ${BW_KBPS} KB/s"
            ;;
        mbit|Mbit)
            BW_MBPS=$(echo "scale=2; ${BW_VALUE} / 8" | bc 2>/dev/null || echo "N/A")
            echo "   ${BANDWIDTH_LIMIT} ≈ ${BW_MBPS} MB/s (megabytes)"
            echo "   Upload 100MB file ≈ $(echo "scale=0; 100 / ${BW_MBPS}" | bc 2>/dev/null || echo "N/A") seconds"
            ;;
        *)
            echo "   ${BANDWIDTH_LIMIT}"
            ;;
    esac
    echo "─────────────────────────────────────────────────────────"
}

# ============================================================
# MAIN EXECUTION
# ============================================================

print_banner

# Kiểm tra throttling có được bật không
if [ "${THROTTLE_ENABLED}" = "true" ] || [ "${THROTTLE_ENABLED}" = "1" ]; then
    echo "🔧 Network throttling is ENABLED"
    echo ""

    # Cleanup rules cũ
    cleanup_tc

    # Áp dụng rules mới
    if apply_tc; then
        show_tc_rules
        show_bandwidth_info
    else
        echo "⚠️  Failed to apply tc rules, running without throttling"
    fi
else
    echo "⏭️  Network throttling is DISABLED"
    echo "   Running MinIO at full network speed"
fi

echo ""
echo "🚀 Starting MinIO server..."
echo "═══════════════════════════════════════════════════════════"
echo ""

# ============================================================
# KHỞI ĐỘNG MINIO
# ============================================================
# exec thay thế shell process bằng minio process
# $@ là arguments từ CMD trong Dockerfile
# ============================================================
exec /usr/local/bin/minio "$@"