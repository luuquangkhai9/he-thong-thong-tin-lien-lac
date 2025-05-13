from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Role, TeacherProfile, StudentProfile, ParentProfile # Đảm bảo Role được import

# Inlines for Profiles - để hiển thị và chỉnh sửa profile ngay trong trang User admin
# ... (các import và các lớp Admin khác đã có) ...

class TeacherProfileInline(admin.StackedInline):
    model = TeacherProfile
    can_delete = False
    verbose_name_plural = 'Hồ sơ Giáo viên'
    fk_name = 'user'
    fieldsets = (
        (None, { # Nhóm không có tiêu đề
            'fields': ('teacher_type',)
        }),
        ('Các môn học giảng dạy', { # Nhóm có tiêu đề
            'fields': ('subjects_taught',)
        }),
    )
    filter_horizontal = ('subjects_taught',)


# ... (lớp StudentProfileInline, ParentProfileInline, CustomUserAdmin và các đăng ký khác) ...

# ... (các import và các lớp Admin khác đã có) ...

class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Hồ sơ Học sinh'
    fk_name = 'user'
    # fields = ('date_of_birth', 'gender', 'current_class', 'parent', 'enrolled_subjects') # Cách đơn giản

    # Hoặc dùng fieldsets để nhóm và sử dụng filter_horizontal
    fieldsets = (
        (None, {
            'fields': ('date_of_birth', 'gender')
        }),
        ('Thông tin Học Tập và Gia Đình', {
            'fields': ('current_class', 'parent', 'enrolled_subjects') # Thêm enrolled_subjects
        }),
    )
    # Sử dụng filter_horizontal để dễ chọn nhiều môn học
    filter_horizontal = ('enrolled_subjects',)
    # Giữ lại raw_id_fields hoặc autocomplete_fields cho current_class và parent nếu bạn đã cấu hình
    raw_id_fields = ('current_class', 'parent') # Ví dụ nếu bạn đã dùng raw_id_fields
    # Hoặc autocomplete_fields = ['current_class', 'parent'] nếu đã cấu hình đúng

# ... (lớp CustomUserAdmin và các đăng ký khác) ...

class ParentProfileInline(admin.StackedInline):
    model = ParentProfile
    can_delete = False
    verbose_name_plural = 'Hồ sơ Phụ huynh'
    fk_name = 'user'

# ... (các import đã có) ...

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'role', 'department_name') # Thêm 'department_name'
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'department')}), # Thêm 'department' vào đây
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        # Khi tạo user mới, bạn có muốn cho phép chọn department không?
        # Nếu có, thêm 'department' vào đây. Nếu không, chỉ thêm vào fieldsets (cho việc sửa).
        ('Custom Fields', {'fields': ('role', 'department')}), # Thêm 'department'
    )
    inlines = (TeacherProfileInline, StudentProfileInline, ParentProfileInline,)
    # Thêm filter và autocomplete nếu cần
    list_filter = UserAdmin.list_filter + ('department', 'role') # Thêm department và role vào bộ lọc
    search_fields = UserAdmin.search_fields + ('department__name',) # Cho phép tìm kiếm theo tên department
    autocomplete_fields = ['department', 'role'] # Giúp chọn department và role dễ hơn

    # Phương thức để hiển thị tên department thay vì ID trong list_display
    def department_name(self, obj):
        if obj.department:
            return obj.department.name
        return "-"
    department_name.short_description = 'Phòng Ban' # Tên cột
    department_name.admin_order_field = 'department__name' # Cho phép sắp xếp theo tên phòng ban

    # ... (phần get_inline_instances nếu có) ...

    # Tùy chỉnh để khi xem User, các trường profile cũng hiển thị gọn gàng
    def get_inline_instances(self, request, obj=None):
        if not obj: # Khi tạo user mới, không hiển thị inline nào cả
            return list()
        # Khi xem/sửa user đã có, chỉ hiển thị inline profile phù hợp với vai trò của user đó
        # (Phần này có thể cần logic phức tạp hơn để tự động chọn inline dựa trên user.role)
        # Ví dụ đơn giản: nếu user có role là TEACHER thì hiển thị TeacherProfileInline
        # if obj.role and obj.role.name == 'TEACHER':
        #     return [inline(self.model, self.admin_site) for inline in [TeacherProfileInline] if isinstance(inline, type)] # Check type
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_name_display_custom', 'description') # Hiển thị tên và mô tả
    search_fields = ('name', 'description') # Cho phép tìm kiếm theo name (mã) và description

    def get_name_display_custom(self, obj):
        return obj.get_name_display() # Gọi phương thức get_name_display của model
    get_name_display_custom.short_description = 'Tên Vai trò Hiển thị' # Tên cột trong admin
    get_name_display_custom.admin_order_field = 'name' # Cho phép sắp xếp theo trường 'name'

admin.site.register(User, CustomUserAdmin)

# Không cần đăng ký riêng các Profile model nữa nếu chúng đã là inline
# admin.site.register(TeacherProfile)
# admin.site.register(StudentProfile)
# admin.site.register(ParentProfile)
@admin.register(ParentProfile) # Đăng ký ParentProfile riêng
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'address')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'address') # Quan trọng!
    autocomplete_fields = ['user'] # Nếu bạn muốn chọn User cho ParentProfile bằng autocomplete

    def user_display(self, obj):
        return obj.user.get_full_name() if obj.user.get_full_name() else obj.user.username
    user_display.short_description = "Tài khoản Phụ huynh"
    user_display.admin_order_field = 'user__username'

# Trong accounts/admin.py
from .models import StudentProfile # Đảm bảo đã import

@admin.register(StudentProfile) # Đăng ký StudentProfile riêng
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'date_of_birth', 'gender', 'current_class_name', 'parent_full_name')
    search_fields = ( # Đây là phần quan trọng cho autocomplete_fields ở nơi khác
        'user__username',
        'user__first_name',
        'user__last_name',
        'current_class__name'
    )
    autocomplete_fields = ['user', 'current_class', 'parent'] # autocomplete cho các ForeignKey của chính StudentProfile

    def user_display(self, obj):
        return obj.user.get_full_name() if obj.user.get_full_name() else obj.user.username
    user_display.short_description = 'Học sinh'
    user_display.admin_order_field = 'user__last_name'

    def current_class_name(self, obj):
        return obj.current_class.name if obj.current_class else '-'
    current_class_name.short_description = 'Lớp Hiện Tại'

    def parent_full_name(self, obj):
        if obj.parent and obj.parent.user:
            return obj.parent.user.get_full_name() if obj.parent.user.get_full_name() else obj.parent.user.username
        return '-'
    parent_full_name.short_description = 'Phụ Huynh Chính'