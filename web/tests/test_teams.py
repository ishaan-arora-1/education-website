from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from web.models import TeamGoal, TeamGoalMember, TeamInvite


class TeamGoalTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create users
        self.user1 = User.objects.create_user(username="testuser1", password="testpassword", email="test1@example.com")
        self.user2 = User.objects.create_user(username="testuser2", password="testpassword", email="test2@example.com")
        
        # Log in user1
        self.client.login(username="testuser1", password="testpassword")
        
        # Create a team goal
        self.team_goal = TeamGoal.objects.create(
            title="Test Team Goal",
            description="Testing team collaboration",
            creator=self.user1,
            deadline=timezone.now() + timezone.timedelta(days=7)
        )
        
        # Add user1 as a team leader
        self.member = TeamGoalMember.objects.create(
            team_goal=self.team_goal,
            user=self.user1,
            role="leader"
        )

    def test_team_goal_list(self):
        """Test the team goals listing page works correctly."""
        response = self.client.get(reverse("team_goals"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Team Goal")
        
    def test_team_goal_detail(self):
        """Test the team goal detail page works correctly."""
        response = self.client.get(reverse("team_goal_detail", args=[self.team_goal.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Team Goal")
        self.assertContains(response, "Testing team collaboration")
        
    def test_create_team_goal(self):
        """Test creating a new team goal."""
        data = {
            "title": "New Team Goal",
            "description": "New Description",
            "deadline": (timezone.now() + timezone.timedelta(days=14)).strftime("%Y-%m-%dT%H:%M")
        }
        response = self.client.post(reverse("create_team_goal"), data)
        self.assertEqual(TeamGoal.objects.count(), 2)
        new_goal = TeamGoal.objects.get(title="New Team Goal")
        self.assertEqual(new_goal.creator, self.user1)
        self.assertEqual(new_goal.members.count(), 1)  # Creator should be added as member
        
    def test_team_invite(self):
        """Test inviting a user to a team goal."""
        data = {
            "recipient": self.user2.id,
            "recipient_search": self.user2.username
        }
        response = self.client.post(
            reverse("team_goal_detail", args=[self.team_goal.id]), 
            data
        )
        self.assertEqual(TeamInvite.objects.count(), 1)
        invite = TeamInvite.objects.first()
        self.assertEqual(invite.sender, self.user1)
        self.assertEqual(invite.recipient, self.user2)
        
    def test_accept_invite(self):
        """Test accepting a team invitation."""
        # Create an invite
        invite = TeamInvite.objects.create(
            goal=self.team_goal,
            sender=self.user1,
            recipient=self.user2
        )
        
        # Switch to user2
        self.client.logout()
        self.client.login(username="testuser2", password="testpassword")
        
        # Accept the invite
        response = self.client.post(reverse("accept_team_invite", args=[invite.id]))
        
        # Check that user2 is now a member
        self.assertTrue(TeamGoalMember.objects.filter(team_goal=self.team_goal, user=self.user2).exists())
        
        # Check that invite is now marked as accepted
        invite.refresh_from_db()
        self.assertEqual(invite.status, "accepted")
        
    def test_mark_contribution(self):
        """Test marking a contribution as completed."""
        response = self.client.post(reverse("mark_team_contribution", args=[self.team_goal.id]))
        self.member.refresh_from_db()
        self.assertTrue(self.member.completed)
        self.assertIsNotNone(self.member.completed_at)