from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from web.forms import (
    BlogCommentForm,
    CourseCreationForm,
    CourseReviewForm,
    CourseSearchForm,
    CourseUpdateForm,
    LearningInquiryForm,
    MaterialUploadForm,
    MessageForm,
    ProfileUpdateForm,
    SessionForm,
    StudyGroupForm,
    TeachingInquiryForm,
    TopicCreationForm,
    UserRegistrationForm,
)
from web.models import Course, ForumCategory, Subject, User


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


class CourseSearchFormTests(TestCase):
    def test_valid_search_form(self):
        """Test course search with valid data"""
        form_data = {
            "query": "python",
            "min_price": "0",
            "max_price": "100",
            "subject": "",
        }
        form = CourseSearchForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_search_form(self):
        """Test course search with invalid data"""
        form_data = {
            "min_price": "invalid",
            "max_price": "invalid",
        }
        form = CourseSearchForm(data=form_data)
        self.assertFalse(form.is_valid())


class CourseUpdateFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="teacher",
            password="testpass123",
        )
        # Set teacher status through profile
        self.user.profile.is_teacher = True
        self.user.profile.save()

        self.subject = Subject.objects.create(name="Test Subject")
        self.course = Course.objects.create(
            title="Test Course",
            teacher=self.user,
            subject=self.subject,
            price=99.99,
            max_students=50,
            description="Test description",
            learning_objectives="Test objectives",
            level="beginner",
            tags="test,course",
            prerequisites="None",
        )

    def test_valid_update_form(self):
        """Test course update with valid data"""
        form_data = {
            "title": "Updated Course",
            "description": "New description",
            "learning_objectives": "New objectives",
            "prerequisites": "Updated prerequisites",
            "price": "149.99",
            "max_students": 75,
            "subject": self.subject.id,
            "level": "intermediate",
            "tags": "updated,test,course",
        }
        form = CourseUpdateForm(data=form_data, instance=self.course)
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_invalid_update_form(self):
        """Test course update with invalid data"""
        form_data = {
            "title": "",  # Title is required
            "price": "invalid",
            "max_students": -1,  # Invalid value
            "description": "",  # Description is required
            "learning_objectives": "",  # Learning objectives are required
        }
        form = CourseUpdateForm(data=form_data, instance=self.course)
        self.assertFalse(form.is_valid())


class CourseReviewFormTests(TestCase):
    def test_valid_review_form(self):
        """Test course review with valid data"""
        form_data = {
            "rating": 5,
            "comment": "Great course!",
        }
        form = CourseReviewForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_review_form(self):
        """Test course review with invalid data"""
        form_data = {
            "rating": 6,  # Invalid rating
            "comment": "",  # Comment required
        }
        form = CourseReviewForm(data=form_data)
        self.assertFalse(form.is_valid())


class MaterialUploadFormTests(TestCase):
    def test_valid_upload_form(self):
        """Test material upload with valid data"""
        test_file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        form_data = {
            "title": "Lecture Notes",
            "description": "Week 1 notes",
        }
        file_data = {"file": test_file}
        form = MaterialUploadForm(data=form_data, files=file_data)
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_invalid_upload_form(self):
        """Test material upload with invalid data"""
        form_data = {
            "title": "",  # Title required
        }
        form = MaterialUploadForm(data=form_data)
        self.assertFalse(form.is_valid())


class TopicCreationFormTests(TestCase):
    def setUp(self):
        self.category = ForumCategory.objects.create(name="General Discussion")

    def test_valid_topic_form(self):
        """Test topic creation with valid data"""
        form_data = {
            "title": "New Topic",
            "content": "Topic content here",
        }
        form = TopicCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_topic_form(self):
        """Test topic creation with invalid data"""
        form_data = {
            "title": "",  # Title required
            "content": "",  # Content required
        }
        form = TopicCreationForm(data=form_data)
        self.assertFalse(form.is_valid())


class StudyGroupFormTests(TestCase):
    def test_valid_group_form(self):
        """Test study group creation with valid data"""
        form_data = {
            "name": "Python Study Group",
            "description": "Weekly study sessions",
            "max_members": 10,
            "is_private": False,
        }
        form = StudyGroupForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_group_form(self):
        """Test study group creation with invalid data"""
        form_data = {
            "name": "",  # Name required
            "max_members": 1,  # Too few members
        }
        form = StudyGroupForm(data=form_data)
        self.assertFalse(form.is_valid())


class BlogCommentFormTests(TestCase):
    def test_valid_comment_form(self):
        """Test blog comment with valid data"""
        form_data = {
            "content": "Great article!",
        }
        form = BlogCommentForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_comment_form(self):
        """Test blog comment with invalid data"""
        form_data = {
            "content": "",  # Content required
        }
        form = BlogCommentForm(data=form_data)
        self.assertFalse(form.is_valid())


class MessageFormTests(TestCase):
    def test_valid_message_form(self):
        """Test message with valid data"""
        form_data = {
            "content": "Hello there!",
        }
        form = MessageForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_message_form(self):
        """Test message with invalid data"""
        form_data = {
            "content": "",  # Content required
        }
        form = MessageForm(data=form_data)
        self.assertFalse(form.is_valid())


class LearningInquiryFormTests(TestCase):
    def test_valid_inquiry_form(self):
        """Test learning inquiry with valid data"""
        form_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "interests": "Python, Web Development",
            "experience_level": "beginner",
        }
        form = LearningInquiryForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_inquiry_form(self):
        """Test learning inquiry with invalid data"""
        form_data = {
            "name": "",  # Name required
            "email": "invalid-email",  # Invalid email
        }
        form = LearningInquiryForm(data=form_data)
        self.assertFalse(form.is_valid())


class TeachingInquiryFormTests(TestCase):
    def test_valid_inquiry_form(self):
        """Test teaching inquiry with valid data"""
        form_data = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "expertise": "Machine Learning",
            "experience": "5 years teaching experience",
        }
        form = TeachingInquiryForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_inquiry_form(self):
        """Test teaching inquiry with invalid data"""
        form_data = {
            "name": "",  # Name required
            "email": "invalid-email",  # Invalid email
        }
        form = TeachingInquiryForm(data=form_data)
        self.assertFalse(form.is_valid())


class ProfileUpdateFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_valid_profile_form(self):
        """Test profile update with valid data"""
        form_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "bio": "Python developer",
        }
        form = ProfileUpdateForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_invalid_profile_form(self):
        """Test profile update with invalid data"""
        form_data = {
            "email": "invalid-email",  # Invalid email
        }
        form = ProfileUpdateForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())
