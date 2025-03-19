import uuid
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from web.models import Certificate, Course, Enrollment, Subject
class CertificateDashboardTest(TestCase):
    def setUp(self):
        # Create a test user.
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass",
            email="test@example.com",
            first_name="Test",
            last_name="User"
        )
        # Create a test subject.
        self.subject = Subject.objects.create(name="Test Subject", slug="test-subject")
        # Create a test course.
        self.course = Course.objects.create(
            title="Testing Course",
            slug="testing-course",
            teacher=self.user,
            description="Test Description",
            learning_objectives="Test Objectives",
            prerequisites="None",
            price=100.00,
            allow_individual_sessions=False,
            invite_only=False,
            status="published",
            max_students=10,
            subject=self.subject,
            level="beginner",
            tags="test",
            is_featured=False,
        )
        # Create an enrollment with status "completed"
        self.enrollment = Enrollment.objects.create(
            student=self.user, course=self.course, status="completed"
        )
        # Create a certificate for the course manually
        self.certificate_uuid = uuid.UUID("9775783c-9f74-4aeb-8a47-5128a3b7b73a")
        self.certificate = Certificate.objects.create(
            user=self.user, course=self.course, certificate_id=self.certificate_uuid
        )
        # Log in the test client as the certificate owner
        self.client.force_login(self.user)

    def test_certificate_creation(self):
        # Basic test for certificate creation and string representation
        certificate = Certificate.objects.create(
            user=self.user,
            course=self.course,
        )
        self.assertIsNotNone(certificate.certificate_id)
        expected_str = f"Certificate for {self.user.username} - {self.course.title}"
        self.assertEqual(str(certificate), expected_str)

    def test_certificate_detail_view(self):
        # Test that the certificate detail view renders correctly for the owner
        url = reverse("certificate_detail", args=[str(self.certificate.certificate_id)])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Certificate of Completion")
        self.assertContains(response, self.user.get_full_name())
        self.assertContains(response, self.course.title)

    def test_dashboard_certificates_section(self):
        """
        Test that the student dashboard displays the certificate section correctly.
        For testing the "Generate Certificate" button, we simulate the case where
        no certificate exists for a completed enrollment.
        """
        # Delete the existing certificate to simulate that the certificate hasn't been generated
        self.certificate.delete()
        url = reverse("student_dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check that the generate button appears.
        # Since the template renders a button with text "Generate" for each enrollment,
        # we look for that button text.
        self.assertContains(response, "Generate")
        # Optionally, check that the course title is correctly displayed in the generate section.
        expected_course_text = f"Course: <span class=\"font-bold\">{self.course.title}</span>"
        self.assertContains(response, expected_course_text)