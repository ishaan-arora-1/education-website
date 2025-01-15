from decimal import Decimal
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from web.forms import LearnForm, TeachForm
from web.models import Course, Profile, Session, Subject
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
