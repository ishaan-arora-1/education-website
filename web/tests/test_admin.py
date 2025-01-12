from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

User = get_user_model()


@override_settings(DEBUG=True, SLACK_WEBHOOK_URL=None)
class AdminTests(TestCase):
    def setUp(self):
        # Create superuser for admin access
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.client = Client()
        success = self.client.login(username="admin", password="adminpass123")
        self.assertTrue(success, "Login failed")

    def test_create_user_through_admin(self):
        """Test that a user can be created through the admin interface"""
        initial_user_count = User.objects.count()
        self.assertEqual(initial_user_count, 1)  # Just the admin user

        # Step 1: Create the user with initial data
        initial_data = {
            "username": "testuser",
            "password1": "testpass123",
            "password2": "testpass123",
            "usable_password": "true",
            "profile-TOTAL_FORMS": "1",
            "profile-INITIAL_FORMS": "0",
            "profile-MIN_NUM_FORMS": "0",
            "profile-MAX_NUM_FORMS": "1",
            "profile-0-id": "",
            "profile-0-user": "",
            "profile-0-bio": "Test bio",
            "profile-0-expertise": "Test expertise",
            "profile-0-is_teacher": "1",
            "_save": "Save",
        }

        response = self.client.post("/en/admin/auth/user/add/", initial_data, follow=True)
        print("Step 1 - Response status code:", response.status_code)
        print("Step 1 - Response content:", response.content.decode())
        print("Step 1 - Final redirect chain:", response.redirect_chain)
        if response.context and "form" in response.context:
            print("Step 1 - Form errors:", response.context["form"].errors)

        # Verify the user was created
        user = User.objects.get(username="testuser")
        self.assertEqual(User.objects.count(), 2)  # Admin + new user

        # Verify the profile was created
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.bio, "Test bio")
        self.assertEqual(user.profile.expertise, "Test expertise")
        self.assertTrue(user.profile.is_teacher)
