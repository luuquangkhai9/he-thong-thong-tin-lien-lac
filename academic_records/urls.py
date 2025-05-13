from django.urls import path
from . import views

app_name = 'academic_records'

urlpatterns = [
    path('scores/', views.view_scores, name='view_scores'),
    path('enter-scores/', views.enter_scores, name='enter_scores'),
    path('teacher/class-scores/', views.teacher_view_class_scores, name='teacher_view_class_scores'),
    
    path('rewards-discipline/', views.view_reward_discipline, name='view_reward_discipline'),
    path('teacher/class-rewards-discipline/', views.teacher_view_class_rewards_discipline, name='teacher_view_class_rewards_discipline'),
    path('rewards-discipline/add/', views.manage_reward_discipline_record, name='add_reward_discipline'),
    path('rewards-discipline/<int:pk>/edit/', views.manage_reward_discipline_record, name='edit_reward_discipline'),

    # --- URL MỚI CHO XEM TỔNG HỢP KHEN THƯỞNG/KỶ LUẬT TOÀN TRƯỜNG ---
    path('school-wide/rewards-discipline/', views.school_wide_reward_discipline_list, name='school_wide_reward_discipline_list'),
    # --- KẾT THÚC URL MỚI ---
]
