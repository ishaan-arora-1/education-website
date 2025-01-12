from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from web.models import Course, Enrollment, Profile, Session, Subject


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class BaseViewTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Create teacher user and profile
        self.teacher = User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher, defaults={"is_teacher": True})

        # Create student user and profile
        self.student = User.objects.create_user(
            username="student", email="student@example.com", password="studentpass123"
        )
        self.student_profile, _ = Profile.objects.get_or_create(user=self.student, defaults={"is_teacher": False})

        # Create test subject
        self.subject = Subject.objects.create(
            name="Programming2",
            slug="programming2",
            description="Programming courses",
            icon="fas fa-code",
        )

        # Create test course
        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.teacher,
            learning_objectives="Test Objectives",
            price=99.99,
            max_students=50,
            subject=self.subject,
            level="beginner",
        )


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class SessionViewTests(BaseViewTest):
    def setUp(self):
        super().setUp()

        # Mock Google credentials and calendar sync
        self.google_patcher = patch("web.calendar_sync.google_calendar_api", return_value=True)
        self.mock_google = self.google_patcher.start()

        # Mock create calendar event
        self.calendar_event_patcher = patch(
            "web.calendar_sync.create_calendar_event",
            return_value="calendar_event_123",
        )
        self.mock_calendar_event = self.calendar_event_patcher.start()

        # Create enrollment first
        self.enrollment = Enrollment.objects.create(student=self.student, course=self.course, status="approved")

        # Then create session
        self.session = Session.objects.create(
            course=self.course,
            title="Test Session",
            description="Test Description",
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=2),
            is_virtual=True,
            meeting_link="https://meet.google.com/abc-defg-hij",
        )

    def tearDown(self):
        self.google_patcher.stop()
        self.calendar_event_patcher.stop()
        super().tearDown()

    def test_session_detail_view(self):
        # Login first
        self.client.force_login(self.student)

        # Get session detail
        url = reverse("session_detail", args=[self.session.id])
        response = self.client.get(url)

        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "web/study/session_detail.html")
        self.assertContains(response, self.session.title)
