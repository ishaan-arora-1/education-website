from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="mandatory",
    ACCOUNT_EMAIL_REQUIRED=True,
    ACCOUNT_USERNAME_REQUIRED=False,
    ACCOUNT_AUTHENTICATION_METHOD="email",
    ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE=True,
)
class SignupFormTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_url = reverse("account_signup")
        # Mock captcha validation
        patcher = patch("captcha.fields.CaptchaField.clean", return_value=True)
        self.mock_captcha = patcher.start()
        self.addCleanup(patcher.stop)

    def test_signup_form_validation(self):
        """Test form validation for invalid submissions"""
        # Test empty form
        response = self.client.post(self.signup_url, {})
        self.assertEqual(response.status_code, 200)
        self.assertIn("This field is required.", str(response.context["form"].errors["email"]))

        # Test invalid email
        data = {
            "email": "invalid-email",
            "first_name": "Test",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "testpass123",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Enter a valid email address.",
            str(response.context["form"].errors["email"]),
        )

    @patch("allauth.account.signals.email_confirmed")
    @patch("allauth.account.signals.user_signed_up")
    def test_successful_signup_as_student(self, mock_signed_up, mock_email_confirmed):
        """Test successful signup as a student"""
        data = {
            "email": "student@example.com",
            "first_name": "Student",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "testpass123",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 302)  # Should redirect after successful signup

        # Verify user was created
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.email, "student@example.com")
        self.assertFalse(user.profile.is_teacher)

        # Verify email address
        email = EmailAddress.objects.get(user=user, email=user.email)
        email.verified = True
        email.save()
        mock_email_confirmed.send()
        mock_signed_up.send(sender=user.__class__, request=None, user=user)

    @patch("allauth.account.signals.email_confirmed")
    @patch("allauth.account.signals.user_signed_up")
    def test_successful_signup_as_teacher(self, mock_signed_up, mock_email_confirmed):
        """Test successful signup as a teacher"""
        data = {
            "email": "teacher@example.com",
            "first_name": "Teacher",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "testpass123",
            "is_teacher": "on",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 302)  # Should redirect after successful signup

        # Verify user was created
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.email, "teacher@example.com")
        self.assertTrue(user.profile.is_teacher)

        # Verify email address
        email = EmailAddress.objects.get(user=user, email=user.email)
        self.assertFalse(email.verified)  # Should be unverified initially

        # Verify response redirects to confirm-email URL
        self.assertTrue("/accounts/confirm-email/" in response.url)

        # Simulate email verification
        email.verified = True
        email.save()
        mock_email_confirmed.send()
        mock_signed_up.send(sender=user.__class__, request=None, user=user)
