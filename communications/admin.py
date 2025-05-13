from django.contrib import admin
from .models import Notification, Conversation, Message, RequestForm # Thêm RequestForm vào import

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'sent_by', 'status', 'created_time', 'publish_time', 'is_published')
    list_filter = ('status', 'is_published', 'created_time', 'publish_time', 'sent_by')
    search_fields = ('title', 'content', 'sent_by__username') # Tìm kiếm theo username của người gửi

    # Các trường ManyToMany nên dùng filter_horizontal hoặc filter_vertical để dễ chọn
    filter_horizontal = ('target_users', 'target_roles', 'target_classes') # Bỏ comment dòng target_departments nếu bạn đã thêm nó vào model

    # Sắp xếp các trường trong form chỉnh sửa chi tiết
    fieldsets = (
        (None, { # Nhóm không có tiêu đề, cho các trường chính
            'fields': ('title', 'content', 'sent_by', 'status', 'publish_time', 'is_published')
        }),
        ('Đối tượng nhận', { # Nhóm cho các trường target
            'classes': ('collapse',), # Cho phép thu gọn nhóm này
            'fields': ('target_users', 'target_roles', 'target_classes') # Bỏ comment dòng target_departments nếu bạn đã thêm nó vào model
        }),
    )

    # Nếu bạn muốn một số trường chỉ đọc sau khi đã gửi (ví dụ)
    # def get_readonly_fields(self, request, obj=None):
    #     if obj and obj.status == 'SENT': # Nếu thông báo đã được gửi
    #         return ('title', 'content', 'sent_by', 'target_users', 'target_roles', 'target_classes', 'publish_time')
    #     return super().get_readonly_fields(request, obj)

# Hoặc cách đăng ký đơn giản:
# admin.site.register(Notification)
class MessageInline(admin.TabularInline): # Hoặc admin.StackedInline nếu muốn hiển thị các trường xếp chồng
    model = Message
    extra = 1 # Số lượng form trống cho Message mới hiển thị ban đầu
    fields = ('sender', 'content', 'sent_at') # Các trường của Message muốn hiển thị/sửa
    readonly_fields = ('sent_at',) # Thời gian gửi thường không nên cho sửa
    # autocomplete_fields = ['sender'] # Nếu danh sách User dài

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'conversation_type', 'created_at', 'updated_at', 'display_participants')
    list_filter = ('conversation_type', 'created_at', 'updated_at')
    search_fields = ('title', 'participants__username') # Tìm theo username của người tham gia
    filter_horizontal = ('participants',) # Widget tốt cho ManyToManyField participants
    inlines = [MessageInline] # Hiển thị Messages như một phần của Conversation

    def display_participants(self, obj):
        # Hiển thị tối đa 3 người tham gia, còn lại là "..."
        participants = obj.participants.all()
        if participants.count() > 3:
            return ", ".join([user.username for user in participants[:3]]) + ", ..."
        return ", ".join([user.username for user in participants])
    display_participants.short_description = "Thành viên" # Đặt tên cột

# Nếu bạn chỉ muốn đăng ký Message một cách riêng lẻ (thường không cần nếu đã có inline)
# @admin.register(Message)
# class MessageAdmin(admin.ModelAdmin):
#     list_display = ('sender', 'conversation_title', 'sent_at_formatted', 'short_content')
#     list_filter = ('sent_at', 'sender', 'conversation')
#     search_fields = ('content', 'sender__username', 'conversation__title')
#     autocomplete_fields = ['sender', 'conversation']

#     def conversation_title(self, obj):
#         return obj.conversation.title if obj.conversation.title else f"Chat ID {obj.conversation.id}"
#     conversation_title.short_description = "Cuộc hội thoại"

#     def sent_at_formatted(self, obj):
#         return obj.sent_at.strftime('%Y-%m-%d %H:%M')
#     sent_at_formatted.short_description = "Thời gian gửi"

#     def short_content(self, obj):
#         return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
#     short_content.short_description = "Nội dung ngắn"

@admin.register(RequestForm)
class RequestFormAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'submitted_by',
        'form_type',
        'status',
        'submission_date',
        'assigned_department',
        'display_assigned_teachers', # Thêm để hiển thị giáo viên
        'response_date'
    )
    list_filter = ('status', 'form_type', 'submission_date', 'assigned_department', 'assigned_teachers') # Thêm assigned_teachers
    search_fields = (
        'title',
        'content',
        'submitted_by__username',
        'related_student__user__username',
        'assigned_teachers__username' # Tìm theo username của giáo viên được gán
    )
    fieldsets = (
        ('Thông tin Đơn', {
            'fields': ('title', 'form_type', 'submitted_by', 'related_student', 'content')
        }),
        ('Đối tượng Xử lý', { # Đổi tên nhóm hoặc thêm nhóm mới
            'fields': ('assigned_department', 'assigned_teachers') # Thêm assigned_teachers
        }),
        ('Xử lý và Trạng thái', {
            'fields': ('status',)
        }),
        ('Phản hồi từ Nhà trường', {
            'classes': ('collapse',),
            'fields': ('response_content', 'responded_by', 'response_date')
        }),
    )
    readonly_fields = ('submission_date',)
    autocomplete_fields = ['submitted_by', 'related_student', 'assigned_department', 'responded_by'] # Giữ nguyên
    filter_horizontal = ('assigned_teachers',) # Widget tốt cho ManyToManyField

    def display_assigned_teachers(self, obj):
        return ", ".join([teacher.username for teacher in obj.assigned_teachers.all()])
    display_assigned_teachers.short_description = 'Giáo viên nhận'