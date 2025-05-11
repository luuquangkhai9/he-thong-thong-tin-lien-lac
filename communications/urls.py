from django.urls import path
from . import views # Chúng ta sẽ tạo views.py sau

app_name = 'communications' # Đặt namespace cho app này

urlpatterns = [
    path('', views.notification_list, name='notification_list'), # Trang chủ của app communications sẽ là danh sách thông báo
    # Thêm các URL khác cho communications sau (ví dụ: xem chi tiết thông báo, gửi tin nhắn,...)
]