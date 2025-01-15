from decimal import Decimal
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from web.forms import LearnForm, TeachForm
from web.models import Course, Enrollment, Profile, Session, SessionAttendance, Subject
from web.utils import get_or_create_cart


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class BaseViewTest(TestCase):
    def setUp(self):
        # Debug statement
        print("\n[BaseViewTest] setUp starting...")

        self.client = Client()

        # Create teacher user and profile
        print("[BaseViewTest] Creating teacher user...")
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="teacherpass123",
        )
        self.teacher_profile, created_teacher_profile = Profile.objects.get_or_create(
            user=self.teacher,
            defaults={"is_teacher": True},
        )
        print(f"[BaseViewTest] Teacher profile created: {created_teacher_profile}")

        # Create student user and profile
        print("[BaseViewTest] Creating student user...")
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="studentpass123",
        )
        self.student_profile, created_student_profile = Profile.objects.get_or_create(
            user=self.student,
            defaults={"is_teacher": False},
        )
        print(f"[BaseViewTest] Student profile created: {created_student_profile}")

        # Create test subject
        print("[BaseViewTest] Creating test subject...")
        self.subject = Subject.objects.create(
            name="Programming2",
            slug="programming2",
            description="Programming courses",
            icon="fas fa-code",
        )
        print(f"[BaseViewTest] Subject created: {self.subject.name}")

        # Create test course
        print("[BaseViewTest] Creating test course...")
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
        print(f"[BaseViewTest] Course created: {self.course.title}")

        print("[BaseViewTest] setUp completed.")


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="mandatory",
    ACCOUNT_EMAIL_REQUIRED=True,
    ACCOUNT_USERNAME_REQUIRED=True,
    ACCOUNT_AUTHENTICATION_METHOD="email",
    ACCOUNT_RATE_LIMITS={
        "login_attempt": "5/5m",
        "login_failed": "3/5m",
        "signup": "5/h",
        "send_email": "5/5m",
        "change_email": "3/h",
    },
)
class AuthenticationTests(TestCase):
    def setUp(self):
        # Debug statement
        print("\n[AuthenticationTests] setUp starting...")

        self.client = Client()
        self.username = "testuser"
        self.email = "test@example.com"
        self.password = "testpass123"

        # Create user with username (required) but login will use email
        print("[AuthenticationTests] Creating test user...")
        self.user = User.objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password,
        )

        # Verify email for allauth
        print("[AuthenticationTests] Verifying user email in allauth...")
        EmailAddress.objects.create(
            user=self.user,
            email=self.email,
            primary=True,
            verified=True,
        )
        self.login_url = reverse("account_login")

        print("[AuthenticationTests] setUp completed.")

    def test_successful_login_with_email(self):
        """Test that a user can successfully login with email and password"""
        print("\n[AuthenticationTests] Running test_successful_login_with_email...")

        self.client.logout()
        print("[AuthenticationTests] Client logged out, fetching login page for CSRF...")

        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        print("[AuthenticationTests] Login page status code:", response.status_code)

        # Attempt login
        login_data = {"login": self.email, "password": self.password}
        print("[AuthenticationTests] Posting login data...")
        response = self.client.post(self.login_url, login_data, follow=True)

        # Check that login was successful
        print("[AuthenticationTests] Checking login status...")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)
        self.assertEqual(response.context["user"].email, self.email)
        print("[AuthenticationTests] User successfully logged in with email!")


@override_settings(
    STRIPE_SECRET_KEY="dummy_key",
    STRIPE_PUBLIC_KEY="dummy_pub_key",
    GOOGLE_CALENDAR_ENABLED=False,
    SLACK_ENABLED=False,
    SLACK_WEBHOOK_URL="https://dummy-slack-url.com",
    GOOGLE_CREDENTIALS_PATH="dummy_path",
)
class CartCheckoutTest(BaseViewTest):
    def setUp(self):
        # First call parent setUp
        print("\n[CartCheckoutTest] setUp starting...")
        super().setUp()

        # Allow individual sessions for the course
        print("[CartCheckoutTest] Allowing individual sessions for course...")
        self.course.allow_individual_sessions = True
        self.course.save()

        # Create test session
        print("[CartCheckoutTest] Creating test session...")
        start = timezone.now() + timezone.timedelta(days=1)
        end = start + timezone.timedelta(hours=1)
        self.session = Session.objects.create(
            course=self.course,
            title="Test Session",
            description="Test Session Description",
            start_time=start,
            end_time=end,
            price=Decimal("29.99"),
        )
        self.cart_url = reverse("cart_view")
        self.add_course_url = reverse("add_course_to_cart", args=[self.course.id])
        self.add_session_url = reverse("add_session_to_cart", args=[self.session.id])

    @patch("web.views.send_welcome_email")
    @patch("stripe.PaymentIntent.retrieve")
    def test_guest_cart_checkout_flow(self, mock_retrieve, mock_welcome_email):
        """Test that a guest user can add items to cart and checkout"""
        print("\n[CartCheckoutTest] Running test_guest_cart_checkout_flow...")
        # Mock the payment intent
        mock_payment_intent = type("PaymentIntent", (), {"status": "succeeded", "receipt_email": "test@example.com"})
        mock_retrieve.return_value = mock_payment_intent
        print(
            "[CartCheckoutTest] Mocked payment intent with "
            f"status={mock_payment_intent.status} and "
            f"receipt_email={mock_payment_intent.receipt_email}"
        )

        # Add course to cart
        print("[CartCheckoutTest] Adding course to cart...")
        response = self.client.post(self.add_course_url)
        self.assertEqual(response.status_code, 302)
        print("[CartCheckoutTest] Course added to cart")

        # Add session to cart
        print("[CartCheckoutTest] Adding session to cart...")
        response = self.client.post(self.add_session_url)
        self.assertEqual(response.status_code, 302)
        print("[CartCheckoutTest] Session added to cart")

        # Check cart contents
        print("[CartCheckoutTest] Checking cart contents...")
        response = self.client.get(self.cart_url)
        cart = get_or_create_cart(response.wsgi_request)
        print(f"[CartCheckoutTest] Cart items count: {cart.items.count()}")
        self.assertEqual(cart.items.count(), 2)
        print(f"[CartCheckoutTest] Cart has course: {cart.items.filter(course=self.course).exists()}")
        self.assertTrue(cart.items.filter(course=self.course).exists())
        print(f"[CartCheckoutTest] Cart has session: {cart.items.filter(session=self.session).exists()}")
        self.assertTrue(cart.items.filter(session=self.session).exists())

        # Process checkout
        print("\n[CartCheckoutTest] Starting checkout with payment_intent_id=pi_test_123")
        response = self.client.get(reverse("checkout_success") + "?payment_intent=pi_test_123")
        print(f"[CartCheckoutTest] Checkout response status: {response.status_code}")
        self.assertEqual(response.status_code, 200)

        # Verify receipt page
        self.assertTemplateUsed(response, "cart/receipt.html")
        self.assertEqual(response.context["payment_intent_id"], "pi_test_123")
        self.assertEqual(response.context["user"].email, "test@example.com")
        self.assertEqual(len(response.context["enrollments"]), 1)
        self.assertEqual(len(response.context["session_enrollments"]), 1)
        expected_total = Decimal("129.98")  # 99.99 for course + 29.99 for session
        self.assertEqual(response.context["total"], expected_total)


class PageLoadTests(BaseViewTest):
    """Test that all important pages load correctly"""

    def setUp(self):
        super().setUp()
        print("\n[PageLoadTests] setUp starting...")
        self.urls_to_test = {
            "index": reverse("index"),
            "subjects": reverse("subjects"),
            "learn": reverse("learn"),
            "teach": reverse("teach"),
            "course_search": reverse("course_search"),
            "cart": reverse("cart_view"),
        }
        self.authenticated_urls = {
            "student_dashboard": reverse("student_dashboard"),
        }
        print("[PageLoadTests] URLs prepared for testing")

    def test_page_loads(self):
        """Test that each page loads with correct template and status code"""
        print("\n[PageLoadTests] Testing page loads...")

        # Expected templates for each URL
        template_map = {
            "index": "index.html",
            "subjects": "subjects.html",
            "learn": "learn.html",
            "teach": "teach.html",
            "course_search": "courses/search.html",
            "cart": "cart/cart.html",
        }

        # Test each URL
        for name, url in self.urls_to_test.items():
            print(f"[PageLoadTests] Testing {name} at {url}")
            response = self.client.get(url)

            # Verify status code
            self.assertEqual(
                response.status_code, 200, f"Failed to load {name} page. Status code: {response.status_code}"
            )

            # Verify template
            self.assertTemplateUsed(response, template_map[name], f"Wrong template used for {name} page")

            print(f"[PageLoadTests] {name} page loaded successfully")

    def test_authenticated_page_loads(self):
        """Test pages that require authentication"""
        print("\n[PageLoadTests] Testing authenticated page loads...")

        # Login as student
        self.client.login(username="student", password="studentpass123")

        # Test student dashboard
        response = self.client.get(self.authenticated_urls["student_dashboard"])
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/student.html")

        print("[PageLoadTests] Authenticated pages loaded successfully")

    def test_unauthenticated_redirects(self):
        """Test that authenticated pages redirect when not logged in"""
        print("\n[PageLoadTests] Testing unauthenticated redirects...")

        # Test student dashboard redirect
        response = self.client.get(self.authenticated_urls["student_dashboard"])
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/en/accounts/login/"))

        print("[PageLoadTests] Unauthenticated redirects working correctly")

    def test_form_pages_have_forms(self):
        """Test that pages with forms have the correct form in context"""
        print("\n[PageLoadTests] Testing form pages...")

        # Test learn page
        response = self.client.get(self.urls_to_test["learn"])
        self.assertTrue("form" in response.context)
        self.assertIsInstance(response.context["form"], LearnForm)

        # Test teach page
        response = self.client.get(self.urls_to_test["teach"])
        self.assertTrue("form" in response.context)
        self.assertIsInstance(response.context["form"], TeachForm)

        print("[PageLoadTests] Form pages verified successfully")


class CourseInvitationTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a teacher
        self.teacher = User.objects.create_user(
            username="testteacher", email="teacher@test.com", password="testpass123"
        )
        # Create a subject
        self.subject = Subject.objects.create(name="Test Subject")
        # Create a course
        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.teacher,
            subject=self.subject,
            price=29.99,
            status="published",
            max_students=50,
        )
        self.invite_url = reverse("invite_student", args=[self.course.id])

    def test_invite_student_view_access(self):
        """Test that only the course teacher can access the invite view"""
        # Unauthenticated user should be redirected to login
        response = self.client.get(self.invite_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/en/accounts/login/"))

        # Create and login a non-teacher user
        User.objects.create_user(username="other", email="other@test.com", password="testpass123")
        self.client.login(username="other", password="testpass123")
        response = self.client.get(self.invite_url)
        self.assertEqual(response.status_code, 302)  # Should be redirected
        self.assertTrue(response.url.startswith("/en/courses/"))

        # Teacher should have access
        self.client.login(username="testteacher", password="testpass123")
        response = self.client.get(self.invite_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/invite.html")

    def test_invite_student_send_invitation(self):
        """Test sending an invitation to a student"""
        self.client.login(username="testteacher", password="testpass123")

        # Send invitation
        data = {"email": "student@test.com", "message": "Please join my course!"}
        response = self.client.post(self.invite_url, data)

        # Check redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("course_detail", args=[self.course.slug]))

        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, f"Invitation to join {self.course.title}")
        self.assertEqual(email.to, ["student@test.com"])

        # Check email content
        self.assertIn(self.course.title, email.body)
        self.assertIn("Please join my course!", email.body)
        self.assertIn(str(self.course.price), email.body)

        # Verify success message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn("Invitation sent", str(messages[0]))


class CourseDetailTests(TestCase):
    def setUp(self):
        """Set up test data for course detail tests"""
        self.client = Client()

        # Create users
        self.teacher = User.objects.create_user(username="teacher", email="teacher@test.com", password="testpass123")
        self.student = User.objects.create_user(username="student", email="student@test.com", password="testpass123")

        # Create subject
        self.subject = Subject.objects.create(
            name="Test Subject",
            slug="test-subject",
            description="Test Description",
        )

        # Create course
        self.course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            teacher=self.teacher,
            description="Test Description",
            learning_objectives="Test Objectives",
            prerequisites="Test Prerequisites",
            price=99.99,
            max_students=50,
            subject=self.subject,
            level="beginner",
            status="published",
            allow_individual_sessions=True,
        )

        # Create sessions
        now = timezone.now()
        self.future_session = Session.objects.create(
            course=self.course,
            title="Future Session",
            description="Future Session Description",
            start_time=now + timezone.timedelta(days=1),
            end_time=now + timezone.timedelta(days=1, hours=1),
            price=29.99,
            is_virtual=True,
            meeting_link="https://meet.test.com",
        )
        self.past_session = Session.objects.create(
            course=self.course,
            title="Past Session",
            description="Past Session Description",
            start_time=now - timezone.timedelta(days=1),
            end_time=now - timezone.timedelta(days=1, hours=1),
            price=29.99,
            location="Test Location",
        )

        # Create enrollment for student
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status="approved",
        )

        # Create attendance for past session
        self.attendance = SessionAttendance.objects.create(
            student=self.student,
            session=self.past_session,
            status="completed",
        )

        # URL for detail page
        self.detail_url = reverse("course_detail", args=[self.course.slug])

    def test_course_detail_page_load(self):
        """Test course detail page loads for different user types"""
        # Test anonymous user
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/detail.html")

        # Test teacher
        self.client.login(username="teacher", password="testpass123")
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_teacher"])

        # Test enrolled student
        self.client.login(username="student", password="testpass123")
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["enrollment"])
        self.assertFalse(response.context["is_teacher"])

    def test_course_information_display(self):
        """Test that course information is correctly displayed"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.context["course"], self.course)
        self.assertContains(response, self.course.title)
        self.assertContains(response, self.course.description)
        self.assertContains(response, self.course.learning_objectives)
        self.assertContains(response, self.course.prerequisites)
        self.assertContains(response, str(self.course.price))
        self.assertContains(response, self.course.get_level_display())
        self.assertContains(response, self.course.subject.name)

    def test_session_display(self):
        """Test that sessions are correctly displayed"""
        response = self.client.get(self.detail_url)
        self.assertContains(response, self.future_session.title)
        self.assertContains(response, self.past_session.title)
        self.assertContains(response, self.future_session.meeting_link)
        self.assertContains(response, self.past_session.location)

        # Test session prices are shown when allow_individual_sessions is True
        self.assertContains(response, str(self.future_session.price))

        # Test virtual/in-person indicators
        self.assertContains(response, "Virtual")
        self.assertContains(response, self.past_session.location)

    def test_teacher_specific_functionality(self):
        """Test functionality available only to teachers"""
        self.client.login(username="teacher", password="testpass123")
        response = self.client.get(self.detail_url)

        # Test edit course link is present
        self.assertContains(response, reverse("update_course", args=[self.course.slug]))

        # Test invite student link is present
        self.assertContains(response, reverse("invite_student", args=[self.course.id]))

        # Test add session link is present
        self.assertContains(response, reverse("add_session", args=[self.course.slug]))

        # Test session management links are present
        self.assertContains(response, reverse("mark_session_attendance", args=[self.future_session.id]))
        self.assertContains(response, reverse("edit_session", args=[self.future_session.id]))

    def test_enrolled_student_functionality(self):
        """Test functionality available to enrolled students"""
        self.client.login(username="student", password="testpass123")
        response = self.client.get(self.detail_url)

        # Test enrollment status is shown
        self.assertContains(response, "You're enrolled!")

        # Test progress link is shown
        self.assertContains(response, reverse("student_dashboard"))

        # Test completed session is marked
        self.assertIn(self.past_session, response.context["completed_sessions"])
        self.assertContains(response, "Completed")

    def test_calendar_display(self):
        """Test that the session calendar is correctly displayed"""
        response = self.client.get(self.detail_url)

        # Test calendar context
        self.assertTrue("calendar_weeks" in response.context)
        self.assertTrue("today" in response.context)

        # Test session dates are marked
        calendar_weeks = response.context["calendar_weeks"]
        session_date = self.future_session.start_time.date()

        # Find the day in calendar that matches the session date
        session_day_found = False
        for week in calendar_weeks:
            for day in week:
                if day["date"] and day["date"] == session_date:
                    self.assertTrue(day["has_session"])
                    session_day_found = True
                    break
            if session_day_found:
                break

        self.assertTrue(session_day_found, "Session date not found in calendar")

    def test_session_completion_form(self):
        """Test session completion form for enrolled students"""
        self.client.login(username="student", password="testpass123")
        response = self.client.get(self.detail_url)

        # Past session should have completion form if not completed
        self.attendance.delete()  # Remove existing completion
        response = self.client.get(self.detail_url)
        self.assertContains(response, f'action="{reverse("mark_session_completed", args=[self.past_session.id])}"')

        # Future session should not have completion form
        self.assertNotContains(response, f'action="{reverse("mark_session_completed", args=[self.future_session.id])}"')
