from django.db import models
from django.conf import settings # Để tham chiếu đến Custom User Model một cách an toàn
# from accounts.models import Role # Hoặc dùng string 'accounts.Role'
# from school_data.models import Class, Department # Hoặc dùng string
from django.utils import timezone
# Create your models here.
class Notification(models.Model):
    # ERD: notice_id (PK - Django tự tạo)
    # ERD: title, content, created_time, send_by, status

    STATUS_CHOICES = [
        ('DRAFT', 'Bản nháp'),
        ('SENT', 'Đã gửi'),
        ('READ', 'Đã xem'), # Có thể cần một bảng trung gian để theo dõi trạng thái đọc cho từng người nhận
        ('ARCHIVED', 'Đã lưu trữ'),
    ]

    title = models.CharField(max_length=255, verbose_name="Tiêu đề")
    content = models.TextField(verbose_name="Nội dung")
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo")
    # Người gửi thông báo: Liên kết đến Custom User Model của bạn
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, # Tham chiếu an toàn đến User model
        on_delete=models.SET_NULL, # Nếu người gửi bị xóa, thông báo vẫn còn nhưng không rõ người gửi
        null=True,
        blank=True, # Có thể là thông báo hệ thống không có người gửi cụ thể
        related_name='sent_notifications',
        verbose_name="Người gửi"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT', verbose_name="Trạng thái")
    publish_time = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian gửi dự kiến") # Thời điểm thông báo sẽ được gửi đi

    # ERD: send_to - Cách xử lý người nhận (recipients)
    # Chúng ta sẽ cho phép thông báo được gửi đến nhiều nhóm đối tượng khác nhau.
    # Một thông báo có thể gửi đến nhiều người dùng, nhiều vai trò, nhiều lớp, hoặc nhiều phòng ban.

    # Trường hợp gửi đến người dùng cụ thể:
    target_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='received_notifications', # Từ User, có thể xem các thông báo họ nhận
        blank=True,
        verbose_name="Người nhận cụ thể"
    )

    # Trường hợp gửi đến các vai trò:
    target_roles = models.ManyToManyField(
        'accounts.Role', # Tham chiếu đến Role model trong app 'accounts'
        related_name='role_notifications', # Từ Role, có thể xem các thông báo gửi cho vai trò đó
        blank=True,
        verbose_name="Gửi đến Vai trò"
    )

    # Trường hợp gửi đến các lớp học:
    target_classes = models.ManyToManyField(
        'school_data.Class', # Tham chiếu đến Class model trong app 'school_data'
        related_name='class_notifications', # Từ Class, có thể xem các thông báo gửi cho lớp đó
        blank=True,
        verbose_name="Gửi đến Lớp học"
    )

    # Trường hợp gửi đến các phòng ban:
    # target_departments = models.ManyToManyField(
    #     'school_data.Department',
    #     related_name='department_notifications',
    #     blank=True,
    #     verbose_name="Gửi đến Phòng Ban"
    # )
    # (Bạn có thể thêm target_departments nếu cần thiết dựa trên yêu cầu)

    # Để biết thông báo này đã được thực sự gửi đi chưa (ngoài status='SENT')
    is_published = models.BooleanField(default=False, verbose_name="Đã phát hành")


    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Thông báo"
        verbose_name_plural = "Các Thông báo"
        ordering = ['-created_time'] # Sắp xếp mặc định theo thời gian tạo mới nhất lên đầu

# ... (các import và model Notification đã có ở trên) ...

class Conversation(models.Model):
    # ERD: conversation_id (PK - Django tự tạo), title, created_at, type
    CONVERSATION_TYPE_CHOICES = [
        ('DIRECT', 'Trò chuyện trực tiếp (1-1)'),
        ('GROUP', 'Trò chuyện nhóm'),
    ]

    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Tiêu đề cuộc hội thoại (cho nhóm)")
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
        verbose_name="Thành viên tham gia"
    )
    conversation_type = models.CharField(
        max_length=10,
        choices=CONVERSATION_TYPE_CHOICES,
        default='DIRECT',
        verbose_name="Loại cuộc hội thoại"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối") # Thời gian của tin nhắn cuối cùng

    def __str__(self):
        if self.conversation_type == 'GROUP' and self.title:
            return self.title
        elif self.conversation_type == 'DIRECT':
            # Cố gắng hiển thị tên của 2 người tham gia cho chat 1-1
            # Điều này có thể cần logic phức tạp hơn nếu bạn muốn loại trừ người dùng hiện tại
            # và chỉ hiển thị người còn lại.
            # Hoặc bạn có thể có một phương thức để lấy "tên hiển thị" của cuộc hội thoại.
            participant_names = ", ".join([user.username for user in self.participants.all()[:2]]) # Lấy 2 người đầu tiên
            return f"Trò chuyện giữa: {participant_names}"
        return f"Cuộc hội thoại ID: {self.id}"

    class Meta:
        verbose_name = "Cuộc hội thoại"
        verbose_name_plural = "Các Cuộc hội thoại"
        ordering = ['-updated_at'] # Sắp xếp theo thời gian cập nhật mới nhất

class Message(models.Model):
    # ERD: message_id (PK), sender_role, name (của sender), content, sent_at
    # Chúng ta sẽ dùng ForeignKey đến User cho sender để có đầy đủ thông tin.
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE, # Nếu cuộc hội thoại bị xóa, tất cả tin nhắn trong đó cũng bị xóa
        related_name='messages', # Từ Conversation, truy cập: cuoc_hoi_thoai.messages.all()
        verbose_name="Thuộc cuộc hội thoại"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Nếu người gửi bị xóa, tin nhắn vẫn còn nhưng không rõ người gửi
        null=True, # Cho phép sender là NULL (ví dụ: tin nhắn hệ thống trong cuộc hội thoại)
        related_name='sent_messages_in_conversation', # Đổi tên related_name để tránh xung đột nếu User có related_name 'sent_messages' khác
        verbose_name="Người gửi"
    )
    content = models.TextField(verbose_name="Nội dung tin nhắn")
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian gửi")
    # Việc theo dõi trạng thái "đã đọc" cho từng người trong group chat khá phức tạp.
    # Ban đầu, chúng ta có thể bỏ qua hoặc chỉ làm đơn giản cho chat 1-1.
    # read_by_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='read_messages', blank=True)
    # Bên trong model Message
# from django.utils import timezone # Thêm import này ở đầu file models.py

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs) # Gọi phương thức save gốc trước
        # Cập nhật trường updated_at của cuộc hội thoại cha
        if self.conversation:
            self.conversation.updated_at = timezone.now() # Hoặc self.sent_at nếu muốn chính xác hơn
            self.conversation.save(update_fields=['updated_at'])

    def __str__(self):
        return f"Tin nhắn từ {self.sender.username if self.sender else 'Hệ thống'} lúc {self.sent_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = "Tin nhắn"
        verbose_name_plural = "Các Tin nhắn"
        ordering = ['sent_at'] # Sắp xếp tin nhắn theo thời gian gửi

# ... (các import và model Notification, Conversation, Message đã có ở trên) ...
# from school_data.models import Department # Hoặc dùng string
# from accounts.models import StudentProfile # Hoặc dùng string

from django.db import models
from django.conf import settings # Để tham chiếu đến Custom User Model
# from accounts.models import Role, StudentProfile (nếu bạn dùng trực tiếp)
# from school_data.models import Class, Department (nếu bạn dùng trực tiếp)
from django.utils import timezone # Thêm import này nếu bạn dùng timezone.now() trong model Message

# ... (model Notification, Conversation, Message đã có ở trên) ...

class RequestForm(models.Model):
    FORM_TYPE_CHOICES = [
        ('LEAVE_APPLICATION', 'Đơn xin nghỉ học'),
        ('GRADE_APPEAL', 'Đơn phúc khảo điểm'),
        ('GENERAL_REQUEST', 'Kiến nghị/Đề xuất chung'),
        ('FEEDBACK', 'Góp ý'),
    ]

    STATUS_CHOICES = [
        ('SUBMITTED', 'Mới gửi'),
        ('PROCESSING', 'Đang xử lý'),
        ('RESOLVED', 'Đã giải quyết'),
        ('REJECTED', 'Đã từ chối'),
        ('CLOSED', 'Đã đóng'),
    ]

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submitted_forms',
        verbose_name="Người gửi"
    )
    related_student = models.ForeignKey(
        'accounts.StudentProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_request_forms',
        verbose_name="Học sinh liên quan (nếu có)"
    )
    form_type = models.CharField(max_length=50, choices=FORM_TYPE_CHOICES, verbose_name="Loại đơn")
    title = models.CharField(max_length=255, verbose_name="Tiêu đề đơn/kiến nghị")
    content = models.TextField(verbose_name="Nội dung chi tiết")
    submission_date = models.DateTimeField(auto_now_add=True, verbose_name="Ngày gửi")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED', verbose_name="Trạng thái")

    assigned_department = models.ForeignKey(
        'school_data.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Cho phép không chọn phòng ban (nếu gửi cho giáo viên)
        related_name='assigned_request_forms',
        verbose_name="Phòng Ban xử lý"
    )

    # --- THÊM TRƯỜNG MỚI assigned_teachers VÀO ĐÂY ---
    assigned_teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='received_request_forms', # Các đơn mà giáo viên này nhận/xử lý
        blank=True, # Cho phép không chọn giáo viên (nếu gửi cho phòng ban)
        limit_choices_to={'role__name': 'TEACHER'}, # Chỉ những User có vai trò là Giáo viên
        verbose_name="Giáo viên xử lý/nhận đơn"
    )
    # --- KẾT THÚC PHẦN THÊM MỚI ---

    response_content = models.TextField(blank=True, null=True, verbose_name="Nội dung phản hồi từ nhà trường")
    response_date = models.DateTimeField(null=True, blank=True, verbose_name="Ngày phản hồi")
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responded_request_forms', # Đổi tên related_name này để tránh xung đột với assigned_teachers
        limit_choices_to={'is_staff': True},
        verbose_name="Người phản hồi"
    )

    def __str__(self):
        return f"{self.get_form_type_display()} từ {self.submitted_by.username} - {self.title}"

    class Meta:
        verbose_name = "Đơn từ/Kiến nghị"
        verbose_name_plural = "Các Đơn từ/Kiến nghị"
        ordering = ['-submission_date']