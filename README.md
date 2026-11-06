# 👁️ PGOD (Presence Guardian of Owner Daemon)
## Hệ Thống Giám Sát Sự Sống Thụ Động & Chứng Thực Không Ma Sát Cho Dead-Man Switch

---

### Giới Thiệu
**PGod** là hệ thống giám sát sự sống thụ động (Zero-Friction Proof-of-Life) dành riêng cho Người Sáng Lập của **PGDSecurity**.

Thay vì bắt người dùng phải nhớ và nhập Private Key 3 tháng một lần theo cách thủ công phiền phức:
- **PGod** kết hợp với AI để thu thập và tổng hợp các tín hiệu sự sống tự nhiên xung quanh bạn (Ambient Presence).
- Khi độ tin cậy vượt qua ngưỡng an toàn (**$\ge 75\%$**), PGod sẽ **tự động ký số và gửi lệnh gia hạn** tới PGDSecurity để reset lại bộ đếm 90 ngày.

---

### 3 Cảm Biến Giám Sát Độc Nhất

1. **Stylometry & Prompt Interaction Sensor (`pgod/sensors/stylometry.py`)**:
   - Phân tích cú pháp, phong cách viết code và các dấu ấn ngôn ngữ đặc trưng của Bạn khi làm việc với AI Agent.
2. **Biometric Glance & Windows Hello (`pgod/sensors/biometric.py`)**:
   - Tương tác với hệ thống xác thực sinh trắc học cục bộ của hệ điều hành (Windows Hello / TouchID / Optical Glance 2s) để xác nhận sự hiện diện thực tế của con người trước màn hình.
3. **Mobile Device Telemetry & Giao Thức Đổi Máy (`pgod/sensors/device_telemetry.py`)**:
   - Giám sát vị trí định vị GPS và hành lang di chuyển bình thường trên điện thoại cá nhân.
   - **Giao thức đổi máy đột ngột (Device Replacement Protocol):** Nếu điện thoại bị hỏng hoặc đổi máy mới, cho phép xác thực bằng Master Recovery Seed để đăng ký thiết bị mới tức thì mà không làm kích hoạt Dead-Man switch.

---

### Cài Đặt & Sử Dụng

```bash
# Kiểm tra danh sách thiết bị tin cậy
python -m pgod.cli status

# Thực hiện kiểm tra sự sống và tự động reset timer 90 ngày
python -m pgod.cli verify

# Đổi điện thoại khi máy cũ bị hỏng
python -m pgod.cli replace-device dev-phone-primary-01 dev-phone-new-galaxy "Creator New Phone"

# Chạy ngầm daemon giám sát định kỳ
python -m pgod.cli daemon --interval 3600
```
