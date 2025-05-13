from django.urls import path
from . import views

app_name = 'academic_records'

urlpatterns = [
    # URL cho học sinh/phụ huynh xem điểm của họ/con họ
    path('scores/', views.view_scores, name='view_scores'),
    
    # URL cho giáo viên nhập điểm
    path('enter-scores/', views.enter_scores, name='enter_scores'),
    
    # URL cho giáo viên xem điểm của lớp họ chủ nhiệm
    path('teacher/class-scores/', views.teacher_view_class_scores, name='teacher_view_class_scores'),
    
    # Thêm các URL khác cho academic_records sau nếu cần
    # Ví dụ: xem khen thưởng/kỷ luật, xem đánh giá
]
