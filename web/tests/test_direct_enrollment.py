from django.urls import reverse
from django.contrib.auth.models import User
from django.test import TestCase
from web.models import Course, Enrollment, Subject
from django.utils.text import slugify

class DirectEnrollmentTest(TestCase):
    def setUp(self):
        # Create a Subject first so that the Course foreign key is valid.
        self.subject = Subject.objects.create(
            name="Test Subject", 
            slug="test-subject", 
            description="Test subject description"
        )
        # Create a teacher with a unique email.
        self.teacher = User.objects.create_user(
            username="teacher1", password="pass", email="teacher1@example.com"
        )
        self.teacher.profile.is_teacher = True
        self.teacher.profile.save()

        # Create a course for the teacher, now with a valid subject.
        self.course = Course.objects.create(
            title="Test Course",
            slug=slugify("Test Course"),
            teacher=self.teacher,
            description="A test course",
            learning_objectives="Learn testing",
            prerequisites="None",
            price=10.00,
            allow_individual_sessions=False,
            invite_only=False,
            max_students=30,
            subject=self.subject,  # Use the subject instance we created.
            level="beginner",
            tags="test,course"
        )

        # Create a student with a unique email.
        self.student = User.objects.create_user(
            username="student1", password="pass", email="student1@example.com"
        )

    def test_get_add_student_view(self):
        # Teacher logs in and retrieves the form.
        self.client.login(username="teacher1", password="pass")
        url = reverse("add_student", args=[self.course.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enroll Student in")

    def test_post_add_student_view(self):
        self.client.login(username="teacher1", password="pass")
        url = reverse("add_student", args=[self.course.slug])
        data = {"student": self.student.id}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        # Verify that the enrollment is created.
        self.assertTrue(Enrollment.objects.filter(course=self.course, student=self.student).exists())

    def test_prevent_duplicate_enrollment(self):
        # Enroll the student once.
        Enrollment.objects.create(course=self.course, student=self.student, status="approved")
        self.client.login(username="teacher1", password="pass")
        url = reverse("add_student", args=[self.course.slug])
        data = {"student": self.student.id}
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, "already enrolled", status_code=200)
