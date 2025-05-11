from django.contrib import admin
from django.urls import path, include # Thêm include
from django.contrib.auth import views as auth_views # Import các view xác thực của Django

# Sẽ tạo view cho trang chủ sau
# from some_app import views as home_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # URLs cho xác thực người dùng
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'), # Sau khi logout sẽ về trang login

    # URL cho app accounts (nếu sau này bạn có thêm URL cho accounts như đăng ký, đổi mật khẩu)
    # path('accounts/', include('accounts.urls')), # Chúng ta sẽ tạo file accounts/urls.py sau nếu cần

    # URL cho app communications (để hiển thị thông báo)
    path('communications/', include('communications.urls')),

    # URL cho trang chủ - Sẽ hiển thị thông báo ở đây
    # path('', home_views.homepage, name='homepage'), # Ví dụ, sẽ trỏ đến view hiển thị thông báo
    # Tạm thời, chúng ta có thể trỏ trang chủ đến danh sách thông báo của app communications
    path('', include('communications.urls')), # Đảm bảo communications.urls có path cho ''
]