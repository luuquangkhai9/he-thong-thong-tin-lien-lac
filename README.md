# he-thong-thong-tin-lien-lac

## Hướng dẫn Cài đặt và Chạy Dự án

Dưới đây là các bước để cài đặt và chạy dự án này trên máy tính của bạn.

**CẢNH BÁO BẢO MẬT:**
Các thông tin cấu hình như `SECRET_KEY` và chi tiết kết nối cơ sở dữ liệu hiện đang được đặt trong file `school_communication_system/settings.py`. Khi bạn clone dự án này, bạn **PHẢI** thay đổi các giá trị này cho phù hợp với môi trường của bạn và đảm bảo an toàn. Đặc biệt, `SECRET_KEY` cần được thay thế bằng một giá trị mới, mạnh và bí mật.

### Yêu cầu Tiên quyết:

* **Python:** Phiên bản 3.8 trở lên (khuyến nghị 3.10+).
* **Pip:** Trình quản lý gói của Python.
* **Git:** Hệ thống quản lý phiên bản.
* **MySQL Server:** Cài đặt MySQL Server (ví dụ: 8.0) và một công cụ quản lý như MySQL Workbench. Nhớ mật khẩu `root` của MySQL.

### Các bước Cài đặt:

1.  **Clone Repository:**
    ```bash
    git clone <URL_repository_GitHub_của_bạn>
    cd <tên_thư_mục_repository_của_bạn>
    ```

2.  **Tạo và Kích hoạt Môi trường ảo:**
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # macOS/Linux:
    source venv/bin/activate
    ```

3.  **Cài đặt các Gói Phụ thuộc:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Thiết lập Cơ sở dữ liệu MySQL:**
    * Mở MySQL Workbench.
    * Kết nối đến MySQL Server của bạn.
    * Tạo một database mới cho dự án, ví dụ `school_communication_db`:
        ```sql
        CREATE DATABASE school_communication_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
        ```
    * **(Khuyến nghị)** Tạo một user MySQL riêng cho dự án:
        ```sql
        CREATE USER 'school_user'@'localhost' IDENTIFIED BY 'your_strong_password_here';
        GRANT ALL PRIVILEGES ON school_communication_db.* TO 'school_user'@'localhost';
        FLUSH PRIVILEGES;
        ```
        Thay thế bằng tên người dùng và mật khẩu bạn muốn.

5.  **Cấu hình file `settings.py`:**
    * Mở file `school_communication_system/settings.py` trong dự án bạn vừa clone.
    * **Cập nhật `SECRET_KEY`:** Thay thế giá trị placeholder bằng một khóa bí mật mới, mạnh và ngẫu nhiên. Bạn có thể dùng các công cụ online để tạo hoặc tự tạo một chuỗi dài và phức tạp.
    * **Cập nhật `DATABASES`:**
        * `NAME`: Tên database bạn đã tạo (ví dụ: `school_communication_db`).
        * `USER`: User MySQL bạn đã tạo (ví dụ: `school_user`) hoặc `root`.
        * `PASSWORD`: Mật khẩu của user MySQL đó.
        * `HOST`: Thường là `127.0.0.1`.
        * `PORT`: Thường là `3306`.
    * **Cập nhật `DEBUG`:** Đặt là `True` cho môi trường phát triển.

6.  **Chạy Migrations:**
    ```bash
    python manage.py migrate
    ```

7.  **Tạo Superuser (Tài khoản Quản trị viên):**
    ```bash
    python manage.py createsuperuser
    ```
    Làm theo hướng dẫn để nhập username, email, và mật khẩu.

8.  **Chạy Development Server:**
    ```bash
    python manage.py runserver
    ```
    Truy cập `http://127.0.0.1:8000/` trong trình duyệt.

### Truy cập Trang Admin:

* Truy cập `http://127.0.0.1:8000/admin/` và đăng nhập bằng tài khoản superuser.

---