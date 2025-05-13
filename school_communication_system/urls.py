from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from communications import views as comm_views # Import view từ app communications

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Include các URL của app communications dưới một prefix (ví dụ: /communications/)
    path('communications/', include('communications.urls')), # Namespace 'communications' sẽ được dùng ở đây

    # Trang chủ sẽ trỏ trực tiếp đến view notification_list
    path('', comm_views.notification_list, name='homepage'), # Đặt tên URL là 'homepage'
]