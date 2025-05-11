from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Role, TeacherProfile, StudentProfile, ParentProfile

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
    # Thêm các trường bạn muốn hiển thị và chỉnh sửa trong inline
    fields = ('date_of_birth', 'gender', 'current_class', 'parent') # Thêm 'current_class' và 'parent'

# ... (lớp CustomUserAdmin và các đăng ký khác) ...

class ParentProfileInline(admin.StackedInline):
    model = ParentProfile
    can_delete = False
    verbose_name_plural = 'Hồ sơ Phụ huynh'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'role')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role',)}),
    )
    # Thêm các inlines vào User admin
    inlines = (TeacherProfileInline, StudentProfileInline, ParentProfileInline,)

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


admin.site.register(Role)
admin.site.register(User, CustomUserAdmin)

# Không cần đăng ký riêng các Profile model nữa nếu chúng đã là inline
# admin.site.register(TeacherProfile)
# admin.site.register(StudentProfile)
# admin.site.register(ParentProfile)
