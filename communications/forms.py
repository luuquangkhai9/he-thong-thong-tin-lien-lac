from django import forms
from .models import RequestForm # RequestForm từ .models
from accounts.models import StudentProfile, User # StudentProfile, User từ accounts.models
from school_data.models import Department # Department từ school_data.models

class RequestFormSubmissionForm(forms.ModelForm):
    # ... (code của form này đã có) ...
    related_student_for_parent = forms.ModelChoiceField(
        queryset=StudentProfile.objects.none(), 
        required=False,
        label="Học sinh liên quan (nếu bạn là Phụ huynh)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    assigned_department = forms.ModelChoiceField(
        queryset=Department.objects.all().order_by('name'),
        required=False, 
        label="Gửi đến Phòng Ban",
        empty_label="--- Chọn Phòng Ban (Tùy chọn) ---",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    assigned_teachers = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role__name='TEACHER', is_active=True).select_related('role').order_by('last_name', 'first_name'),
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
        required=False,
        label="Hoặc/Và Gửi đến Giáo viên (chọn một hoặc nhiều)",
        help_text="Bạn có thể chọn gửi đơn này cho Phòng Ban và/hoặc một hoặc nhiều Giáo viên."
    )
    class Meta:
        model = RequestForm
        fields = ['form_type', 'title', 'content', 'related_student_for_parent', 'assigned_department', 'assigned_teachers']
        widgets = {
            'form_type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tiêu đề đơn...'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Nhập nội dung chi tiết...'}),
        }
        labels = {
            'form_type': 'Loại đơn/kiến nghị',
            'title': 'Tiêu đề',
            'content': 'Nội dung chi tiết',
        }
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, 'role') and user.role and user.role.name == 'PARENT':
            if hasattr(user, 'parent_profile') and user.parent_profile:
                self.fields['related_student_for_parent'].queryset = user.parent_profile.children.select_related('user').order_by('user__first_name', 'user__last_name')
                self.fields['related_student_for_parent'].label = "Chọn học sinh liên quan (con của bạn)"
            else:
                self.fields['related_student_for_parent'].queryset = StudentProfile.objects.none()
                self.fields['related_student_for_parent'].widget.attrs['disabled'] = True
                self.fields['related_student_for_parent'].help_text = "Bạn cần cập nhật hồ sơ phụ huynh để chọn học sinh."
        else:
            if 'related_student_for_parent' in self.fields:
                 del self.fields['related_student_for_parent']
    def clean(self):
        cleaned_data = super().clean()
        assigned_department = cleaned_data.get('assigned_department')
        assigned_teachers = cleaned_data.get('assigned_teachers')
        if not assigned_department and not assigned_teachers:
            raise forms.ValidationError(
                "Bạn phải chọn ít nhất một Phòng Ban hoặc một Giáo viên để gửi đơn đến.",
                code='no_recipient'
            )
        return cleaned_data


# --- ĐẢM BẢO LỚP NÀY ĐÃ CÓ TRONG FILE communications/forms.py ---
class RequestFormResponseForm(forms.ModelForm):
    class Meta:
        model = RequestForm
        fields = ['status', 'response_content']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'response_content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Nhập nội dung phản hồi...'}),
        }
        labels = {
            'status': 'Cập nhật Trạng thái Đơn',
            'response_content': 'Nội dung Phản hồi',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed_statuses = [
            ('PROCESSING', 'Đang xử lý'),
            ('RESOLVED', 'Đã giải quyết'),
            ('REJECTED', 'Đã từ chối'),
            ('CLOSED', 'Đã đóng'),
        ]
        self.fields['status'].choices = [choice for choice in allowed_statuses if choice[0] in dict(RequestForm.STATUS_CHOICES).keys()]
        if self.instance and self.instance.pk and self.instance.status == 'SUBMITTED':
             self.fields['status'].initial = 'PROCESSING'
# --- KẾT THÚC ĐỊNH NGHĨA RequestFormResponseForm ---