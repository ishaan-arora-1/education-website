from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from web.models import Course, Profile, Session, Subject


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
            price=29.99,
        )
        self.cart_url = reverse("cart_view")
        self.add_course_url = reverse("add_course_to_cart", args=[self.course.id])
        self.add_session_url = reverse("add_session_to_cart", args=[self.session.id])
        print("[CartCheckoutTest] setUp completed.")

    @patch("web.views.notify_teacher_new_enrollment")
    @patch("web.views.send_enrollment_confirmation")
    @patch("web.views.send_welcome_email")
    @patch("web.views.stripe.PaymentIntent.retrieve")
    @patch("web.views.stripe.PaymentIntent.create")
    @patch("web.views.os.path.exists", return_value=True)
    @patch("web.views.requests.post")
    def test_guest_cart_checkout_flow(
        self,
        mock_requests_post,
        mock_path_exists,
        mock_create_intent,
        mock_payment_intent,
        mock_welcome_email,
        mock_send_confirm,
        mock_notify,
    ):
        """Test that a guest user can add items to cart and checkout"""
        print("\n[CartCheckoutTest] Running test_guest_cart_checkout_flow...")

        # Mock Slack webhook response
        mock_requests_post.return_value.status_code = 200
        print("[CartCheckoutTest] Slack webhook response mocked to 200.")

        # Mock payment intent retrieval and creation
        mock_payment_intent.return_value = type("MockIntent", (), {"receipt_email": "newuser@example.com"})
        mock_create_intent.return_value = type("MockIntent", (), {"client_secret": "dummy_client_secret"})
        print("[CartCheckoutTest] Stripe PaymentIntent mocked.")

        # Ensure session middleware is working
        print("[CartCheckoutTest] Saving session middleware...")
        session = self.client.session
        session.save()

        # Add course to cart
        print("[CartCheckoutTest] Adding course to cart...")
        response = self.client.post(self.add_course_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.cart_url)
        print("[CartCheckoutTest] Course added, redirected to cart.")

        # Add session to cart
        print("[CartCheckoutTest] Adding session to cart...")
        response = self.client.post(self.add_session_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.cart_url)
        print("[CartCheckoutTest] Session added, redirected to cart.")

        # Check cart contents
        print("[CartCheckoutTest] Checking cart contents...")
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, 200)
        cart = response.context["cart"]
        print("[CartCheckoutTest] Cart retrieved. Number of items:", cart.items.count())
        self.assertEqual(cart.items.count(), 2)

        # Verify cart items
        cart_items = cart.items.all()
        has_course = any(item.course == self.course for item in cart_items)
        has_session = any(item.session == self.session for item in cart_items)
        self.assertTrue(has_course)
        self.assertTrue(has_session)
        print("[CartCheckoutTest] Cart items verified: course & session are present.")

        # Create payment intent
        intent_url = reverse("create_cart_payment_intent")
        print("[CartCheckoutTest] Creating payment intent...")
        response = self.client.post(intent_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("clientSecret", response.json())
        print("[CartCheckoutTest] Payment intent created, clientSecret found.")

        # Simulate successful payment and checkout
        payment_intent_id = "pi_test_123"
        checkout_url = reverse("checkout_success")
        print("[CartCheckoutTest] Simulating checkout success...")
        response = self.client.get(checkout_url, {"payment_intent": payment_intent_id})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("account_login"))
        print("[CartCheckoutTest] Checkout success simulation complete, user redirected to login.")

        # Verify mocks were called
        print("[CartCheckoutTest] Verifying mocked calls...")
        mock_welcome_email.assert_called_once()
        mock_send_confirm.assert_called()
        mock_notify.assert_called()
        print("[CartCheckoutTest] All mocks called as expected.")

        print("[CartCheckoutTest] test_guest_cart_checkout_flow completed successfully!")
