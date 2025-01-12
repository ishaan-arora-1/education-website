from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from web.forms import CourseCreationForm, SessionForm, UserRegistrationForm
from web.models import Course, Subject


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class UserRegistrationFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Mock stripe module
        cls.stripe_patcher = patch("web.views.stripe")
        cls.mock_stripe = cls.stripe_patcher.start()
        # Mock CAPTCHA field
        cls.captcha_patcher = patch("captcha.fields.CaptchaField.clean", return_value=True)
        cls.mock_captcha = cls.captcha_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.stripe_patcher.stop()
        cls.captcha_patcher.stop()
        super().tearDownClass()

    def test_valid_registration_form(self):
        """Test user registration with valid data"""
        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "testpass123",
            "is_teacher": False,
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_registration_form(self):
        """Test user registration with invalid data"""
        # Test with mismatched passwords
        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "differentpass123",
            "is_teacher": False,
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

        # Test with invalid email
        form_data = {
            "username": "newuser",
            "email": "invalid-email",
            "first_name": "New",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "testpass123",
            "is_teacher": False,
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class CourseCreationFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Mock stripe module
        cls.stripe_patcher = patch("web.views.stripe")
        cls.mock_stripe = cls.stripe_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.stripe_patcher.stop()
        super().tearDownClass()

    def setUp(self):
        self.User = get_user_model()
        self.teacher = self.User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        # Update existing profile instead of creating a new one
        self.teacher.profile.is_teacher = True
        self.teacher.profile.save()

        # Create a test subject
        self.subject = Subject.objects.create(
            name="Programming5",
            slug="programming5",
            description="Programming courses",
            icon="fas fa-code",
        )

    def test_valid_course_creation_form(self):
        """Test course creation with valid data"""
        form_data = {
            "title": "New Course",
            "description": "Course Description",
            "learning_objectives": "Course Objectives",
            "price": 99.99,
            "max_students": 50,
            "subject": self.subject.id,  # Use subject ID instead of string
            "level": "beginner",
            "teacher": self.teacher.id,
        }
        form = CourseCreationForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_invalid_course_creation_form(self):
        """Test course creation with invalid data"""
        # Test with negative price
        form_data = {
            "title": "New Course",
            "description": "Course Description",
            "learning_objectives": "Course Objectives",
            "price": -99.99,
            "max_students": 50,
            "subject": self.subject.id,  # Use subject ID instead of string
            "level": "beginner",
            "teacher": self.teacher.id,
        }
        form = CourseCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("price", form.errors)

        # Test with invalid subject
        form_data["price"] = 99.99
        form_data["subject"] = 999  # Use non-existent subject ID
        form = CourseCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("subject", form.errors)


class SessionFormTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.teacher = self.User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        self.teacher.profile.is_teacher = True
        self.teacher.profile.save()

        # Create test subject
        self.subject = Subject.objects.create(
            name="Programming6",
            slug="programming6",
            description="Programming courses",
            icon="fas fa-code",
        )

        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.teacher,
            learning_objectives="Test Objectives",
            price=99.99,
            max_students=50,
            subject=self.subject,  # Use Subject instance instead of string
            level="beginner",
        )

    def test_valid_session_form(self):
        """Test session creation with valid data"""
        form_data = {
            "course": self.course.id,
            "title": "Test Session",
            "description": "Test Session Description",
            "start_time": timezone.now() + timezone.timedelta(days=1),
            "end_time": timezone.now() + timezone.timedelta(days=1, hours=2),
            "is_virtual": True,
            "meeting_link": "https://meet.google.com/abc-defg-hij",
            "max_participants": 20,
            "location": "",  # Empty for virtual sessions
        }
        form = SessionForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_invalid_session_form(self):
        """Test session creation with invalid data"""
        # Test case 1: end time before start time
        start_time = timezone.now() + timezone.timedelta(days=1)
        end_time = start_time - timezone.timedelta(hours=1)
        form_data = {
            "course": self.course.id,
            "title": "Test Session",
            "description": "Test Session Description",
            "start_time": start_time,
            "end_time": end_time,
            "is_virtual": True,
            "meeting_link": "https://meet.google.com/abc-defg-hij",
            "max_participants": 20,
        }
        form = SessionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("end_time", form.errors)

        # Test case 2: virtual session without meeting link
        form_data.update(
            {
                "end_time": start_time + timezone.timedelta(hours=2),
                "meeting_link": "",
            }
        )
        form = SessionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("meeting_link", form.errors)

        # Test case 3: in-person session without location
        form_data.update(
            {
                "is_virtual": False,
                "location": "",
            }
        )
        form = SessionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("location", form.errors)
