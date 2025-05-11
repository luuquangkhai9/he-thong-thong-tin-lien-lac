from django.db import models
# Import User model từ app accounts nếu cần liên kết (ví dụ: Giáo viên chủ nhiệm)
# from accounts.models import User # Hoặc TeacherProfile nếu cụ thể hơn
# Để đơn giản, chúng ta sẽ dùng string 'accounts.User' hoặc 'accounts.TeacherProfile' cho ForeignKey
# để tránh circular imports ban đầu.

class Department(models.Model):
    # ERD: department_id (PK - Django tự tạo), name, email
    name = models.CharField(max_length=255, unique=True, verbose_name="Tên Phòng Ban")
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Email Phòng Ban")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    # Có thể thêm trường liên kết với người đứng đầu phòng ban (User có vai trò SCHOOL_ADMIN) sau.

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Phòng Ban"
        verbose_name_plural = "Các Phòng Ban"

class Class(models.Model):
    # ERD: class_id (PK - Django tự tạo), class_name
    # ERD: Mối quan hệ "is homeroom teacher" (1:N) từ TEACHER đến CLASS
    name = models.CharField(max_length=100, unique=True, verbose_name="Tên Lớp học")
    # Giáo viên chủ nhiệm: Liên kết đến TeacherProfile hoặc User có vai trò Giáo viên
    # Sử dụng string 'app_label.ModelName' để tránh circular import
    homeroom_teacher = models.ForeignKey(
        'accounts.User', # Hoặc 'accounts.TeacherProfile' nếu bạn muốn liên kết trực tiếp với profile giáo viên
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='homeroom_classes',
        verbose_name="Giáo viên Chủ nhiệm",
        # Giới hạn lựa chọn chỉ những User có vai trò là Giáo viên
        limit_choices_to={'role__name': 'TEACHER'} # Giả sử Role model có trường name với value 'TEACHER'
    )
    academic_year = models.CharField(max_length=9, blank=True, null=True, verbose_name="Năm học (VD: 2024-2025)")
    # Sau này sẽ thêm liên kết với Học sinh (ví dụ: một Lớp có nhiều Học sinh)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Lớp học"
        verbose_name_plural = "Các Lớp học"
        unique_together = ('name', 'academic_year') # Đảm bảo tên lớp là duy nhất trong một năm học

class Subject(models.Model):
    # ERD: subject_id (PK - Django tự tạo), name
    name = models.CharField(max_length=150, unique=True, verbose_name="Tên Môn học")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả Môn học")
    # Sau này sẽ thêm liên kết N:M với Giáo viên (Giáo viên dạy Môn học)
    # và Học sinh (Học sinh học Môn học)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Môn học"
        verbose_name_plural = "Các Môn học"