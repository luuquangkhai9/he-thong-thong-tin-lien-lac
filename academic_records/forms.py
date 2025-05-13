from django import forms
from .models import Score # Score được định nghĩa trong academic_records.models

# Import các model từ các app khác
from accounts.models import StudentProfile, User 
from school_data.models import Class as SchoolClass, Subject as SchoolSubject # Đổi tên để tránh nhầm lẫn

class ScoreContextForm(forms.Form):
    """
    Form để Giáo viên chọn các thông tin chung (context) trước khi nhập điểm.
    """
    school_class = forms.ModelChoiceField(
        queryset=SchoolClass.objects.none(), 
        label="Chọn Lớp học",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--- Chọn Lớp ---"
    )
    subject = forms.ModelChoiceField(
        queryset=SchoolSubject.objects.none(), 
        label="Chọn Môn học",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="--- Chọn Môn ---"
    )
    exam_type = forms.ChoiceField(
        choices=Score.EXAM_TYPE_CHOICES,
        label="Loại Kỳ thi/Kiểm tra",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    exam_date = forms.DateField(
        label="Ngày thi/Kiểm tra",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text="Chọn ngày thi hoặc ngày kiểm tra."
    )
    academic_period = forms.CharField(
        max_length=50,
        required=False, 
        label="Kỳ học/Năm học (VD: HK1 2024-2025)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: HK1 2024-2025'}),
        help_text="Để trống nếu không áp dụng cho kỳ học cụ thể."
    )

    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None) 
        super().__init__(*args, **kwargs)
        
        self.fields['school_class'].queryset = SchoolClass.objects.all().order_by('name')
        self.fields['subject'].queryset = SchoolSubject.objects.all().order_by('name')

        if teacher:
            if hasattr(teacher, 'teacher_profile') and teacher.teacher_profile:
                self.fields['subject'].queryset = teacher.teacher_profile.subjects_taught.all().order_by('name')
                if not self.fields['subject'].queryset.exists():
                     self.fields['subject'].help_text = "Bạn chưa được phân công giảng dạy môn nào."
            else: 
                self.fields['subject'].queryset = SchoolSubject.objects.none()
                self.fields['subject'].help_text = "Không tìm thấy hồ sơ giáo viên hoặc bạn chưa được phân công môn dạy."
        
        if self.data.get('school_class'):
            try:
                selected_class_pk = int(self.data.get('school_class'))
                self.fields['school_class'].initial = selected_class_pk
            except (ValueError, TypeError):
                pass 
        
        if self.data.get('subject'):
            try:
                self.fields['subject'].initial = int(self.data.get('subject'))
            except (ValueError, TypeError):
                pass


class ScoreEntryForm(forms.ModelForm):
    """
    Form cho một mục điểm của một học sinh.
    Sẽ được sử dụng trong modelformset_factory.
    """
    # Fields không phải là một phần của Score model, nhưng cần cho hiển thị/logic
    student_name = forms.CharField(
        label="Học sinh", 
        required=False, 
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext bg-light p-1 border rounded'})
    )
    student_id = forms.IntegerField(widget=forms.HiddenInput(), required=True) # Bắt buộc để biết điểm này của ai

    class Meta:
        model = Score
        fields = ['score_value', 'notes'] # Chỉ các trường của model Score mà người dùng sẽ nhập
        widgets = {
            'score_value': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'min': '0', 'max': '10'}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 1, 'placeholder': 'Ghi chú (nếu có)'}),
        }
        labels = {
            'score_value': 'Điểm',
            'notes': 'Ghi chú',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Nếu form được khởi tạo với một instance Score đã có (khi load điểm cũ để sửa)
        if self.instance and self.instance.pk and self.instance.student:
            self.fields['student_name'].initial = self.instance.student.user.get_full_name() or self.instance.student.user.username
            self.fields['student_id'].initial = self.instance.student.pk
        # Nếu form được khởi tạo với initial data (khi tạo formset cho danh sách học sinh mới)
        # modelformset_factory sẽ truyền initial data vào từng form instance.
        # Các trường của form sẽ tự động lấy giá trị từ self.initial nếu key khớp.
        # Ví dụ, nếu self.initial = {'student_id': X, 'student_name': 'Y'},
        # thì self.fields['student_id'].initial và self.fields['student_name'].initial sẽ được tự động gán.
        # Chúng ta không cần gán lại một cách tường minh ở đây nếu initial data được cung cấp đúng cho formset.
