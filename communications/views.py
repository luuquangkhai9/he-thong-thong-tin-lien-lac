from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Q

from .models import Notification, RequestForm # Các model từ app này
from .forms import RequestFormSubmissionForm, RequestFormResponseForm # Các form từ app này

@login_required
def notification_list(request):
    user = request.user
    direct_q = Q(target_users=user)
    role_q = Q()
    if hasattr(user, 'role') and user.role:
        role_q = Q(target_roles=user.role)
    class_q = Q()
    if hasattr(user, 'student_profile') and user.student_profile and hasattr(user.student_profile, 'current_class') and user.student_profile.current_class:
        class_q = Q(target_classes=user.student_profile.current_class)
    
    final_q = direct_q | role_q | class_q
    notifications = Notification.objects.filter(final_q, is_published=True, status='SENT').distinct().order_by('-publish_time', '-created_time')

    context = {
        'notifications': notifications,
        'page_title': 'Danh sách Thông báo'
    }
    return render(request, 'communications/notification_list.html', context)

@login_required
def submit_request_form(request):
    if request.method == 'POST':
        form = RequestFormSubmissionForm(request.POST, user=request.user)
        if form.is_valid():
            new_request = form.save(commit=False) # Tạo instance nhưng chưa lưu các trường M2M
            new_request.submitted_by = request.user
            
            # Xử lý related_student từ related_student_for_parent
            # Trường này là ForeignKey nên sẽ được gán vào new_request trước khi save()
            if 'related_student_for_parent' in form.cleaned_data and form.cleaned_data['related_student_for_parent']:
                new_request.related_student = form.cleaned_data['related_student_for_parent']
            
            # assigned_department cũng là ForeignKey và sẽ được form xử lý khi new_request.save() được gọi
            # nếu nó là một phần của form.cleaned_data và model field.

            new_request.save() # Bước này lưu đối tượng chính và các ForeignKey vào DB. Instance new_request giờ đã có ID.

            # ===> SỬA Ở ĐÂY: Gọi form.save_m2m() để lưu các trường ManyToManyField <===
            form.save_m2m() # Dòng này sẽ lưu các mối quan hệ cho 'assigned_teachers'

            messages.success(request, 'Đơn của bạn đã được gửi thành công!')
            # Nên chuyển hướng đến trang danh sách đơn đã gửi để người dùng thấy đơn mới của họ
            return redirect('communications:my_submitted_requests')
    else:
        form = RequestFormSubmissionForm(user=request.user)
    
    context = {
        'form': form,
        'page_title': 'Gửi Đơn từ / Kiến nghị'
    }
    return render(request, 'communications/submit_request_form.html', context)

@login_required
def my_submitted_requests(request):
    user_requests = RequestForm.objects.filter(submitted_by=request.user).order_by('-submission_date')
    context = {
        'user_requests': user_requests,
        'page_title': 'Đơn từ/Kiến nghị đã gửi'
    }
    return render(request, 'communications/my_submitted_requests.html', context)

@login_required
def department_request_list(request):
    user = request.user
    if not (user.is_staff and hasattr(user, 'department') and user.department):
        raise PermissionDenied("Bạn không có quyền truy cập trang này hoặc chưa được gán vào phòng ban.")

    department_requests = RequestForm.objects.filter(
        assigned_department=user.department
    ).exclude(
        status__in=['RESOLVED', 'REJECTED', 'CLOSED']
    ).order_by('submission_date')

    context = {
        'department_requests': department_requests,
        'page_title': f'Đơn từ/Kiến nghị cho Phòng {user.department.name}',
        'department_name': user.department.name
    }
    return render(request, 'communications/department_request_list.html', context)

@login_required
def department_request_detail_respond(request, pk):
    user = request.user
    if not (user.is_staff and hasattr(user, 'department') and user.department):
        raise PermissionDenied("Bạn không có quyền truy cập hoặc xử lý đơn này.")

    request_form_instance = get_object_or_404(
        RequestForm,
        pk=pk,
        assigned_department=user.department
    )

    if request.method == 'POST':
        response_form = RequestFormResponseForm(request.POST, instance=request_form_instance)
        if response_form.is_valid():
            updated_request_form = response_form.save(commit=False)
            updated_request_form.responded_by = user
            updated_request_form.response_date = timezone.now()
            
            updated_request_form.save() # Lưu các thay đổi vào instance
            # response_form.save_m2m() # Không cần thiết cho RequestFormResponseForm vì nó không xử lý M2M

            messages.success(request, f"Đã cập nhật và phản hồi cho đơn '{request_form_instance.title}'.")
            
            # TODO: Gửi thông báo cho người gửi đơn gốc (Phụ huynh)
            
            return redirect('communications:department_request_list')
    else:
        response_form = RequestFormResponseForm(instance=request_form_instance)

    context = {
        'request_form_instance': request_form_instance,
        'response_form': response_form,
        'page_title': f'Chi tiết và Phản hồi Đơn: {request_form_instance.title}'
    }
    return render(request, 'communications/department_request_detail_respond.html', context)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db.models import Q

from .models import Notification, RequestForm # Các model từ app này
from .forms import RequestFormSubmissionForm, RequestFormResponseForm # Các form từ app này
# from accounts.models import User, Role # Ví dụ, nếu bạn cần kiểm tra Role cụ thể

# ... (các views notification_list, submit_request_form, my_submitted_requests,
# department_request_list, department_request_detail_respond đã có ở trên) ...

@login_required
def teacher_request_list(request):
    user = request.user
    # Kiểm tra xem user có phải là giáo viên không
    # (Dựa vào vai trò hoặc một cờ is_teacher trong User model/TeacherProfile)
    # Giả sử user.role.name == 'TEACHER'
    if not (hasattr(user, 'role') and user.role and user.role.name == 'TEACHER'):
        raise PermissionDenied("Bạn không có quyền truy cập trang này. Chức năng này dành cho Giáo viên.")

    # Lấy các đơn từ được gán cho giáo viên này và chưa được giải quyết hoàn toàn
    teacher_requests = RequestForm.objects.filter(
        assigned_teachers=user # Lọc các RequestForm mà user hiện tại nằm trong ManyToManyField 'assigned_teachers'
    ).exclude(
        status__in=['RESOLVED', 'REJECTED', 'CLOSED'] # Loại trừ các trạng thái đã xong
    ).order_by('submission_date') # Ưu tiên đơn cũ hơn

    context = {
        'teacher_requests': teacher_requests,
        'page_title': 'Đơn từ/Kiến nghị được gán cho bạn',
    }
    return render(request, 'communications/teacher_request_list.html', context)

@login_required
def teacher_request_detail_respond(request, pk):
    user = request.user
    # Kiểm tra quyền tương tự như teacher_request_list
    if not (hasattr(user, 'role') and user.role and user.role.name == 'TEACHER'):
        raise PermissionDenied("Bạn không có quyền truy cập hoặc xử lý đơn này.")

    # Lấy đơn từ, đảm bảo nó được gán cho giáo viên này
    request_form_instance = get_object_or_404(
        RequestForm,
        pk=pk,
        assigned_teachers=user # Đảm bảo giáo viên này nằm trong danh sách được gán
    )

    if request.method == 'POST':
        # Sử dụng lại RequestFormResponseForm
        response_form = RequestFormResponseForm(request.POST, instance=request_form_instance)
        if response_form.is_valid():
            updated_request_form = response_form.save(commit=False)
            updated_request_form.responded_by = user # Người phản hồi là giáo viên này
            updated_request_form.response_date = timezone.now()
            
            # Logic cập nhật status (tương tự như của phòng ban)
            # current_status_from_form = response_form.cleaned_data.get('status')
            # if current_status_from_form in ['RESOLVED', 'REJECTED']:
            #    updated_request_form.status = 'CLOSED' 

            updated_request_form.save()
            messages.success(request, f"Đã cập nhật và phản hồi cho đơn '{request_form_instance.title}'.")
            
            # TODO: Gửi thông báo cho người gửi đơn gốc (Phụ huynh) rằng đơn đã được phản hồi.
            
            return redirect('communications:teacher_request_list') # Chuyển hướng về danh sách đơn của giáo viên
    else:
        response_form = RequestFormResponseForm(instance=request_form_instance)

    context = {
        'request_form_instance': request_form_instance,
        'response_form': response_form,
        'page_title': f'Chi tiết và Phản hồi Đơn (GV): {request_form_instance.title}'
    }
    return render(request, 'communications/teacher_request_detail_respond.html', context)
