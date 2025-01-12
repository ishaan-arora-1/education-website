from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from web.models import Course, Profile, Subject


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class BaseViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create teacher user and profile
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="teacherpass123",
        )
        self.teacher_profile, _ = Profile.objects.get_or_create(
            user=self.teacher,
            defaults={"is_teacher": True},
        )
        # Create student user and profile
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="studentpass123",
        )
        self.student_profile, _ = Profile.objects.get_or_create(
            user=self.student,
            defaults={"is_teacher": False},
        )
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
        self.client = Client()
        # Create test user
        self.username = "testuser"
        self.email = "test@example.com"
        self.password = "testpass123"
        # Create user with username (required) but login will use email
        self.user = User.objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password,
        )
        # Verify email for allauth
        EmailAddress.objects.create(
            user=self.user,
            email=self.email,
            primary=True,
            verified=True,
        )
        self.login_url = reverse("account_login")

    def test_successful_login_with_email(self):
        """Test that a user can successfully login with email and password"""
        # First, ensure user is not logged in
        self.assertFalse(self.client.session.get("_auth_user_id"))

        # Debug prints for user setup
        print("\nDEBUG USER SETUP:")
        print(f"Email: {self.email}")
        print(f"Password: {self.password}")
        print(f"User exists: {User.objects.filter(email=self.email).exists()}")
        print(f"Email verified: {EmailAddress.objects.filter(email=self.email, verified=True).exists()}")

        # Verify email is primary
        email_obj = EmailAddress.objects.get(email=self.email)
        print(f"Email is primary: {email_obj.primary}")
        print(f"User active: {self.user.is_active}")

        # Get CSRF token
        response = self.client.get(self.login_url)
        csrftoken = response.cookies["csrftoken"].value

        # Attempt login with CSRF token
        response = self.client.post(
            self.login_url,
            {
                "login": self.email,
                "password": self.password,
                "csrfmiddlewaretoken": csrftoken,
            },
            HTTP_X_CSRFTOKEN=csrftoken,
        )

        # Debug prints for response
        print("\nDEBUG LOGIN RESPONSE:")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        if response.context and "form" in response.context:
            print(f"Form Errors: {response.context['form'].errors}")
            form = response.context["form"]
            print(f"Form Data: {form.data}")
            print(f"Form is Valid: {form.is_valid()}")
            print(f"Form Cleaned Data: {form.cleaned_data if form.is_valid() else None}")
        print(f"Session: {self.client.session.items()}")
        print(f"Cookies: {response.cookies}")

        # Check redirect status code
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("index"))

        # Verify user is logged in
        self.assertTrue(self.client.session.get("_auth_user_id"))
