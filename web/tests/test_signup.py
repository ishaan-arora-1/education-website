from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class SignupFormTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_url = reverse("account_signup")

    def test_signup_page_loads(self):
        """Test that the signup page loads correctly"""
        response = self.client.get(self.signup_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/signup.html")

        # Check for required form fields
        self.assertContains(response, 'id="id_username"')
        self.assertContains(response, 'id="id_email"')
        self.assertContains(response, 'id="id_first_name"')
        self.assertContains(response, 'id="id_last_name"')
        self.assertContains(response, 'id="id_password1"')
        self.assertContains(response, 'id="id_is_teacher"')

        # Check for the illustration and welcome text
        self.assertContains(response, "fa-graduation-cap")
        self.assertContains(response, "Join our community")

    def test_signup_form_validation(self):
        """Test form validation for invalid submissions"""
        # Test empty form
        response = self.client.post(self.signup_url, {})
        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)
        self.assertIn("This field is required.", response.context["form"].errors["username"])

        # Test invalid email
        data = {
            "username": "testuser",
            "email": "invalid-email",
            "first_name": "Test",
            "last_name": "User",
            "password1": "testpass123",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertIn("Enter a valid email address.", response.context["form"].errors["email"])

        # Test weak password
        data["email"] = "test@example.com"
        data["password1"] = "weak"
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This password is too short")

    def test_successful_signup_as_student(self):
        """Test successful signup as a student"""
        data = {
            "username": "student",
            "email": "student@example.com",
            "first_name": "Student",
            "last_name": "User",
            "password1": "testpass123",
            "captcha": "dummy",
        }
        self.client.post(self.signup_url, data)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.username, "student")
        self.assertEqual(user.email, "student@example.com")
        self.assertFalse(user.profile.is_teacher)

    def test_successful_signup_as_teacher(self):
        """Test successful signup as a teacher"""
        data = {
            "username": "teacher",
            "email": "teacher@example.com",
            "first_name": "Teacher",
            "last_name": "User",
            "password1": "testpass123",
            "is_teacher": "on",
            "captcha": "dummy",
        }
        self.client.post(self.signup_url, data)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.first()
        self.assertEqual(user.username, "teacher")
        self.assertEqual(user.email, "teacher@example.com")
        self.assertTrue(user.profile.is_teacher)
