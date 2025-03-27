import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from django.db.models import Prefetch
from django.template.loader import render_to_string

from .models import (
    Course,
    Session,
    VirtualClassroom,
    VirtualSeat,
    VirtualHand,
    Share,
    UpdateRound,
    StandaloneSession,
    ValidationError,
)

from django.forms import ModelForm

class StandaloneSessionForm(ModelForm):
    class Meta:
        model = StandaloneSession
        fields = ['title', 'description', 'max_participants']

@login_required
def virtual_classroom(request, session_id=None, standalone_id=None):
    if session_id:
        session = get_object_or_404(Session, id=session_id)
        standalone_session = None
        
        # Check if user is enrolled or is the teacher
        if not (request.user == session.course.teacher or 
                session.course.enrollments.filter(student=request.user, status='approved').exists()):
            return HttpResponseForbidden("You must be enrolled in this course or be the teacher.")
    elif standalone_id:
        standalone_session = get_object_or_404(StandaloneSession, id=standalone_id)
        session = None
        
        # For standalone sessions, anyone can join
        if not standalone_session.is_active:
            return HttpResponseForbidden("This session is no longer active.")
    else:
        return HttpResponseForbidden("Invalid session type.")
    
    try:
        # Get or create virtual classroom
        if session:
            classroom, created = VirtualClassroom.objects.get_or_create(session=session)
        else:
            classroom, created = VirtualClassroom.objects.get_or_create(standalone_session=standalone_session)
        
        if created:
            # Create the seating grid
            for row in range(classroom.grid_rows):
                for col in range(classroom.grid_columns):
                    VirtualSeat.objects.create(classroom=classroom, row=row, column=col)
    except ValidationError as e:
        return HttpResponseForbidden(str(e))
    
    # Get classroom data
    seats = classroom.seats.all()
    raised_hands = classroom.raised_hands.filter(is_active=True)
    raised_hands_students = raised_hands.values_list('student_id', flat=True)
    screen_shares = classroom.screen_shares.all()
    active_round = classroom.update_rounds.filter(is_active=True).first()
    hand_raised = classroom.raised_hands.filter(student=request.user, is_active=True).exists()
    
    context = {
        'session': session,
        'standalone_session': standalone_session,
        'classroom': classroom,
        'seats': seats,
        'raised_hands': raised_hands,
        'raised_hands_students': raised_hands_students,
        'screen_shares': screen_shares,
        'active_round': active_round,
        'hand_raised': hand_raised,
        'is_teacher': (session and request.user == session.course.teacher) or 
                     (standalone_session and request.user == standalone_session.host),
    }
    
    return render(request, 'classroom/virtual_classroom.html', context)

@login_required
@require_POST
def select_seat(request, classroom_id):
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id)
    
    # Validate user access
    if classroom.session:
        if not (request.user == classroom.session.course.teacher or 
                classroom.session.course.enrollments.filter(student=request.user, status='approved').exists()):
            return JsonResponse({'error': 'Access denied'}, status=403)
    else:  # Standalone session
        if not (request.user == classroom.standalone_session.host or request.user.is_authenticated):
            return JsonResponse({'error': 'Access denied'}, status=403)
    
    data = json.loads(request.body)
    row = data.get('row')
    column = data.get('column')
    
    try:
        # Clear user's previous seat if any
        VirtualSeat.objects.filter(classroom=classroom, student=request.user).update(
            student=None,
            is_occupied=False
        )
        
        # Assign new seat
        seat = get_object_or_404(VirtualSeat, classroom=classroom, row=row, column=column)
        if seat.is_occupied:
            return JsonResponse({'error': 'Seat is already occupied'}, status=400)
        
        seat.student = request.user
        seat.is_occupied = True
        seat.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'success': True})

@login_required
@require_POST
def toggle_hand(request, classroom_id):
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id)
    
    # Check if user has an active hand raise
    hand = VirtualHand.objects.filter(
        classroom=classroom,
        student=request.user,
        is_active=True
    ).first()
    
    if hand:
        hand.is_active = False
        hand.save()
        return JsonResponse({'status': 'lowered'})
    else:
        VirtualHand.objects.create(
            classroom=classroom,
            student=request.user
        )
        return JsonResponse({'status': 'raised'})

@login_required
@require_POST
def select_speaker(request, hand_id):
    hand = get_object_or_404(VirtualHand, id=hand_id)
    
    # Only teacher can select speakers
    if request.user != hand.classroom.session.course.teacher:
        return JsonResponse({'error': 'Only the teacher can select speakers'}, status=403)
    
    # Deselect any currently selected speakers
    VirtualHand.objects.filter(
        classroom=hand.classroom,
        selected_for_speaking=True
    ).update(selected_for_speaking=False)
    
    hand.selected_for_speaking = True
    hand.save()
    
    return JsonResponse({'success': True})

@login_required
@require_POST
def share(request, classroom_id):
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id)
    
    share_type = request.POST.get('share_type')
    if share_type not in ['screenshot', 'link']:
        return JsonResponse({'error': 'Invalid share type'}, status=400)
    
    share = Share(classroom=classroom, sender=request.user, share_type=share_type)
    
    if share_type == 'screenshot':
        if 'screenshot' not in request.FILES:
            return JsonResponse({'error': 'No screenshot provided'}, status=400)
        share.screenshot = request.FILES['screenshot']
    else:  # link
        link = request.POST.get('link')
        if not link:
            return JsonResponse({'error': 'No link provided'}, status=400)
        share.link = link
    
    share.title = request.POST.get('title', '')
    share.description = request.POST.get('description', '')
    share.save()
    
    # Check if client accepts JSON
    if 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'id': share.id,
            'type': share.share_type,
            'url': share.screenshot.url if share.screenshot else share.link,
            'title': share.title,
            'description': share.description,
            'sender': share.sender.username
        })
    
    # Otherwise, redirect to classroom page
    return redirect('virtual_classroom_standalone', standalone_id=classroom_id)

@login_required
@require_POST
def start_update_round(request, classroom_id):
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id)
    
    # Only teacher can start update rounds
    if request.user != classroom.session.course.teacher:
        return JsonResponse({'error': 'Only the teacher can start update rounds'}, status=403)
    
    # End any active rounds
    UpdateRound.objects.filter(classroom=classroom, is_active=True).update(is_active=False)
    
    duration = int(request.POST.get('duration', 120))  # Default 2 minutes
    round = UpdateRound.objects.create(
        classroom=classroom,
        duration=duration
    )
    
    # Select first speaker randomly from students with seats
    seated_students = VirtualSeat.objects.filter(
        classroom=classroom,
        is_occupied=True
    ).exclude(student=None).values_list('student', flat=True)
    
    if seated_students:
        import random
        first_speaker = random.choice(seated_students)
        round.current_speaker_id = first_speaker
        round.save()
    
    return JsonResponse({
        'round_id': round.id,
        'duration': round.duration,
        'current_speaker': round.current_speaker.username if round.current_speaker else None
    })

@login_required
def classroom_lobby(request):
    context = {
        'is_teacher': hasattr(request.user, 'teacher'),
    }

    # Get standalone sessions hosted by the user
    context['hosted_sessions'] = StandaloneSession.objects.filter(
        host=request.user,
        is_active=True
    ).order_by('-created_at')

    # Get active standalone sessions
    context['active_sessions'] = StandaloneSession.objects.filter(
        is_active=True
    ).exclude(host=request.user).order_by('-created_at')

    if context['is_teacher']:
        # Get courses where the user is a teacher
        context['teacher_courses'] = Course.objects.filter(
            teacher=request.user
        ).prefetch_related(
            Prefetch('sessions',
                    queryset=Session.objects.filter(
                        start_time__lte=timezone.now(),
                        end_time__gte=timezone.now()
                    ),
                    to_attr='current_session')
        )
    else:
        # Get courses where the user is enrolled
        context['enrolled_courses'] = Course.objects.filter(
            enrollments__student=request.user,
            enrollments__status='approved'
        ).prefetch_related(
            Prefetch('sessions',
                    queryset=Session.objects.filter(
                        start_time__lte=timezone.now(),
                        end_time__gte=timezone.now()
                    ),
                    to_attr='current_session')
        )

    # Get upcoming sessions for all relevant courses
    if context['is_teacher']:
        courses = context['teacher_courses']
    else:
        courses = context['enrolled_courses']

    context['upcoming_sessions'] = Session.objects.filter(
        course__in=courses,
        start_time__gte=timezone.now()
    ).select_related('course').order_by('start_time')[:5]

    return render(request, 'classroom/classroom_lobby.html', context)


@login_required
@require_POST
def start_standalone_session(request):
    form = StandaloneSessionForm(request.POST)
    if form.is_valid():
        session = form.save(commit=False)
        session.host = request.user
        session.save()
        
        # Create virtual classroom for the session
        classroom = VirtualClassroom.objects.create(standalone_session=session)
        
        # Create the seating grid
        for row in range(classroom.grid_rows):
            for col in range(classroom.grid_columns):
                VirtualSeat.objects.create(classroom=classroom, row=row, column=col)
        
        # Get updated list of hosted sessions
        hosted_sessions = StandaloneSession.objects.filter(
            host=request.user,
            is_active=True
        ).order_by('-created_at')
        
        # Render the updated hosted sessions section
        html = render_to_string('classroom/partials/hosted_sessions.html', {
            'hosted_sessions': hosted_sessions
        }, request=request)
        
        return JsonResponse({
            'html': html,
            'redirect_url': f'/classroom/standalone/{session.id}/'
        })
    
    return JsonResponse({'error': 'Invalid form data'}, status=400)


def complete_speaker_turn(request, round_id):
    round = get_object_or_404(UpdateRound, id=round_id)
    
    # Verify current speaker or teacher
    if not (request.user == round.current_speaker or request.user == round.classroom.session.course.teacher):
        return JsonResponse({'error': 'Only the current speaker or teacher can complete the turn'}, status=403)
    
    # Add current speaker to completed list
    if round.current_speaker:
        round.completed_speakers.add(round.current_speaker)
    
    # Select next speaker randomly from seated students who haven't spoken
    seated_students = VirtualSeat.objects.filter(
        classroom=round.classroom,
        is_occupied=True
    ).exclude(
        student__in=round.completed_speakers.all()
    ).exclude(
        student=None
    ).values_list('student', flat=True)
    
    if seated_students:
        import random
        next_speaker = random.choice(seated_students)
        round.current_speaker_id = next_speaker
        round.save()
    else:
        # No more speakers, end the round
        round.is_active = False
        round.current_speaker = None
        round.save()
    
    return JsonResponse({
        'status': 'active' if round.is_active else 'completed',
        'current_speaker': round.current_speaker.username if round.current_speaker else None
    })
