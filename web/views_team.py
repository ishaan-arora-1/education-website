from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q
from django.utils import timezone

from .models import TeamGoal, TeamGoalMember, TeamInvite
from .forms import TeamGoalForm, TeamInviteForm

@login_required
def team_goals(request):
    """List all team goals the user is part of or has created."""
    user_goals = TeamGoal.objects.filter(
        Q(creator=request.user) | Q(members__user=request.user)
    ).distinct().order_by('-created_at')
    
    pending_invites = TeamInvite.objects.filter(
        recipient=request.user,
        status='pending'
    ).select_related('team_goal', 'sender')
    
    context = {
        'goals': user_goals,
        'pending_invites': pending_invites,
    }
    return render(request, 'teams/list.html', context)

@login_required
def create_team_goal(request):
    """Create a new team goal."""
    if request.method == 'POST':
        form = TeamGoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.creator = request.user
            goal.save()
            
            # Add creator as a member
            TeamGoalMember.objects.create(
                team_goal=goal,
                user=request.user,
                role='leader'
            )
            
            messages.success(request, 'Team goal created successfully!')
            return redirect('team_goal_detail', goal_id=goal.id)
    else:
        form = TeamGoalForm()
    
    return render(request, 'teams/create.html', {'form': form})

@login_required
def team_goal_detail(request, goal_id):
    """View and manage a specific team goal."""
    goal = get_object_or_404(
        TeamGoal.objects.prefetch_related('members__user'),
        id=goal_id
    )
    
    # Check if user has access to this goal
    if not (goal.creator == request.user or goal.members.filter(user=request.user).exists()):
        messages.error(request, 'You do not have access to this team goal.')
        return redirect('team_goals')
    
    # Handle inviting new members
    if request.method == 'POST':
        form = TeamInviteForm(request.POST)
        if form.is_valid():
            invite = form.save(commit=False)
            invite.sender = request.user
            invite.team_goal = goal
            invite.save()
            messages.success(request, f'Invitation sent to {invite.recipient.email}!')
            return redirect('team_goal_detail', goal_id=goal.id)
    else:
        form = TeamInviteForm()
    
    context = {
        'goal': goal,
        'invite_form': form,
    }
    return render(request, 'teams/detail.html', context)

@login_required
def accept_team_invite(request, invite_id):
    """Accept a team invitation."""
    invite = get_object_or_404(
        TeamInvite.objects.select_related('team_goal'),
        id=invite_id,
        recipient=request.user,
        status='pending'
    )
    
    # Create team member
    TeamGoalMember.objects.create(
        team_goal=invite.team_goal,
        user=request.user,
        role='member'
    )
    
    # Update invite status
    invite.status = 'accepted'
    invite.responded_at = timezone.now()
    invite.save()
    
    messages.success(request, f'You have joined {invite.team_goal.title}!')
    return redirect('team_goal_detail', goal_id=invite.team_goal.id)

@login_required
def decline_team_invite(request, invite_id):
    """Decline a team invitation."""
    invite = get_object_or_404(
        TeamInvite,
        id=invite_id,
        recipient=request.user,
        status='pending'
    )
    
    invite.status = 'declined'
    invite.responded_at = timezone.now()
    invite.save()
    
    messages.info(request, f'You have declined to join {invite.team_goal.title}.')
    return redirect('team_goals') 