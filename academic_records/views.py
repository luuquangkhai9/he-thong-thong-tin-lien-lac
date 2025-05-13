from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Q, Max
from django.forms import modelformset_factory 
from django.urls import reverse
from collections import defaultdict
import json 

from .models import Score, RewardAndDiscipline, Evaluation # Đảm bảo Evaluation được import
from accounts.models import StudentProfile, ParentProfile, User, Role
from school_data.models import Class as SchoolClass, Subject as SchoolSubject, Department
from .forms import ScoreContextForm, ScoreEntryForm, RewardAndDisciplineForm, EvaluationForm # Đảm bảo EvaluationForm được import

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
    user_role_name = getattr(user.role, 'name', None) if hasattr(user, 'role') else None
    
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
                context['students_to_view'] = list(children_profiles_qs)
                context['page_title'] = 'Bảng điểm của các con'
        except ParentProfile.DoesNotExist:
            context['error_message'] = "Không tìm thấy hồ sơ phụ huynh của bạn."
        except Exception:
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
    # ... (code enter_scores không thay đổi so với phiên bản hoạt động gần nhất) ...
    teacher = request.user
    if not (hasattr(teacher, 'role') and teacher.role and teacher.role.name == 'TEACHER'):
        raise PermissionDenied("Chức năng này chỉ dành cho Giáo Viên.")

    score_context_form = ScoreContextForm(request.GET or None, teacher=teacher)
    ScoreFormSet_default = modelformset_factory(Score, form=ScoreEntryForm, extra=0)
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

        score_context_form = ScoreContextForm(initial={
            'school_class': post_selected_class_id, 'subject': post_selected_subject_id,
            'exam_type': post_selected_exam_type, 'exam_date': post_selected_exam_date,
            'academic_period': post_selected_academic_period
        }, teacher=teacher)

        if post_selected_class_id:
            target_class = get_object_or_404(SchoolClass, pk=post_selected_class_id)
            students_for_scoring = StudentProfile.objects.filter(current_class=target_class).select_related('user').order_by('user__last_name', 'user__first_name')
        
        num_forms_for_post = len(students_for_scoring) if students_for_scoring else 0
        ScoreFormSet_post = modelformset_factory(Score, form=ScoreEntryForm, extra=num_forms_for_post, can_delete=False)
        score_formset = ScoreFormSet_post(request.POST, queryset=Score.objects.none())

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
        
    context = {
        'score_context_form': score_context_form,
        'score_formset': score_formset,
        'students_for_scoring': students_for_scoring,
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
    # ... (code teacher_view_class_scores không thay đổi) ...
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

@login_required
def view_reward_discipline(request):
    # ... (code view_reward_discipline không thay đổi) ...
    user = request.user
    context = {
        'page_title': 'Khen thưởng và Kỷ luật',
        'records_by_student': defaultdict(list), 
        'is_parent': False,
        'students_to_view': [], 
        'error_message': None
    }

    user_role_name = getattr(user.role, 'name', None) if hasattr(user, 'role') else None
    
    if user_role_name == 'STUDENT':
        try:
            student_profile = user.student_profile
            context['students_to_view'] = [student_profile]
            context['page_title'] = f'Khen thưởng/Kỷ luật của {student_profile.user.get_full_name() or student_profile.user.username}'
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
                context['students_to_view'] = list(children_profiles_qs)
                context['page_title'] = 'Khen thưởng/Kỷ luật của các con'
        except ParentProfile.DoesNotExist:
            context['error_message'] = "Không tìm thấy hồ sơ phụ huynh của bạn."
    else:
        context['error_message'] = "Chức năng này chỉ dành cho Học sinh và Phụ huynh."

    if context['students_to_view']:
        student_pks = [sp.pk for sp in context['students_to_view']]
        records_qs = RewardAndDiscipline.objects.filter(
            student_id__in=student_pks
        ).select_related('student__user', 'issued_by').order_by('student__user__username', '-date_issued')
        
        for record in records_qs:
            student_display_name = record.student.user.get_full_name() or record.student.user.username
            context['records_by_student'][student_display_name].append(record)
    context['records_by_student'] = dict(context['records_by_student'])
    return render(request, 'academic_records/view_reward_discipline.html', context)

@login_required
def manage_reward_discipline_record(request, pk=None):
    # ... (code manage_reward_discipline_record với redirect đã sửa) ...
    user = request.user
    allowed_roles = ['TEACHER', 'SCHOOL_ADMIN', 'ADMIN']
    user_role_name = getattr(user.role, 'name', None) if hasattr(user, 'role') else None

    can_manage = False
    # User phải là staff HOẶC là TEACHER để có thể vào view này
    if user.is_staff and user_role_name in allowed_roles: # Admin, School Admin (staff)
        can_manage = True
    elif user_role_name == 'TEACHER': # Giáo viên có thể không phải là staff nhưng vẫn có quyền này
        can_manage = True 
    
    # Logic kiểm tra quyền chi tiết hơn cho TEACHER khi sửa
    if pk and user_role_name == 'TEACHER':
        record_to_check = get_object_or_404(RewardAndDiscipline, pk=pk)
        is_homeroom_teacher_of_student = False
        if record_to_check.student and record_to_check.student.current_class:
            is_homeroom_teacher_of_student = record_to_check.student.current_class.homeroom_teacher == user
        is_creator = record_to_check.issued_by == user
        if not (is_homeroom_teacher_of_student or is_creator):
            can_manage = False # Ghi đè nếu không đủ quyền cụ thể

    if not can_manage:
        raise PermissionDenied("Bạn không có quyền thực hiện hành động này.")

    instance = None
    if pk:
        instance = get_object_or_404(RewardAndDiscipline, pk=pk)

    if request.method == 'POST':
        form = RewardAndDisciplineForm(request.POST, instance=instance, requesting_user=user)
        if form.is_valid():
            new_record = form.save(commit=False)
            if not new_record.pk: 
                new_record.issued_by = user
            new_record.save()
            messages.success(request, f"Đã {'cập nhật' if pk else 'tạo mới'} mục khen thưởng/kỷ luật thành công.")
            
            if user_role_name == 'TEACHER':
                return redirect('academic_records:teacher_view_class_rewards_discipline')
            else: 
                return redirect('academic_records:school_wide_reward_discipline_list')
    else:
        form = RewardAndDisciplineForm(instance=instance, requesting_user=user)

    context = {
        'form': form,
        'page_title': f"{'Chỉnh sửa' if pk else 'Tạo mới'} Khen thưởng/Kỷ luật",
        'record_instance': instance
    }
    return render(request, 'academic_records/manage_reward_discipline_record.html', context)

@login_required
def teacher_view_class_rewards_discipline(request):
    # ... (code teacher_view_class_rewards_discipline không thay đổi) ...
    teacher = request.user
    if not (hasattr(teacher, 'role') and teacher.role and teacher.role.name == 'TEACHER'):
        raise PermissionDenied("Chức năng này chỉ dành cho Giáo viên.")

    homeroom_classes = SchoolClass.objects.filter(homeroom_teacher=teacher)
    
    selected_class_pk_from_get = request.GET.get('class_to_view')
    active_class = None
    records_in_class = RewardAndDiscipline.objects.none()

    if selected_class_pk_from_get:
        active_class = get_object_or_404(SchoolClass, pk=selected_class_pk_from_get, homeroom_teacher=teacher)
    elif homeroom_classes.exists():
        active_class = homeroom_classes.first()

    if active_class:
        students_in_class_pks = StudentProfile.objects.filter(current_class=active_class).values_list('pk', flat=True)
        records_in_class = RewardAndDiscipline.objects.filter(student_id__in=students_in_class_pks).select_related('student__user', 'issued_by').order_by('-date_issued')
    else:
        if homeroom_classes.exists():
             messages.info(request, "Vui lòng chọn một lớp chủ nhiệm để xem.")
        else:
            messages.info(request, "Bạn hiện không chủ nhiệm lớp nào.")
            
    context = {
        'page_title': f'Khen thưởng/Kỷ luật Lớp {active_class.name}' if active_class else 'Khen thưởng/Kỷ luật Lớp Chủ Nhiệm',
        'active_class': active_class,
        'homeroom_classes': homeroom_classes,
        'records_in_class': records_in_class
    }
    return render(request, 'academic_records/teacher_view_class_rewards_discipline.html', context)

@login_required
def school_wide_reward_discipline_list(request):
    # ... (code school_wide_reward_discipline_list không thay đổi) ...
    user = request.user
    allowed_roles_for_school_wide_view = ['SCHOOL_ADMIN', 'ADMIN'] 
    
    can_view = False
    user_role_name = getattr(user.role, 'name', None) if hasattr(user, 'role') else None

    if user_role_name in allowed_roles_for_school_wide_view and user.is_staff: # Thêm user.is_staff
        can_view = True
    elif user.is_staff and hasattr(user, 'department') and user.department:
        can_view = True
        
    if not can_view:
        raise PermissionDenied("Bạn không có quyền truy cập trang này.")

    all_records_qs = RewardAndDiscipline.objects.all().select_related(
        'student__user', 
        'student__current_class', 
        'issued_by'
    ).order_by('-date_issued', 'student__user__last_name')

    context = {
        'all_records': all_records_qs,
        'page_title': 'Tổng hợp Khen thưởng/Kỷ luật Toàn trường',
    }
    return render(request, 'academic_records/school_wide_reward_discipline_list.html', context)

# === VIEW MỚI CHO GIÁO VIÊN TẠO/SỬA ĐÁNH GIÁ ===
@login_required
def create_edit_evaluation(request, pk=None):
    user = request.user
    allowed_roles = ['TEACHER', 'SCHOOL_ADMIN', 'ADMIN']
    user_role_name = getattr(user.role, 'name', None) if hasattr(user, 'role') else None

    can_manage = False
    if user_role_name in allowed_roles and user.is_staff:
        can_manage = True
    
    if not can_manage:
        # Thêm kiểm tra cụ thể cho TEACHER nếu họ không phải staff nhưng có vai trò TEACHER
        if not (user_role_name == 'TEACHER'):
             raise PermissionDenied("Bạn không có quyền thực hiện hành động này.")
        # Nếu là TEACHER, sẽ kiểm tra quyền sửa cụ thể hơn ở dưới nếu pk tồn tại

    instance = None
    if pk:
        instance = get_object_or_404(Evaluation, pk=pk)
        if instance.evaluator != user and not (user_role_name in ['SCHOOL_ADMIN', 'ADMIN'] and user.is_staff):
            # Giáo viên chỉ được sửa đánh giá của chính mình, trừ khi là admin/school_admin
            raise PermissionDenied("Bạn không có quyền sửa đánh giá này.")
    
    if request.method == 'POST':
        form = EvaluationForm(request.POST, instance=instance, requesting_user=user)
        if form.is_valid():
            evaluation = form.save(commit=False)
            if not evaluation.pk: 
                evaluation.evaluator = user # Gán người đánh giá nếu tạo mới
            evaluation.evaluation_date = timezone.now() # Luôn cập nhật/đặt ngày đánh giá là hiện tại
            evaluation.save()
            messages.success(request, f"Đã {'cập nhật' if pk else 'tạo mới'} đánh giá/nhận xét thành công.")
            
            # Chuyển hướng đến đâu?
            # Có thể là danh sách đánh giá của học sinh đó (nếu có view đó)
            # Hoặc danh sách đánh giá giáo viên đã tạo (cần view riêng)
            # Tạm thời về trang chủ
            if evaluation.student:
                # return redirect('some_url_to_view_student_evaluations', student_pk=evaluation.student.pk)
                pass # Placeholder
            return redirect('homepage') 
    else:
        form = EvaluationForm(instance=instance, requesting_user=user)

    context = {
        'form': form,
        'page_title': f"{'Chỉnh sửa' if pk else 'Tạo mới'} Đánh giá/Nhận xét",
        'evaluation_instance': instance
    }
    return render(request, 'academic_records/create_edit_evaluation.html', context)

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages # Có thể dùng để hiển thị thông báo nếu không có dữ liệu
from django.core.exceptions import PermissionDenied
# from django.utils import timezone # Không cần thiết cho view này
from django.db.models import Q, Max # Q, Max có thể không cần thiết cho view này, nhưng để lại nếu các view khác dùng
# from django.forms import modelformset_factory # Không cần thiết cho view này
# from django.urls import reverse # Không cần thiết cho view này
from collections import defaultdict
# import json # Không cần thiết nếu convert_defaultdict_to_dict được dùng đúng

from .models import Score, RewardAndDiscipline, Evaluation # Đảm bảo Evaluation được import
from accounts.models import StudentProfile, ParentProfile, User, Role # User, Role có thể không cần trực tiếp ở đây
# from school_data.models import Class as SchoolClass, Subject as SchoolSubject, Department # Không cần trực tiếp ở đây
# from .forms import ScoreContextForm, ScoreEntryForm, RewardAndDisciplineForm, EvaluationForm # Không cần form cho view này

def convert_defaultdict_to_dict(d):
    """
    Hàm đệ quy để chuyển đổi defaultdict (và các defaultdict lồng nhau) thành dict thông thường.
    """
    if isinstance(d, defaultdict):
        return {k: convert_defaultdict_to_dict(v) for k, v in d.items()}
    return d

# ... (các views khác như view_scores, enter_scores, create_edit_evaluation, etc. đã có) ...

@login_required
def view_evaluations(request):
    user = request.user
    context = {
        'page_title': 'Đánh giá và Nhận xét',
        'evaluations_by_student': defaultdict(list), # {student_display_name: [evaluation_obj1, evaluation_obj2]}
        'is_parent': False,
        'students_to_view': [], # Danh sách StudentProfile instances
        'error_message': None
    }

    user_role_name = getattr(user.role, 'name', None) if hasattr(user, 'role') and user.role else None

    if user_role_name == 'STUDENT':
        try:
            # Giả định user có OneToOneField 'student_profile' đến StudentProfile
            student_profile = StudentProfile.objects.get(user=user) 
            context['students_to_view'] = [student_profile]
            context['page_title'] = f'Đánh giá/Nhận xét cho {student_profile.user.get_full_name() or student_profile.user.username}'
        except StudentProfile.DoesNotExist:
            context['error_message'] = "Không tìm thấy hồ sơ học sinh của bạn."
            # messages.warning(request, "Không tìm thấy hồ sơ học sinh của bạn.")

    elif user_role_name == 'PARENT':
        context['is_parent'] = True
        try:
            parent_profile = ParentProfile.objects.get(user=user)
            # Giả sử StudentProfile có ForeignKey 'parent' trỏ đến ParentProfile
            # và ParentProfile có related_name 'children' từ StudentProfile.parent
            children_profiles_qs = parent_profile.children.all().select_related('user')
            
            if not children_profiles_qs.exists():
                context['error_message'] = "Bạn chưa có thông tin học sinh nào được liên kết."
                # messages.info(request, "Bạn chưa có thông tin học sinh nào được liên kết.")
            else:
                context['students_to_view'] = list(children_profiles_qs)
                context['page_title'] = 'Đánh giá/Nhận xét của các con'
        
        except ParentProfile.DoesNotExist:
            context['error_message'] = "Không tìm thấy hồ sơ phụ huynh của bạn."
            # messages.warning(request, "Không tìm thấy hồ sơ phụ huynh của bạn.")
        except Exception as e: 
            # logger.error(f"Lỗi khi lấy thông tin phụ huynh cho user {user.id}: {e}")
            context['error_message'] = "Đã có lỗi xảy ra khi truy xuất thông tin phụ huynh."
            # messages.error(request, "Đã có lỗi xảy ra khi truy xuất thông tin phụ huynh.")
    else:
        # Nếu không phải STUDENT hoặc PARENT
        context['error_message'] = "Chức năng này chỉ dành cho Học sinh và Phụ huynh."
        # Hoặc bạn có thể raise PermissionDenied("Bạn không có quyền xem trang này.")

    if context['students_to_view']:
        student_pks = [sp.pk for sp in context['students_to_view']]
        evaluations_qs = Evaluation.objects.filter(
            student_id__in=student_pks # Lọc theo ID của StudentProfile
        ).select_related('student__user', 'evaluator', 'subject').order_by('student__user__username', '-evaluation_date')
        
        for evaluation_item in evaluations_qs:
            student_display_name = evaluation_item.student.user.get_full_name() or evaluation_item.student.user.username
            context['evaluations_by_student'][student_display_name].append(evaluation_item)
            
    # Chuyển defaultdict thành dict thường để tránh các vấn đề tiềm ẩn trong template
    context['evaluations_by_student'] = dict(context['evaluations_by_student']) 
    
    return render(request, 'academic_records/view_evaluations.html', context)



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Q, Max
from django.forms import modelformset_factory 
from django.urls import reverse
from collections import defaultdict
# import json # Không cần thiết nếu convert_defaultdict_to_dict được dùng đúng

from .models import Score, RewardAndDiscipline, Evaluation 
from accounts.models import StudentProfile, ParentProfile, User, Role
from school_data.models import Class as SchoolClass, Subject as SchoolSubject, Department
from .forms import ScoreContextForm, ScoreEntryForm, RewardAndDisciplineForm, EvaluationForm

@login_required
def teacher_my_evaluations(request):
    user = request.user
    # Kiểm tra quyền: Chỉ Giáo viên
    # Đảm bảo user.role tồn tại và user.role.name được gán đúng
    if not (hasattr(user, 'role') and user.role and user.role.name == 'TEACHER'):
        # messages.error(request, "Chức năng này chỉ dành cho Giáo viên.") # Tùy chọn: thông báo lỗi
        # return redirect('homepage') # Hoặc trang lỗi quyền
        raise PermissionDenied("Chức năng này chỉ dành cho Giáo viên.")

    # Lấy tất cả các đánh giá mà giáo viên này đã tạo
    my_evaluations = Evaluation.objects.filter(
        evaluator=user
    ).select_related('student__user', 'subject').order_by('-evaluation_date', 'student__user__last_name')

    context = {
        'evaluations': my_evaluations, # Truyền danh sách đánh giá vào template
        'page_title': 'Các Đánh giá/Nhận xét bạn đã tạo',
    }
    return render(request, 'academic_records/teacher_my_evaluations.html', context)
