import json
import os
import subprocess
import time

import requests
import stripe
from captcha.fields import CaptchaField
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.http import FileResponse, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .calendar_sync import generate_google_calendar_link, generate_ical_feed, generate_outlook_calendar_link
from .decorators import teacher_required
from .forms import CourseForm, CourseMaterialForm, ProfileUpdateForm, ReviewForm, SessionForm, TeacherSignupForm
from .marketing import (
    generate_social_share_content,
    get_course_analytics,
    get_promotion_recommendations,
    send_course_promotion_email,
)
from .models import (
    Achievement,
    BlogComment,
    BlogPost,
    Course,
    CourseMaterial,
    CourseProgress,
    Enrollment,
    ForumCategory,
    ForumReply,
    ForumTopic,
    PeerConnection,
    PeerMessage,
    Review,
    Session,
    SessionAttendance,
    StudyGroup,
)
from .notifications import notify_session_reminder, notify_teacher_new_enrollment, send_enrollment_confirmation

GOOGLE_CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, "google_credentials.json")

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


def sitemap(request):
    return render(request, "sitemap.html")


def index(request):
    if request.method == "POST":
        form = TeacherSignupForm(request.POST)
        if form.is_valid():
            user, subject = form.save()
            messages.success(
                request,
                (
                    f"Thank you for signing up! We've sent instructions to {user.email} - "
                    "you can continue to create your course"
                ),
            )
            # log teh user in
            user = User.objects.get(email=user.email)
            user.backend = "django.contrib.auth.backends.ModelBackend"
            login(request, user)

            # TODO: Send welcome email
            # redirect to create a course
            return redirect("create_course")
    else:
        form = TeacherSignupForm()

    # Get featured courses - newest courses with highest ratings
    featured_courses = Course.objects.all().order_by("-created_at")[:3]

    context = {
        "form": form,
        "featured_courses": featured_courses,
    }
    return render(request, "index.html", context)


# def register(request):
#     if request.method == "POST":
#         form = UserRegistrationForm(request.POST)
#         if form.is_valid():
#             user = form.save()
#             # Get or create profile and set is_teacher
#             profile, created = Profile.objects.get_or_create(user=user)
#             profile.is_teacher = form.cleaned_data.get("is_teacher", False)
#             profile.save()

#             messages.success(request, "Registration successful. Please login.")
#             return redirect("login")
#     else:
#         form = UserRegistrationForm()
#     return render(request, "registration/register.html", {"form": form})


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")
    else:
        form = ProfileUpdateForm(instance=request.user)

    context = {
        "form": form,
    }

    # Add teacher-specific stats
    if request.user.profile.is_teacher:
        courses = Course.objects.filter(teacher=request.user)
        total_students = sum(course.enrollments.filter(status="approved").count() for course in courses)
        avg_rating = 0
        total_ratings = 0
        for course in courses:
            course_ratings = course.reviews.all()
            if course_ratings:
                avg_rating += sum(review.rating for review in course_ratings)
                total_ratings += len(course_ratings)

        avg_rating = round(avg_rating / total_ratings, 1) if total_ratings > 0 else 0

        context.update(
            {
                "courses": courses,
                "total_students": total_students,
                "avg_rating": avg_rating,
            }
        )

    # Add student-specific stats
    else:
        enrollments = Enrollment.objects.filter(student=request.user).select_related("course")
        completed_courses = enrollments.filter(status="completed").count()

        # Calculate average progress
        total_progress = 0
        progress_count = 0
        for enrollment in enrollments:
            progress, _ = CourseProgress.objects.get_or_create(enrollment=enrollment)
            if progress.completion_percentage is not None:
                total_progress += progress.completion_percentage
                progress_count += 1

        avg_progress = round(total_progress / progress_count) if progress_count > 0 else 0

        context.update(
            {
                "enrollments": enrollments,
                "completed_courses": completed_courses,
                "avg_progress": avg_progress,
            }
        )

    return render(request, "profile.html", context)


@login_required
def create_course(request):
    if not request.user.profile.is_teacher:
        return HttpResponseForbidden()

    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.teacher = request.user
            course.save()
            form.save_m2m()  # Save many-to-many relationships
            return redirect("course_detail", slug=course.slug)
    else:
        form = CourseForm()

    return render(request, "courses/create.html", {"form": form})


@login_required
def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug)
    sessions = Session.objects.filter(course=course).order_by("start_time")
    reviews = Review.objects.filter(course=course).order_by("-created_at")

    # Check if user is enrolled or is the teacher
    is_enrolled = False
    is_teacher = False
    completed_sessions = []
    enrollment = None

    if request.user.is_authenticated:
        is_enrolled = request.user.enrollments.filter(course=course).exists()
        is_teacher = request.user == course.teacher

        if is_enrolled:
            enrollment = request.user.enrollments.get(course=course)
            progress = CourseProgress.objects.get_or_create(enrollment=enrollment)[0]
            completed_sessions = progress.completed_sessions.all()

    # Get similar courses based on subject and level
    similar_courses = Course.objects.exclude(id=course.id).filter(Q(subject=course.subject) | Q(level=course.level))[:3]

    context = {
        "course": course,
        "sessions": sessions,
        "reviews": reviews,
        "is_enrolled": is_enrolled,
        "is_teacher": is_teacher,
        "enrollment": enrollment,
        "completed_sessions": completed_sessions,
        "similar_courses": similar_courses,
        "now": timezone.now(),
        "stripe_public_key": settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, "courses/detail.html", context)


@login_required
def enroll_course(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)

    # Check if user is already enrolled
    if request.user.enrollments.filter(course=course).exists():
        messages.warning(request, "You are already enrolled in this course.")
        return redirect("course_detail", slug=course_slug)

    # Check if course is full
    if course.max_students and course.enrollments.count() >= course.max_students:
        messages.error(request, "This course is full.")
        return redirect("course_detail", slug=course_slug)

    # For paid courses, enrollment is handled through Stripe webhook
    if course.price > 0:
        messages.error(request, "Please complete the payment process to enroll in this course.")
        return redirect("course_detail", slug=course_slug)

    # Create enrollment for free courses
    enrollment = Enrollment.objects.create(
        student=request.user,
        course=course,
        status="enrolled",
    )

    # Send confirmation email
    send_enrollment_confirmation(enrollment)

    # Notify teacher
    notify_teacher_new_enrollment(enrollment)

    messages.success(request, "You have successfully enrolled in this course.")
    return redirect("course_detail", slug=course_slug)


@login_required
def add_session(request, slug):
    course = Course.objects.get(slug=slug)
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can add sessions!")
        return redirect("course_detail", slug=slug)

    if request.method == "POST":
        form = SessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.course = course
            session.save()
            # Send session notifications to enrolled students
            notify_session_reminder(session)
            messages.success(request, "Session added successfully!")
            return redirect("course_detail", slug=slug)
    else:
        form = SessionForm()

    return render(request, "courses/add_session.html", {"form": form, "course": course})


@login_required
def add_review(request, slug):
    course = Course.objects.get(slug=slug)
    if not request.user.enrollments.filter(course=course).exists():
        messages.error(request, "Only enrolled students can review the course!")
        return redirect("course_detail", slug=slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.student = request.user
            review.course = course
            review.save()
            messages.success(request, "Review added successfully!")
            return redirect("course_detail", slug=slug)
    else:
        form = ReviewForm()

    return render(request, "courses/add_review.html", {"form": form, "course": course})


@login_required
def delete_course(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can delete the course!")
        return redirect("course_detail", slug=slug)

    if request.method == "POST":
        course.delete()
        messages.success(request, "Course deleted successfully!")
        return redirect("profile")

    return render(request, "courses/delete_confirm.html", {"course": course})


@csrf_exempt
def github_update(request):
    send_slack_message("New commit pulled from GitHub")
    root_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        subprocess.run(["chmod", "+x", f"{root_directory}/setup.sh"])
        result = subprocess.run(["bash", f"{root_directory}/setup.sh"], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(
                f"setup.sh failed with return code {result.returncode} and output: {result.stdout} {result.stderr}"
            )
        send_slack_message("CHMOD success about to set time on: " + settings.PA_WSGI)

        current_time = time.time()
        os.utime(settings.PA_WSGI, (current_time, current_time))
        send_slack_message("Repository updated successfully")
        return HttpResponse("Repository updated successfully")
    except Exception as e:
        print(f"Deploy error: {e}")
        send_slack_message(f"Deploy error: {e}")
        return HttpResponse("Deploy error see logs.")


def send_slack_message(message):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("Warning: SLACK_WEBHOOK_URL not configured")
        return

    payload = {"text": f"```{message}```"}
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()  # Raise exception for bad status codes
    except Exception as e:
        print(f"Failed to send Slack message: {e}")


def get_wsgi_last_modified_time():
    try:
        return time.ctime(os.path.getmtime(settings.PA_WSGI))
    except Exception:
        return "Unknown"


def subjects(request):
    return render(request, "subjects.html")


class LearnForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    subject = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea)
    captcha = CaptchaField()


class TeachForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    expertise = forms.CharField(max_length=200)
    experience = forms.CharField(widget=forms.Textarea)
    captcha = CaptchaField()


def about(request):
    return render(request, "about.html")


def learn(request):
    if request.method == "POST":
        form = LearnForm(request.POST)
        if form.is_valid():
            # Process form data
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]

            # Compose the email content
            email_subject = f"New Learning Inquiry: {subject}"
            email_message = (
                f"Hello Admin,\n\n"
                f"You've received a new learning inquiry:\n\n"
                f"Name: {name}\n"
                f"Email: {email}\n"
                f"Subject: {subject}\n"
                f"Message:\n{message}\n\n"
                f"Regards,\nAlpha One Labs"
            )

            # Send the email
            send_mail(
                email_subject,
                email_message,
                settings.EMAIL_FROM,  # From email (configured in settings)
                [settings.EMAIL_FROM],  # Replace with the recipient's email
                fail_silently=False,
            )

            return HttpResponse("Thank you for your interest in learning! We've received your inquiry.")
    else:
        form = LearnForm()
    return render(request, "learn.html", {"form": form})


def teach(request):
    if request.method == "POST":
        form = TeachForm(request.POST)
        if form.is_valid():
            # Process form data
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            expertise = form.cleaned_data["expertise"]
            experience = form.cleaned_data["experience"]

            # Compose the email content
            email_subject = f"New Teaching Inquiry from {name}"
            email_message = (
                f"Hello Admin,\n\n"
                f"You've received a new teaching inquiry:\n\n"
                f"Name: {name}\n"
                f"Email: {email}\n"
                f"Expertise: {expertise}\n"
                f"Experience:\n{experience}\n\n"
                f"Regards,\nAlpha One Labs"
            )

            # Send the email
            send_mail(
                email_subject,
                email_message,
                settings.EMAIL_FROM,  # From email (configured in settings)
                [settings.EMAIL_FROM],  # Replace with the recipient's email
                fail_silently=False,
            )

            return HttpResponse("Thank you for your interest in teaching! We've received your inquiry.")
    else:
        form = TeachForm()
    return render(request, "teach.html", {"form": form})


def course_search(request):
    query = request.GET.get("q", "")
    subject = request.GET.get("subject", "")
    level = request.GET.get("level", "")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    sort_by = request.GET.get("sort", "-created_at")

    courses = Course.objects.all()

    # Apply filters
    if query:
        courses = courses.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(tags__icontains=query))

    if subject:
        courses = courses.filter(subject=subject)

    if level:
        courses = courses.filter(level=level)

    if min_price:
        courses = courses.filter(price__gte=float(min_price))

    if max_price:
        courses = courses.filter(price__lte=float(max_price))

    # Apply sorting
    if sort_by == "price":
        courses = courses.order_by("price")
    elif sort_by == "-price":
        courses = courses.order_by("-price")
    elif sort_by == "title":
        courses = courses.order_by("title")
    elif sort_by == "rating":
        courses = sorted(courses, key=lambda c: c.average_rating, reverse=True)
    else:  # Default to newest
        courses = courses.order_by("-created_at")

    # Pagination
    paginator = Paginator(courses, 12)  # Show 12 courses per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "query": query,
        "subject": subject,
        "level": level,
        "min_price": min_price,
        "max_price": max_price,
        "sort_by": sort_by,
        "subject_choices": Course._meta.get_field("subject").choices,
        "level_choices": Course._meta.get_field("level").choices,
    }

    return render(request, "courses/search.html", context)


@login_required
def create_payment_intent(request, slug):
    course = Course.objects.get(slug=slug)

    # Check if user is already enrolled
    if Enrollment.objects.filter(student=request.user, course=course).exists():
        return JsonResponse({"error": "Already enrolled in this course"}, status=400)

    try:
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(course.price * 100),  # Convert to cents
            currency="usd",
            metadata={"course_id": course.id, "user_id": request.user.id},
        )

        return JsonResponse(
            {
                "clientSecret": intent.client_secret,
                "publicKey": settings.STRIPE_PUBLISHABLE_KEY,
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)

        if event.type == "payment_intent.succeeded":
            payment_intent = event.data.object
            handle_successful_payment(payment_intent)
        elif event.type == "payment_intent.payment_failed":
            payment_intent = event.data.object
            handle_failed_payment(payment_intent)

        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def handle_successful_payment(payment_intent):
    # Get metadata from the payment intent
    course_id = payment_intent.metadata.get("course_id")
    user_id = payment_intent.metadata.get("user_id")

    # Create enrollment and payment records
    course = Course.objects.get(id=course_id)
    user = User.objects.get(id=user_id)

    enrollment = Enrollment.objects.create(student=user, course=course, status="approved")

    # Send notifications
    send_enrollment_confirmation(enrollment)
    notify_teacher_new_enrollment(enrollment)


def handle_failed_payment(payment_intent):
    # Just log the failure, no need to update payment status since we're not tracking payments
    pass


@login_required
def update_course(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.user != course.teacher:
        return HttpResponseForbidden()

    if request.method == "POST":
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            return redirect("course_detail", slug=course.slug)
    else:
        form = CourseForm(instance=course)

    return render(request, "courses/update.html", {"form": form, "course": course})


@login_required
def mark_session_attendance(request, session_id):
    session = Session.objects.get(id=session_id)
    if request.user != session.course.teacher:
        messages.error(request, "Only the course teacher can mark attendance!")
        return redirect("course_detail", slug=session.course.slug)

    if request.method == "POST":
        for student_id, status in request.POST.items():
            if student_id.startswith("student_"):
                student_id = student_id.replace("student_", "")
                student = User.objects.get(id=student_id)
                attendance, created = SessionAttendance.objects.update_or_create(
                    session=session, student=student, defaults={"status": status}
                )
        messages.success(request, "Attendance marked successfully!")
        return redirect("course_detail", slug=session.course.slug)

    enrollments = session.course.enrollments.filter(status="approved")
    attendances = {att.student_id: att.status for att in session.attendances.all()}

    context = {
        "session": session,
        "enrollments": enrollments,
        "attendances": attendances,
    }
    return render(request, "courses/mark_attendance.html", context)


@login_required
def mark_session_completed(request, session_id):
    session = Session.objects.get(id=session_id)
    enrollment = request.user.enrollments.get(course=session.course)

    if enrollment.status != "approved":
        messages.error(request, "You must be enrolled in the course to mark sessions as completed!")
        return redirect("course_detail", slug=session.course.slug)

    progress, created = CourseProgress.objects.get_or_create(enrollment=enrollment)
    progress.completed_sessions.add(session)

    # Check for achievements
    if progress.completion_percentage == 100:
        Achievement.objects.get_or_create(
            student=request.user,
            course=session.course,
            achievement_type="completion",
            defaults={
                "title": "Course Completed!",
                "description": f"Completed all sessions in {session.course.title}",
            },
        )

    if progress.attendance_rate == 100:
        Achievement.objects.get_or_create(
            student=request.user,
            course=session.course,
            achievement_type="attendance",
            defaults={
                "title": "Perfect Attendance!",
                "description": f"Attended all sessions in {session.course.title}",
            },
        )

    messages.success(request, "Session marked as completed!")
    return redirect("course_detail", slug=session.course.slug)


@login_required
def student_progress(request, enrollment_id):
    enrollment = Enrollment.objects.get(id=enrollment_id)

    if request.user != enrollment.student and request.user != enrollment.course.teacher:
        messages.error(request, "You don't have permission to view this progress!")
        return redirect("course_detail", slug=enrollment.course.slug)

    progress, created = CourseProgress.objects.get_or_create(enrollment=enrollment)
    achievements = Achievement.objects.filter(student=enrollment.student, course=enrollment.course)

    past_sessions = enrollment.course.sessions.filter(start_time__lt=timezone.now())
    upcoming_sessions = enrollment.course.sessions.filter(start_time__gte=timezone.now())

    context = {
        "enrollment": enrollment,
        "progress": progress,
        "achievements": achievements,
        "past_sessions": past_sessions,
        "upcoming_sessions": upcoming_sessions,
    }
    return render(request, "courses/student_progress.html", context)


@login_required
def course_progress_overview(request, slug):
    course = Course.objects.get(slug=slug)
    if request.user != course.teacher:
        messages.error(request, "Only the course teacher can view the progress overview!")
        return redirect("course_detail", slug=slug)

    enrollments = course.enrollments.filter(status="approved")
    progress_data = []

    for enrollment in enrollments:
        progress, created = CourseProgress.objects.get_or_create(enrollment=enrollment)
        attendance_data = (
            SessionAttendance.objects.filter(student=enrollment.student, session__course=course)
            .values("status")
            .annotate(count=models.Count("status"))
        )

        progress_data.append(
            {
                "enrollment": enrollment,
                "progress": progress,
                "attendance": attendance_data,
            }
        )

    context = {
        "course": course,
        "progress_data": progress_data,
    }
    return render(request, "courses/progress_overview.html", context)


@login_required
def upload_material(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.user != course.teacher:
        return HttpResponseForbidden("You are not authorized to upload materials for this course.")

    if request.method == "POST":
        form = CourseMaterialForm(request.POST, request.FILES, course=course)
        if form.is_valid():
            material = form.save(commit=False)
            material.course = course
            material.save()
            messages.success(request, "Course material uploaded successfully!")
            return redirect("course_detail", slug=course.slug)
    else:
        form = CourseMaterialForm(course=course)

    return render(request, "courses/upload_material.html", {"form": form, "course": course})


@login_required
def delete_material(request, slug, material_id):
    material = get_object_or_404(CourseMaterial, id=material_id, course__slug=slug)
    if request.user != material.course.teacher:
        return HttpResponseForbidden("You are not authorized to delete this material.")

    if request.method == "POST":
        material.delete()
        messages.success(request, "Course material deleted successfully!")
        return redirect("course_detail", slug=slug)

    return render(request, "courses/delete_material_confirm.html", {"material": material})


@login_required
def download_material(request, slug, material_id):
    material = get_object_or_404(CourseMaterial, id=material_id, course__slug=slug)
    if not material.is_downloadable and request.user != material.course.teacher:
        return HttpResponseForbidden("This material is not available for download.")

    try:
        return FileResponse(material.file, as_attachment=True)
    except FileNotFoundError:
        messages.error(request, "The requested file could not be found.")
        return redirect("course_detail", slug=slug)


@login_required
@teacher_required
def course_marketing(request, slug):
    """View for managing course marketing and promotions."""
    course = get_object_or_404(Course, slug=slug, teacher=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "send_promotional_emails":
            send_course_promotion_email(
                course=course,
                subject=f"New Course Recommendation: {course.title}",
                template_name="course_promotion",
            )
            messages.success(request, "Promotional emails have been sent successfully.")

        elif action == "generate_social_content":
            social_content = generate_social_share_content(course)
            return JsonResponse({"social_content": social_content})

    # Get analytics and recommendations
    analytics = get_course_analytics(course)
    recommendations = get_promotion_recommendations(course)

    context = {
        "course": course,
        "analytics": analytics,
        "recommendations": recommendations,
    }

    return render(request, "courses/marketing.html", context)


@login_required
@teacher_required
def course_analytics(request, slug):
    """View for displaying detailed course analytics."""
    course = get_object_or_404(Course, slug=slug, teacher=request.user)
    analytics = get_course_analytics(course)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"analytics": analytics})

    context = {
        "course": course,
        "analytics": analytics,
    }

    return render(request, "courses/analytics.html", context)


@login_required
def calendar_feed(request):
    """Generate and serve an iCal feed of the user's course sessions."""

    response = HttpResponse(generate_ical_feed(request.user), content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="{settings.SITE_NAME}-schedule.ics"'
    return response


@login_required
def calendar_links(request, session_id):
    """Get calendar links for a specific session."""

    session = get_object_or_404(Session, id=session_id)

    # Check if user has access to this session
    if not (
        request.user == session.course.teacher
        or request.user.enrollments.filter(course=session.course, status="approved").exists()
    ):
        return HttpResponseForbidden("You don't have access to this session.")

    links = {
        "google": generate_google_calendar_link(session),
        "outlook": generate_outlook_calendar_link(session),
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"links": links})

    return render(
        request,
        "courses/calendar_links.html",
        {
            "session": session,
            "calendar_links": links,
        },
    )


def forum_categories(request):
    """Display all forum categories."""
    categories = ForumCategory.objects.all()
    return render(request, "web/forum/categories.html", {"categories": categories})


def forum_category(request, slug):
    """Display topics in a specific category."""
    category = get_object_or_404(ForumCategory, slug=slug)
    topics = category.topics.all()
    return render(request, "web/forum/category.html", {"category": category, "topics": topics})


def forum_topic(request, category_slug, topic_id):
    """Display a specific forum topic and its replies."""
    category = get_object_or_404(ForumCategory, slug=category_slug)
    topic = get_object_or_404(ForumTopic, id=topic_id, category=category)
    replies = topic.replies.all()

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to post replies.")
            return redirect("login")

        content = request.POST.get("content")
        if content:
            ForumReply.objects.create(topic=topic, author=request.user, content=content)
            messages.success(request, "Reply posted successfully!")
            return redirect("forum_topic", category_slug=category_slug, topic_id=topic_id)

    return render(
        request,
        "web/forum/topic.html",
        {
            "category": category,
            "topic": topic,
            "replies": replies,
        },
    )


@login_required
def create_topic(request, category_slug):
    """Create a new forum topic."""
    category = get_object_or_404(ForumCategory, slug=category_slug)

    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        if title and content:
            topic = ForumTopic.objects.create(category=category, author=request.user, title=title, content=content)
            messages.success(request, "Topic created successfully!")
            return redirect("forum_topic", category_slug=category_slug, topic_id=topic.id)

    return render(request, "web/forum/create_topic.html", {"category": category})


@login_required
def peer_connections(request):
    """Display user's peer connections."""
    sent_connections = request.user.sent_connections.all()
    received_connections = request.user.received_connections.all()
    return render(
        request,
        "web/peer/connections.html",
        {
            "sent_connections": sent_connections,
            "received_connections": received_connections,
        },
    )


@login_required
def send_connection_request(request, user_id):
    """Send a peer connection request."""
    receiver = get_object_or_404(User, id=user_id)

    if request.user == receiver:
        messages.error(request, "You cannot connect with yourself!")
        return redirect("peer_connections")

    connection, created = PeerConnection.objects.get_or_create(
        sender=request.user, receiver=receiver, defaults={"status": "pending"}
    )

    if created:
        messages.success(request, f"Connection request sent to {receiver.username}!")
    else:
        messages.info(request, f"Connection request already sent to {receiver.username}.")

    return redirect("peer_connections")


@login_required
def handle_connection_request(request, connection_id, action):
    """Accept or reject a peer connection request."""
    connection = get_object_or_404(PeerConnection, id=connection_id, receiver=request.user, status="pending")

    if action == "accept":
        connection.status = "accepted"
        messages.success(request, f"Connection with {connection.sender.username} accepted!")
    elif action == "reject":
        connection.status = "rejected"
        messages.info(request, f"Connection with {connection.sender.username} rejected.")

    connection.save()
    return redirect("peer_connections")


@login_required
def peer_messages(request, user_id):
    """Display and handle messages with a peer."""
    peer = get_object_or_404(User, id=user_id)

    # Check if users are connected
    connection = PeerConnection.objects.filter(
        (Q(sender=request.user, receiver=peer) | Q(sender=peer, receiver=request.user)),
        status="accepted",
    ).first()

    if not connection:
        messages.error(request, "You must be connected with this user to send messages.")
        return redirect("peer_connections")

    if request.method == "POST":
        content = request.POST.get("content")
        if content:
            PeerMessage.objects.create(sender=request.user, receiver=peer, content=content)
            messages.success(request, "Message sent!")

    # Get conversation messages
    messages_list = PeerMessage.objects.filter(
        (Q(sender=request.user, receiver=peer) | Q(sender=peer, receiver=request.user))
    ).order_by("created_at")

    # Mark received messages as read
    messages_list.filter(sender=peer, receiver=request.user, is_read=False).update(is_read=True)

    return render(request, "web/peer/messages.html", {"peer": peer, "messages": messages_list})


@login_required
def study_groups(request, course_id):
    """Display study groups for a course."""
    course = get_object_or_404(Course, id=course_id)
    groups = course.study_groups.all()

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        max_members = request.POST.get("max_members", 10)
        is_private = request.POST.get("is_private", False)

        if name and description:
            group = StudyGroup.objects.create(
                course=course,
                creator=request.user,
                name=name,
                description=description,
                max_members=max_members,
                is_private=is_private,
            )
            group.members.add(request.user)
            messages.success(request, "Study group created successfully!")
            return redirect("study_group_detail", group_id=group.id)

    return render(request, "web/study/groups.html", {"course": course, "groups": groups})


@login_required
def study_group_detail(request, group_id):
    """Display study group details and handle join/leave requests."""
    group = get_object_or_404(StudyGroup, id=group_id)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "join":
            if group.members.count() >= group.max_members:
                messages.error(request, "This group is full!")
            else:
                group.members.add(request.user)
                messages.success(request, f"You have joined {group.name}!")

        elif action == "leave":
            if request.user == group.creator:
                messages.error(request, "Group creator cannot leave the group!")
            else:
                group.members.remove(request.user)
                messages.info(request, f"You have left {group.name}.")

    return render(request, "web/study/group_detail.html", {"group": group})


# API Views
@login_required
def api_course_list(request):
    """API endpoint for listing courses."""
    courses = Course.objects.filter(status="published")
    data = [
        {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "teacher": course.teacher.username,
            "price": str(course.price),
            "subject": course.subject,
            "level": course.level,
            "slug": course.slug,
        }
        for course in courses
    ]
    return JsonResponse(data, safe=False)


@login_required
@teacher_required
def api_course_create(request):
    """API endpoint for creating a course."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    data = json.loads(request.body)
    course = Course.objects.create(
        teacher=request.user,
        title=data["title"],
        description=data["description"],
        learning_objectives=data["learning_objectives"],
        prerequisites=data.get("prerequisites", ""),
        price=data["price"],
        max_students=data["max_students"],
        subject=data["subject"],
        level=data["level"],
    )
    return JsonResponse(
        {
            "id": course.id,
            "title": course.title,
            "slug": course.slug,
        },
        status=201,
    )


@login_required
def api_course_detail(request, slug):
    """API endpoint for course details."""
    course = get_object_or_404(Course, slug=slug)
    data = {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "teacher": course.teacher.username,
        "price": str(course.price),
        "subject": course.subject,
        "level": course.level,
        "prerequisites": course.prerequisites,
        "learning_objectives": course.learning_objectives,
        "max_students": course.max_students,
        "available_spots": course.available_spots,
        "average_rating": course.average_rating,
    }
    return JsonResponse(data)


@login_required
def api_enroll(request, course_slug):
    """API endpoint for course enrollment."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    course = get_object_or_404(Course, slug=course_slug)
    if request.user.enrollments.filter(course=course).exists():
        return JsonResponse({"error": "Already enrolled"}, status=400)

    enrollment = Enrollment.objects.create(
        student=request.user,
        course=course,
        status="pending",
    )
    return JsonResponse(
        {
            "id": enrollment.id,
            "status": enrollment.status,
        },
        status=201,
    )


@login_required
def api_enrollments(request):
    """API endpoint for listing user enrollments."""
    enrollments = request.user.enrollments.all()
    data = [
        {
            "id": enrollment.id,
            "course": {
                "id": enrollment.course.id,
                "title": enrollment.course.title,
                "slug": enrollment.course.slug,
            },
            "status": enrollment.status,
            "enrollment_date": enrollment.enrollment_date.isoformat(),
        }
        for enrollment in enrollments
    ]
    return JsonResponse(data, safe=False)


@login_required
def api_session_list(request, course_slug):
    """API endpoint for listing course sessions."""
    course = get_object_or_404(Course, slug=course_slug)
    sessions = course.sessions.all()
    data = [
        {
            "id": session.id,
            "title": session.title,
            "description": session.description,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat(),
            "is_virtual": session.is_virtual,
        }
        for session in sessions
    ]
    return JsonResponse(data, safe=False)


@login_required
def api_session_detail(request, pk):
    """API endpoint for session details."""
    session = get_object_or_404(Session, pk=pk)
    data = {
        "id": session.id,
        "title": session.title,
        "description": session.description,
        "start_time": session.start_time.isoformat(),
        "end_time": session.end_time.isoformat(),
        "is_virtual": session.is_virtual,
        "meeting_link": session.meeting_link if session.is_virtual else None,
        "location": session.location if not session.is_virtual else None,
    }
    return JsonResponse(data)


@login_required
def api_forum_topic_create(request):
    """API endpoint for creating forum topics."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    data = json.loads(request.body)
    category = get_object_or_404(ForumCategory, id=data["category"])
    topic = ForumTopic.objects.create(
        title=data["title"],
        content=data["content"],
        category=category,
        author=request.user,
    )
    return JsonResponse(
        {
            "id": topic.id,
            "title": topic.title,
        },
        status=201,
    )


@login_required
def api_forum_reply_create(request):
    """API endpoint for creating forum replies."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    data = json.loads(request.body)
    topic = get_object_or_404(ForumTopic, id=data["topic"])
    reply = ForumReply.objects.create(
        topic=topic,
        content=data["content"],
        author=request.user,
    )
    return JsonResponse(
        {
            "id": reply.id,
            "content": reply.content,
        },
        status=201,
    )


# @login_required
# def logout_view(request):
#     if request.method == "POST":
#         logout(request)
#         return redirect("index")
#     return redirect("index")


@login_required
def session_detail(request, session_id):
    try:
        session = get_object_or_404(Session, id=session_id)

        # Check access rights
        if not (
            request.user == session.course.teacher
            or request.user.enrollments.filter(course=session.course, status="approved").exists()
        ):
            return HttpResponseForbidden("You don't have access to this session")

        context = {
            "session": session,
            "is_teacher": request.user == session.course.teacher,
            "now": timezone.now(),
        }

        return render(request, "web/study/session_detail.html", context)

    except Session.DoesNotExist:
        messages.error(request, "Session not found")
        return redirect("course_search")
    except Exception as e:
        if settings.DEBUG:
            raise e
        messages.error(request, "An error occurred while loading the session")
        return redirect("index")


def blog_list(request):
    blog_posts = BlogPost.objects.filter(status="published").order_by("-published_at")
    return render(request, "blog/list.html", {"blog_posts": blog_posts})


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, status="published")
    comments = post.comments.filter(is_approved=True, parent=None)

    if request.method == "POST" and request.user.is_authenticated:
        content = request.POST.get("content")
        if content:
            BlogComment.objects.create(
                post=post,
                author=request.user,
                content=content,
                is_approved=True,  # Auto-approve for now
            )
            messages.success(request, "Comment posted successfully!")
            return redirect("blog_detail", slug=slug)

    return render(request, "blog/detail.html", {"post": post, "comments": comments})


@login_required
def student_dashboard(request):
    """Dashboard view for students showing their enrollments, progress, and upcoming sessions."""
    if request.user.profile.is_teacher:
        messages.error(request, "This dashboard is for students only.")
        return redirect("profile")

    enrollments = Enrollment.objects.filter(student=request.user).select_related("course")
    upcoming_sessions = Session.objects.filter(
        course__enrollments__student=request.user, start_time__gt=timezone.now()
    ).order_by("start_time")[:5]

    # Get progress for each enrollment
    progress_data = []
    total_progress = 0
    for enrollment in enrollments:
        progress, _ = CourseProgress.objects.get_or_create(enrollment=enrollment)
        progress_data.append(
            {
                "enrollment": enrollment,
                "progress": progress,
            }
        )
        total_progress += progress.completion_percentage

    # Calculate average progress
    avg_progress = round(total_progress / len(progress_data)) if progress_data else 0

    context = {
        "enrollments": enrollments,
        "upcoming_sessions": upcoming_sessions,
        "progress_data": progress_data,
        "avg_progress": avg_progress,
    }
    return render(request, "dashboard/student.html", context)


@login_required
@teacher_required
def teacher_dashboard(request):
    """Dashboard view for teachers showing their courses, student progress, and upcoming sessions."""
    courses = Course.objects.filter(teacher=request.user)
    upcoming_sessions = Session.objects.filter(course__teacher=request.user, start_time__gt=timezone.now()).order_by(
        "start_time"
    )[:5]

    # Get enrollment and progress stats for each course
    course_stats = []
    for course in courses:
        enrollments = course.enrollments.filter(status="approved")
        total_students = enrollments.count()
        completed = enrollments.filter(status="completed").count()
        course_stats.append(
            {
                "course": course,
                "total_students": total_students,
                "completed": completed,
                "completion_rate": (completed / total_students * 100) if total_students > 0 else 0,
            }
        )

    context = {
        "courses": courses,
        "upcoming_sessions": upcoming_sessions,
        "course_stats": course_stats,
    }
    return render(request, "dashboard/teacher.html", context)
