from django.urls import path
from . import views # Chúng ta sẽ tạo views.py sau

app_name = 'communications' # Đặt namespace cho app này

urlpatterns = [
    path('', views.notification_list, name='notification_list'), # Trang chủ của app communications sẽ là danh sách thông báo
    # Thêm các URL khác cho communications sau (ví dụ: xem chi tiết thông báo, gửi tin nhắn,...)
    path('submit-request/', views.submit_request_form, name='submit_request_form'), # URL MỚI
    path('my-requests/', views.my_submitted_requests, name='my_submitted_requests'), # <<--- URL MỚI ---
    path('department-requests/', views.department_request_list, name='department_request_list'), # <<--- URL MỚI ---
    path('department-requests/<int:pk>/respond/', views.department_request_detail_respond, name='department_respond_request'), # <<--- BỎ COMMENT VÀ SỬA LẠI ---
# --- URLs MỚI CHO GIÁO VIÊN ---
    path('teacher-requests/', views.teacher_request_list, name='teacher_request_list'),
    path('teacher-requests/<int:pk>/respond/', views.teacher_request_detail_respond, name='teacher_respond_request'),
    # --- KẾT THÚC URLs MỚI ---

]