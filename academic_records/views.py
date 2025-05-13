from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Q
from django.forms import modelformset_factory 
from django.urls import reverse
from collections import defaultdict
import json

from .models import Score
from accounts.models import StudentProfile, ParentProfile, User, Role
from school_data.models import Class as SchoolClass, Subject as SchoolSubject
from .forms import ScoreContextForm, ScoreEntryForm

def convert_defaultdict_to_dict(d):
    if isinstance(d, defaultdict):
        return {k: convert_defaultdict_to_dict(v) for k, v in d.items()}
    return d

@login_required
def view_scores(request):
    user = request.user
    context = {
        'page_title': 'Bảng điểm của bạn',
        'scores_by_student_period_subject': {},
        'is_parent': False,
        'students_to_view': [],
        'error_message': None
    }

    user_role_name = None
    if hasattr(user, 'role') and user.role:
        user_role_name = user.role.name
    
    if user_role_name == 'STUDENT':
        try:
            student_profile = user.student_profile
            context['students_to_view'] = [student_profile]
            context['page_title'] = f'Bảng điểm của {student_profile.user.get_full_name() or student_profile.user.username}'
        except StudentProfile.DoesNotExist:
            context['error_message'] = "Không tìm thấy hồ sơ học sinh của bạn."

    elif user_role_name == 'PARENT':
        context['is_parent'] = True
        try:
            parent_profile = ParentProfile.objects.get(user=user)
            children_profiles_qs = parent_profile.children.all().select_related('user')
            
            if not children_profiles_qs.exists():
                context['error_message'] = "Bạn chưa có thông tin học sinh nào được liên kết."
            else:
                students_list = list(children_profiles_qs)
                context['students_to_view'] = students_list
                context['page_title'] = 'Bảng điểm của các con'
        
        except ParentProfile.DoesNotExist:
            context['error_message'] = "Không tìm thấy hồ sơ phụ huynh của bạn."
        except Exception as e:
            context['error_message'] = "Đã có lỗi xảy ra khi truy xuất thông tin phụ huynh."
    else:
        context['error_message'] = "Chức năng này chỉ dành cho Học sinh và Phụ huynh."

    scores_data_defaultdict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    if context['students_to_view']:
        student_profile_pks = [sp.pk for sp in context['students_to_view']]
        scores_qs = Score.objects.filter(student_id__in=student_profile_pks).select_related('subject', 'student__user').order_by('student__user__username', 'academic_period', 'subject__name', 'exam_date')
        
        for score_item in scores_qs:
            student_display_name = score_item.student.user.get_full_name() or score_item.student.user.username
            period = score_item.academic_period or "Chưa xác định kỳ học"
            subject_name = score_item.subject.name
            scores_data_defaultdict[student_display_name][period][subject_name].append(score_item)
            
    context['scores_by_student_period_subject'] = convert_defaultdict_to_dict(scores_data_defaultdict)

    return render(request, 'academic_records/view_scores.html', context)


@login_required
def enter_scores(request):
    teacher = request.user
    if not (hasattr(teacher, 'role') and teacher.role and teacher.role.name == 'TEACHER'):
        raise PermissionDenied("Chức năng này chỉ dành cho Giáo Viên.")

    score_context_form = ScoreContextForm(request.GET or None, teacher=teacher)
    ScoreFormSet_default = modelformset_factory(Score, form=ScoreEntryForm, extra=0) # Default empty formset
    score_formset = ScoreFormSet_default(queryset=Score.objects.none()) 
    
    students_for_scoring = []
    selected_class_id = request.GET.get('school_class')
    selected_subject_id = request.GET.get('subject')
    selected_exam_type = request.GET.get('exam_type')
    selected_exam_date = request.GET.get('exam_date')
    selected_academic_period = request.GET.get('academic_period', "")

    if request.method == 'POST':
        post_selected_class_id = request.POST.get('selected_class_id_hidden')
        post_selected_subject_id = request.POST.get('selected_subject_id_hidden')
        post_selected_exam_type = request.POST.get('selected_exam_type_hidden')
        post_selected_exam_date = request.POST.get('selected_exam_date_hidden')
        post_selected_academic_period = request.POST.get('selected_academic_period_hidden', "")

        # Cập nhật lại score_context_form với các giá trị đã POST để hiển thị lại đúng
        score_context_form = ScoreContextForm(initial={
            'school_class': post_selected_class_id, 'subject': post_selected_subject_id,
            'exam_type': post_selected_exam_type, 'exam_date': post_selected_exam_date,
            'academic_period': post_selected_academic_period
        }, teacher=teacher)

        # Lấy lại danh sách học sinh cho việc render lại formset nếu có lỗi
        if post_selected_class_id:
            target_class = get_object_or_404(SchoolClass, pk=post_selected_class_id)
            students_for_scoring = StudentProfile.objects.filter(current_class=target_class).select_related('user').order_by('user__last_name', 'user__first_name')
        
        # Khởi tạo formset với dữ liệu POST
        ScoreFormSet_post = modelformset_factory(Score, form=ScoreEntryForm, extra=len(students_for_scoring) if students_for_scoring else 0)
        score_formset = ScoreFormSet_post(request.POST, queryset=Score.objects.none()) # queryset rỗng vì dùng update_or_create

        if score_formset.is_valid():
            saved_count = 0
            updated_count = 0
            subject_instance = get_object_or_404(SchoolSubject, pk=post_selected_subject_id)

            for form_in_formset in score_formset:
                if form_in_formset.has_changed() and form_in_formset.cleaned_data.get('score_value') is not None:
                    student_id = form_in_formset.cleaned_data.get('student_id')
                    score_value = form_in_formset.cleaned_data.get('score_value')
                    notes = form_in_formset.cleaned_data.get('notes', '')

                    if student_id:
                        student_profile = get_object_or_404(StudentProfile, pk=student_id)
                        score_entry, created = Score.objects.update_or_create(
                            student=student_profile, subject=subject_instance,
                            exam_type=post_selected_exam_type, exam_date=post_selected_exam_date,
                            academic_period=post_selected_academic_period,
                            defaults={'score_value': score_value, 'notes': notes}
                        )
                        if created: saved_count += 1
                        else: updated_count += 1
            
            if saved_count > 0 or updated_count > 0:
                messages.success(request, f"Đã lưu {saved_count} điểm mới và cập nhật {updated_count} điểm thành công!")
            else:
                messages.info(request, "Không có thay đổi nào được thực hiện hoặc không có điểm nào được nhập.")
            
            redirect_url_params = (f"?school_class={post_selected_class_id}&subject={post_selected_subject_id}"
                                   f"&exam_type={post_selected_exam_type}&exam_date={post_selected_exam_date}"
                                   f"&academic_period={post_selected_academic_period}")
            return redirect(reverse('academic_records:enter_scores') + redirect_url_params)
        else:
            messages.error(request, "Vui lòng kiểm tra lại các lỗi trong bảng điểm.")
            # students_for_scoring đã được lấy ở trên.
            # score_formset (chứa lỗi) sẽ được truyền ra template.
            # Cần đảm bảo template render đúng các form này.

    elif score_context_form.is_valid() and selected_class_id and selected_subject_id and selected_exam_type and selected_exam_date:
        target_class = get_object_or_404(SchoolClass, pk=selected_class_id)
        target_subject = get_object_or_404(SchoolSubject, pk=selected_subject_id)
        
        students_for_scoring = StudentProfile.objects.filter(current_class=target_class).select_related('user').order_by('user__last_name', 'user__first_name')

        initial_data_for_formset = []
        if students_for_scoring.exists():
            for student_profile in students_for_scoring:
                existing_score = Score.objects.filter(
                    student=student_profile, subject=target_subject,
                    exam_type=selected_exam_type, exam_date=selected_exam_date,
                    academic_period=selected_academic_period
                ).first()
                initial_data_for_formset.append({
                    'student_id': student_profile.pk,
                    'student_name': student_profile.user.get_full_name() or student_profile.user.username,
                    'score_value': existing_score.score_value if existing_score else None,
                    'notes': existing_score.notes if existing_score else '',
                })
            
            num_forms_to_create = len(initial_data_for_formset)
            ScoreFormSet_get = modelformset_factory(Score, form=ScoreEntryForm, extra=num_forms_to_create, can_delete=False)
            score_formset = ScoreFormSet_get(queryset=Score.objects.none(), initial=initial_data_for_formset)
        # score_context_form đã được khởi tạo ở đầu với request.GET or None, và đã is_valid()

    context = {
        'score_context_form': score_context_form,
        'score_formset': score_formset,
        'students_for_scoring': students_for_scoring, # Quan trọng để template render tên học sinh
        'selected_class_id': selected_class_id,
        'selected_subject_id': selected_subject_id,
        'selected_exam_type': selected_exam_type,
        'selected_exam_date': selected_exam_date,
        'selected_academic_period': selected_academic_period,
        'page_title': 'Nhập Điểm cho Học sinh'
    }
    return render(request, 'academic_records/enter_scores.html', context)

@login_required
def teacher_view_class_scores(request):
    # ... (code view teacher_view_class_scores giữ nguyên như bản đã dọn dẹp) ...
    teacher = request.user
    if not (hasattr(teacher, 'role') and teacher.role and teacher.role.name == 'TEACHER'):
        raise PermissionDenied("Chức năng này chỉ dành cho Giáo viên.")

    homeroom_classes = SchoolClass.objects.filter(homeroom_teacher=teacher)
    
    selected_class_pk_from_get = request.GET.get('class_to_view')
    active_class = None
    
    if selected_class_pk_from_get:
        active_class = get_object_or_404(SchoolClass, pk=selected_class_pk_from_get, homeroom_teacher=teacher)
    elif homeroom_classes.exists():
        active_class = homeroom_classes.first()

    students_in_class = []
    scores_data_defaultdict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    if active_class:
        students_in_class = StudentProfile.objects.filter(current_class=active_class).select_related('user').order_by('user__last_name', 'user__first_name')
        if students_in_class.exists():
            student_pks = [sp.pk for sp in students_in_class]
            scores_qs = Score.objects.filter(student_id__in=student_pks).select_related('subject', 'student__user').order_by('student__user__last_name', 'student__user__first_name', 'academic_period', 'subject__name', 'exam_date')
            
            for score_item in scores_qs:
                student_display_name = score_item.student.user.get_full_name() or score_item.student.user.username
                period = score_item.academic_period or "Chưa xác định kỳ học"
                subject_name = score_item.subject.name
                scores_data_defaultdict[student_display_name][period][subject_name].append(score_item)
    else:
        if homeroom_classes.exists():
             messages.info(request, "Vui lòng chọn một lớp chủ nhiệm để xem điểm.")
        else:
            messages.info(request, "Bạn hiện không chủ nhiệm lớp nào để xem điểm.")

    context = {
        'page_title': f'Bảng điểm Lớp {active_class.name}' if active_class else 'Xem Điểm Lớp Chủ Nhiệm',
        'active_class': active_class,
        'homeroom_classes': homeroom_classes,
        'scores_by_student_period_subject': convert_defaultdict_to_dict(scores_data_defaultdict),
        'students_in_class': students_in_class 
    }
    return render(request, 'academic_records/teacher_view_class_scores.html', context)
