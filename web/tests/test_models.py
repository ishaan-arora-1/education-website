from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from web.models import Course, Enrollment, Profile, Subject


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class UserModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        super().tearDownClass()

    def setUp(self):
        self.profile, _ = Profile.objects.get_or_create(user=self.user)

    def test_user_creation(self):
        """Test that a user can be created"""
        user = User.objects.get(username="testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpass123"))

    def test_profile_creation_signal(self):
        """Test that a profile is automatically created when a user is created"""
        user = User.objects.get(username="testuser")
        self.assertTrue(hasattr(user, "profile"))
        self.assertIsInstance(user.profile, Profile)

    def test_profile_str(self):
        """Test the string representation of a Profile"""
        user = User.objects.get(username="testuser")
        self.assertEqual(str(user.profile), "testuser's profile")

    def test_profile_fields(self):
        """Test that profile fields can be set and retrieved"""
        user = User.objects.get(username="testuser")
        user.profile.bio = "Test bio"
        user.profile.expertise = "Test expertise"
        user.profile.is_teacher = True
        user.profile.save()

        updated_profile = Profile.objects.get(user=user)
        self.assertEqual(updated_profile.bio, "Test bio")
        self.assertEqual(updated_profile.expertise, "Test expertise")
        self.assertTrue(updated_profile.is_teacher)


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class CourseModelTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="teacherpass123",
        )
        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher, defaults={"is_teacher": True})

        # Create test subject
        self.subject = Subject.objects.create(
            name="Programming3",
            slug="programming3",
            description="Programming courses",
            icon="fas fa-code",
        )

        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.teacher,
            learning_objectives="Test Objectives",
            prerequisites="Test Prerequisites",
            price=99.99,
            max_students=50,
            subject=self.subject,
            level="beginner",
        )

    def test_course_creation(self):
        """Test course creation with valid data"""
        self.assertEqual(self.course.title, "Test Course")
        self.assertEqual(self.course.teacher, self.teacher)
        self.assertEqual(self.course.price, 99.99)
        self.assertEqual(self.course.max_students, 50)
        self.assertEqual(self.course.prerequisites, "Test Prerequisites")
        self.assertEqual(self.course.subject.name, "Programming3")
        self.assertEqual(self.course.level, "beginner")

    def test_course_str(self):
        """Test the string representation of Course"""
        self.assertEqual(str(self.course), "Test Course")

    def test_slug_generation(self):
        """Test that slug is automatically generated"""
        self.assertEqual(self.course.slug, "test-course")


class EnrollmentModelTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="teacherpass123",
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="studentpass123",
        )

        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher, defaults={"is_teacher": True})
        self.student_profile, _ = Profile.objects.get_or_create(user=self.student, defaults={"is_teacher": False})

        self.subject = Subject.objects.create(
            name="Programming4",
            slug="programming4",
            description="Programming courses",
            icon="fas fa-code",
        )

        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.teacher,
            learning_objectives="Test Objectives",
            prerequisites="Test Prerequisites",
            price=99.99,
            max_students=50,
            subject=self.subject,
            level="beginner",
        )

    def test_enrollment_creation(self):
        """Test enrollment creation"""
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status="pending",
        )
        self.assertEqual(enrollment.student, self.student)
        self.assertEqual(enrollment.course, self.course)
        self.assertEqual(enrollment.status, "pending")

    def test_enrollment_str(self):
        """Test the string representation of Enrollment"""
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status="pending",
        )
        expected_str = f"{self.student.username} - {self.course.title}"
        self.assertEqual(str(enrollment), expected_str)
        self.assertEqual(str(enrollment), expected_str)
