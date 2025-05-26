from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.db import IntegrityError
from .models import Course, Enrollment, User
from .forms import StudentEnrollmentForm
from .decorators import teacher_required

@login_required
@teacher_required
def add_student_to_course(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if course.teacher != request.user:
        return HttpResponseForbidden("You are not authorized to enroll students in this course.")
    
    if request.method == "POST":
        form = StudentEnrollmentForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]

            # Try to find existing user
            student = User.objects.filter(email=email).first()
            
            if student:
                # Check if student is already enrolled
                if Enrollment.objects.filter(course=course, student=student).exists():
                    form.add_error(None, "Student is already enrolled in this course.")
                else:
                    # Enroll existing student
                    Enrollment.objects.create(course=course, student=student, status="approved")
                    messages.success(request, f"{student.get_full_name()} has been enrolled in the course.")
                    
                    # Send enrollment notification to existing student
                    context = {
                        "student": student,
                        "course": course,
                        "teacher": request.user,
                        "is_existing_user": True
                    }
                    html_message = render_to_string("emails/student_enrollment.html", context)
                    send_mail(
                        f"You have been enrolled in {course.title}",
                        f"You have been enrolled in {course.title} by {request.user.get_full_name() or request.user.username}.",
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    return redirect("course_detail", slug=course.slug)
            else:
                # Create new student account
                try:
                    # Generate a unique username
                    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
                    generated_username = f"user_{timestamp}"
                    while User.objects.filter(username=generated_username).exists():
                        generated_username = f"user_{timestamp}_{get_random_string(6)}"

                    # Create new user
                    random_password = get_random_string(10)
                    student = User.objects.create_user(
                        username=generated_username,
                        email=email,
                        password=random_password,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    student.profile.is_teacher = False
                    student.profile.save()

                    # Enroll the new student
                    Enrollment.objects.create(course=course, student=student, status="approved")
                    messages.success(request, f"{first_name} {last_name} has been enrolled in the course.")

                    # Send enrollment notification and password reset link to new student
                    reset_link = request.build_absolute_uri(reverse("account_reset_password"))
                    context = {
                        "student": student,
                        "course": course,
                        "teacher": request.user,
                        "reset_link": reset_link,
                        "is_existing_user": False
                    }
                    html_message = render_to_string("emails/student_enrollment.html", context)
                    send_mail(
                        f"You have been enrolled in {course.title}",
                        f"You have been enrolled in {course.title} by {request.user.get_full_name() or request.user.username}. "
                        f"Please visit {reset_link} to set your password.",
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    return redirect("course_detail", slug=course.slug)
                except IntegrityError:
                    form.add_error(None, "Failed to create user account. Please try again.")
    else:
        form = StudentEnrollmentForm()

    return render(request, "courses/add_student.html", {"form": form, "course": course}) 