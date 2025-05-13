from django.db import models
from django.contrib.auth.models import AbstractUser

class Role(models.Model):
    # Dựa trên ERD: role_id (PK - Django tự tạo), name, permission
    # Chúng ta có thể đơn giản hóa 'permission' ban đầu, hoặc để sau
    ROLE_CHOICES = [
        ('ADMIN', 'Quản trị viên Hệ thống (Admin)'), # Thường là từ Phòng CNTT
        ('SCHOOL_ADMIN', 'Quản lý Trường (Phòng Ban khác)'),
        ('TEACHER', 'Giáo viên'),
        ('PARENT', 'Phụ huynh'),
        ('STUDENT', 'Học sinh'),
    ]
    name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True, primary_key=True) # Đặt name làm PK và unique
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả vai trò")

    def __str__(self):
        return self.get_name_display() # Hiển thị tên đầy đủ của choice

class User(AbstractUser):
    # Kế thừa AbstractUser sẽ có sẵn: username, password, email, first_name, last_name, is_staff, is_active, is_superuser, date_joined, last_login
    # Thêm các trường tùy chỉnh dựa trên ERD (USER: status) và liên kết với Role
    # Trường 'status' có thể được quản lý bởi 'is_active' của AbstractUser hoặc thêm trường riêng nếu cần trạng thái phức tạp hơn.

    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vai trò")
    # Các trường thông tin chung khác có thể có cho tất cả user nếu cần, ví dụ:
    # phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Số điện thoại")
    # avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Ảnh đại diện")
    # --- THÊM TRƯỜNG MỚI Ở ĐÂY ---
    department = models.ForeignKey(
        'school_data.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Không phải tất cả user đều thuộc về một phòng ban (VD: Học sinh, Phụ huynh)
        related_name='staff_members', # Từ Department, có thể truy cập ds nhân viên: phong_ban.staff_members.all()
        verbose_name="Phòng Ban Công tác (nếu có)"
    )

    # Bạn có thể thêm các trường khác như 'status' nếu 'is_active' không đủ
    # status = models.CharField(max_length=50, blank=True, null=True)


    def __str__(self):
        return self.username
    
# ... (các import và model Role, User đã có ở trên) ...

# ... (các import và model Role, User đã có ở trên) ...
# from school_data.models import Subject # Hoặc dùng string 'school_data.Subject'

class TeacherProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='teacher_profile')
    TEACHER_TYPE_CHOICES = [
        ('HEAD_TEACHER', 'Giáo viên Chủ nhiệm'),
        ('SUBJECT_TEACHER', 'Giáo viên Bộ môn'),
        ('STAFF', 'Nhân viên Phòng Ban'),
    ]
    teacher_type = models.CharField(max_length=20, choices=TEACHER_TYPE_CHOICES, null=True, blank=True, verbose_name="Loại giáo viên/nhân viên")

    # --- THÊM TRƯỜNG MỚI Ở ĐÂY ---
    subjects_taught = models.ManyToManyField(
        'school_data.Subject', # Sử dụng string 'app_name.ModelName'
        blank=True, # Giáo viên có thể (tạm thời) chưa được phân công dạy môn nào
        related_name='teachers', # Từ một Subject, có thể truy cập ds giáo viên: mon_hoc.teachers.all()
        verbose_name="Các Môn học Giảng dạy"
    )
    # --- KẾT THÚC PHẦN THÊM MỚI ---

    def __str__(self):
        # Hiển thị tên các môn học nếu có
        subject_names = ", ".join([subject.name for subject in self.subjects_taught.all()])
        if subject_names:
            return f"GV: {self.user.username} (Dạy: {subject_names})"
        return f"GV: {self.user.username}"

# ... (các model StudentProfile, ParentProfile đã có ở dưới) ...
class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='student_profile')
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Ngày sinh")
    GENDER_CHOICES = [
        ('MALE', 'Nam'),
        ('FEMALE', 'Nữ'),
        ('OTHER', 'Khác'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True, verbose_name="Giới tính")
    current_class = models.ForeignKey(
        'school_data.Class',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name="Lớp Hiện Tại"
    )
    parent = models.ForeignKey(
        'ParentProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Phụ Huynh Chính"
    )

    # --- THÊM TRƯỜNG MỚI Ở ĐÂY ---
    enrolled_subjects = models.ManyToManyField(
        'school_data.Subject',
        blank=True, # Học sinh có thể (tạm thời) chưa đăng ký môn nào
        related_name='enrolled_students', # Từ một Subject, có thể truy cập ds học sinh: mon_hoc.enrolled_students.all()
        verbose_name="Các Môn học Đã đăng ký/Học"
    )
    # --- KẾT THÚC PHẦN THÊM MỚI ---

    def __str__(self):
        return f"Hồ sơ Học sinh: {self.user.username}"

class ParentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='parent_profile')
    # ERD: address
    address = models.TextField(blank=True, null=True, verbose_name="Địa chỉ")
    # phone_number (nếu khác với User.phone_number)
    # email (nếu khác với User.email)
    # Mối quan hệ với Student (một phụ huynh có thể có nhiều con) sẽ được xử lý sau.

    def __str__(self):
        return f"Hồ sơ Phụ huynh: {self.user.username}"