# Create new file: web/virtual_classroom_views.py

import json
import random
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import (
    Session,
    VirtualClassroom,
    VirtualSeat,
    HandRaise,
    SharedContent,
    UpdateRound,
    UpdateTurn,
    SessionAttendance,
    Course,
    Subject,
)

# TEMPORARY: Test view for easy access to virtual classroom
@login_required
def test_virtual_classroom(request):
    # Create a test course if it doesn't exist
    course, _ = Course.objects.get_or_create(
        title="Test Course",
        defaults={
            'slug': 'test-course',
            'teacher': request.user,
            'description': 'Test course for virtual classroom feature',
            'learning_objectives': 'Test learning objectives',
            'price': 0,
            'max_students': 30,
            'subject': Subject.objects.first(),  # Get first subject
        }
    )
    
    # Create a test session if it doesn't exist
    session, _ = Session.objects.get_or_create(
        title="Test Virtual Classroom",
        course=course,
        defaults={
            'start_time': timezone.now(),
            'end_time': timezone.now() + timezone.timedelta(hours=1),
            'description': 'Test session for virtual classroom feature',
        }
    )
    
    # Create virtual classroom for the session if it doesn't exist
    classroom, created = VirtualClassroom.objects.get_or_create(
        session=session,
        defaults={
            'rows': 5,
            'columns': 6,
        }
    )
    
    # Create seats if they don't exist
    if created:
        for row in range(classroom.rows):
            for col in range(classroom.columns):
                VirtualSeat.objects.create(
                    classroom=classroom,
                    row=row,
                    column=col,
                )
    
    return redirect('virtual_classroom', session_id=session.id)
    SessionAttendance,

@login_required
@ensure_csrf_cookie
def virtual_classroom(request, session_id):
    """Main view for the virtual classroom."""
    session = get_object_or_404(Session, id=session_id)
    
    # Check if user is enrolled or is the teacher
    is_teacher = request.user == session.course.teacher
    is_student = session.course.enrollments.filter(student=request.user).exists() or session.enrollments.filter(student=request.user).exists()
    
    if not (is_teacher or is_student):
        messages.error(request, "You must be enrolled in this course to access the virtual classroom.")
        return redirect('course_detail', slug=session.course.slug)
    
    # Get or create the virtual classroom
    classroom, created = VirtualClassroom.objects.get_or_create(session=session)
    
    # If this is a new classroom, create the seats
    if created:
        for row in range(classroom.rows):
            for col in range(classroom.columns):
                VirtualSeat.objects.create(classroom=classroom, row=row, column=col)
    
    # Get the user's current seat if they have one
    user_seat = VirtualSeat.objects.filter(classroom=classroom, student=request.user).first()
    
    # Get all seats with their status
    seats = VirtualSeat.objects.filter(classroom=classroom).order_by('row', 'column')
    
    # Get active hand raises
    active_hand_raises = HandRaise.objects.filter(
        seat__classroom=classroom, 
        lowered_at__isnull=True
    ).select_related('seat', 'seat__student')
    
    # Get active update round if any
    active_update_round = UpdateRound.objects.filter(
        classroom=classroom, 
        ended_at__isnull=True
    ).first()
    
    # Get current update turn if any
    current_turn = None
    remaining_seconds = 0
    
    if active_update_round:
        current_turn = UpdateTurn.objects.filter(
            update_round=active_update_round,
            ended_at__isnull=True
        ).first()
        
        # Calculate remaining time for the timer
        if active_update_round.started_at:
            elapsed_seconds = (timezone.now() - active_update_round.started_at).total_seconds()
            remaining_seconds = max(0, active_update_round.duration_seconds - int(elapsed_seconds))
    
    # Mark attendance for the student
    if is_student and not is_teacher:
        attendance, _ = SessionAttendance.objects.get_or_create(
            session=session,
            student=request.user,
            defaults={'status': 'present'}
        )
        if attendance.status != 'present':
            attendance.status = 'present'
            attendance.save()
    
    context = {
        'session': session,
        'classroom': classroom,
        'is_teacher': is_teacher,
        'is_student': is_student,
        'seats': seats,
        'user_seat': user_seat,
        'active_hand_raises': active_hand_raises,
        'active_update_round': active_update_round,
        'current_turn': current_turn,
        'remaining_seconds': remaining_seconds,
    }
    
    # If this is a refresh request for just the seating grid, return only that part
    if request.GET.get('refresh_grid') == 'true':
        return render(request, 'virtual_classroom/_seating_grid.html', context)
    
    return render(request, 'virtual_classroom/classroom.html', context)


@csrf_exempt
@login_required
@require_POST
def select_seat(request, classroom_id):
    """API for selecting a seat in the classroom."""
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id)
    
    # Check if the user is enrolled or is the teacher
    session = classroom.session
    is_teacher = request.user == session.course.teacher
    is_student = session.course.enrollments.filter(student=request.user).exists() or session.enrollments.filter(student=request.user).exists()
    
    # Prevent teachers from selecting seats
    if is_teacher:
        return JsonResponse({'success': False, 'message': 'Teachers cannot select seats.'}, status=403)
    
    if not is_student:
        return JsonResponse({'success': False, 'message': 'You must be enrolled in this course.'}, status=403)
    
    # Get the row and column from the request
    try:
        row = int(request.POST.get('row'))
        column = int(request.POST.get('column'))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Invalid seat coordinates.'}, status=400)
    
    with transaction.atomic():
        # Release any existing seat for this user
        VirtualSeat.objects.filter(classroom=classroom, student=request.user).update(
            student=None,
            status='empty',
            assigned_at=None
        )
        
        # Try to select the new seat
        try:
            seat = VirtualSeat.objects.get(classroom=classroom, row=row, column=column)
            if seat.student:
                return JsonResponse({'success': False, 'message': 'This seat is already taken.'}, status=409)
            
            seat.student = request.user
            seat.status = 'occupied'
            seat.assigned_at = timezone.now()
            seat.save()
            
            # Get the previous seat that was released (if any)
            previous_seat = None
            if 'previous_seat_id' in request.POST and request.POST['previous_seat_id']:
                try:
                    previous_seat_id = int(request.POST['previous_seat_id'])
                    previous_seat = VirtualSeat.objects.get(id=previous_seat_id)
                except (ValueError, VirtualSeat.DoesNotExist):
                    pass
            
            # Return both the new seat and the previous seat (if any)
            response_data = {
                'new_seat': render_to_string('virtual_classroom/_seat.html', {
                    'seat': seat,
                    'request': request
                }),
                'new_seat_id': f'seat-{seat.id}',
                'classroom_id': classroom.id,
                'success': True
            }
            
            if previous_seat:
                response_data['previous_seat'] = render_to_string('virtual_classroom/_seat.html', {
                    'seat': previous_seat,
                    'request': request
                })
                response_data['previous_seat_id'] = f'seat-{previous_seat.id}'
            
            # Broadcast seat change to all connected users
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'classroom_{classroom.id}',
                    {
                        'type': 'seat_update',
                        'seat_id': seat.id,
                        'student_id': request.user.id,
                        'student_name': request.user.username,
                        'previous_seat_id': previous_seat.id if previous_seat else None
                    }
                )
            except ImportError:
                # Channels not available, continue without broadcasting
                pass
            
            # Check if this is an HTMX request
            if request.headers.get('HX-Request') == 'true':
                # Get active hand raises
                active_hand_raises = HandRaise.objects.filter(
                    seat__classroom=classroom, 
                    lowered_at__isnull=True
                ).select_related('seat', 'seat__student')
                
                # Return the updated seating grid for HTMX to swap in
                return render(request, 'virtual_classroom/_seating_grid.html', {
                    'classroom': classroom,
                    'session': session,
                    'seats': VirtualSeat.objects.filter(classroom=classroom).order_by('row', 'column').select_related('student'),
                    'user_seat': seat,  # The newly selected seat
                    'request': request,
                    'is_teacher': is_teacher,
                    'is_student': is_student,
                    'active_hand_raises': active_hand_raises
                })
            else:
                # Return JSON for non-HTMX requests (e.g., API calls)
                return JsonResponse(response_data)
        except VirtualSeat.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Seat not found.'}, status=404)


@login_required
@require_POST
def toggle_laptop(request):
    """API for toggling laptop status."""
    user = request.user
    
    # Get the user's current seat
    seat = VirtualSeat.objects.filter(student=user).first()
    if not seat:
        return JsonResponse({'success': False, 'message': 'You must be seated to use laptop.'}, status=400)
    
    # Toggle laptop status
    seat.laptop_open = not seat.laptop_open
    seat.save()
    
    # Return updated seating grid
    classroom = seat.classroom
    session = classroom.session
    is_teacher = request.user == session.course.teacher
    is_student = session.course.enrollments.filter(student=request.user).exists() or session.enrollments.filter(student=request.user).exists()
    
    # Get active hand raises
    active_hand_raises = HandRaise.objects.filter(
        seat__classroom=classroom, 
        lowered_at__isnull=True
    ).select_related('seat', 'seat__student')
    
    return render(request, 'virtual_classroom/_seating_grid.html', {
        'classroom': classroom,
        'session': session,
        'seats': classroom.seats.all().order_by('row', 'column'),
        'user_seat': seat,
        'request': request,
        'is_teacher': is_teacher,
        'is_student': is_student,
        'active_hand_raises': active_hand_raises
    })

@login_required
@require_POST
def raise_hand(request):
    """API for raising/lowering hand."""
    user = request.user
    
    # Get the user's current seat
    seat = VirtualSeat.objects.filter(student=user).first()
    if not seat:
        return JsonResponse({'success': False, 'message': 'You must be seated to raise your hand.'}, status=400)
    
    # Check if already has hand raised
    active_hand_raise = HandRaise.objects.filter(seat=seat, lowered_at__isnull=True).first()
    
    if active_hand_raise:
        # Lower hand
        active_hand_raise.lowered_at = timezone.now()
        active_hand_raise.save()
        seat.status = 'occupied'
        seat.save()
    else:
        # Raise hand
        HandRaise.objects.create(seat=seat)
        seat.status = 'hand_raised'
        seat.save()
    
    # Return updated seating grid
    classroom = seat.classroom
    session = classroom.session
    is_teacher = request.user == session.course.teacher
    is_student = session.course.enrollments.filter(student=request.user).exists() or session.enrollments.filter(student=request.user).exists()
    
    # Get active hand raises
    active_hand_raises = HandRaise.objects.filter(
        seat__classroom=classroom, 
        lowered_at__isnull=True
    ).select_related('seat', 'seat__student')
    
    return render(request, 'virtual_classroom/_seating_grid.html', {
        'classroom': classroom,
        'session': session,
        'seats': classroom.seats.all().order_by('row', 'column'),
        'user_seat': seat,
        'request': request,
        'is_teacher': is_teacher,
        'is_student': is_student,
        'active_hand_raises': active_hand_raises
    })


@login_required
@require_POST
def start_speaking(request, hand_raise_id):
    """Teacher selects a student to speak."""
    hand_raise = get_object_or_404(HandRaise, id=hand_raise_id, lowered_at__isnull=True)
    
    # Verify the user is the teacher
    session = hand_raise.seat.classroom.session
    if request.user != session.course.teacher:
        return JsonResponse({'success': False, 'message': 'Only the teacher can select who speaks.'}, status=403)
    
    with transaction.atomic():
        # Mark all seats as not speaking
        VirtualSeat.objects.filter(classroom=hand_raise.seat.classroom, status='speaking').update(status='occupied')
        
        # Mark this student as speaking
        hand_raise.acknowledged = True
        hand_raise.save()
        
        seat = hand_raise.seat
        seat.status = 'speaking'
        seat.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'{seat.student.username} is now speaking.',
            'student': {
                'id': seat.student.id,
                'username': seat.student.username,
                'seat_id': seat.id
            }
        })


@csrf_exempt
@login_required
@require_POST
def upload_content(request, seat_id):
    """Upload content from a student's virtual laptop."""
    print(f'Processing upload_content request for seat_id: {seat_id}')
    seat = get_object_or_404(VirtualSeat, id=seat_id)
    
    # Verify the user owns this seat
    if request.user != seat.student:
        return JsonResponse({'success': False, 'message': 'You can only share content from your own seat.'}, status=403)
    
    # Handle file upload
    if 'file' in request.FILES:
        content_type = request.POST.get('content_type', 'screenshot')
        description = request.POST.get('description', '')
        
        shared_content = SharedContent.objects.create(
            seat=seat,
            content_type=content_type,
            file=request.FILES['file'],
            description=description
        )
        
        # Notify other users via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'classroom_{seat.classroom.id}',
            {
                'type': 'content_shared',
                'student_name': request.user.username,
                'content_type': content_type,
                'description': description,
                'content_url': request.build_absolute_uri(shared_content.file.url),
                'shared_at': shared_content.shared_at.isoformat()
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Content shared successfully.',
            'content': {
                'id': shared_content.id,
                'type': shared_content.content_type,
                'url': shared_content.file.url,
                'file_url': request.build_absolute_uri(shared_content.file.url),
                'description': shared_content.description,
                'shared_at': shared_content.shared_at.isoformat()
            }
        })
    
    # Handle URL sharing
    elif request.POST.get('link'):
        link = request.POST.get('link')
        description = request.POST.get('description', '')
        
        shared_content = SharedContent.objects.create(
            seat=seat,
            content_type='link',
            link=link,
            description=description
        )
        
        # Notify other users via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'classroom_{seat.classroom.id}',
            {
                'type': 'content_shared',
                'student_name': request.user.username,
                'content_type': 'link',
                'description': description,
                'content_url': link,
                'shared_at': shared_content.shared_at.isoformat()
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Link shared successfully.',
            'content': {
                'id': shared_content.id,
                'type': 'link',
                'url': shared_content.link,
                'content_url': link,
                'description': shared_content.description,
                'shared_at': shared_content.shared_at.isoformat()
            }
        })
    
    return JsonResponse({'success': False, 'message': 'No content provided.'}, status=400)


@login_required
@csrf_exempt
def start_update_round(request, classroom_id):
    """Teacher starts a timed update round."""
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id)
    
    # Temporarily allow any user to start an update round for testing
    # if request.user != classroom.session.course.teacher:
    #     return JsonResponse({'success': False, 'message': 'Only the teacher can start update rounds.'}, status=403)
    is_teacher = True  # Force is_teacher to be True for testing
    
    # Check if there's an active round
    active_round = UpdateRound.objects.filter(classroom=classroom, ended_at__isnull=True).first()
    if active_round:
        return JsonResponse({'success': False, 'message': 'There is already an active update round.'}, status=409)
    
    # Get duration from POST data or use default
    try:
        duration_seconds = int(request.POST.get('duration_seconds', 120))
    except (ValueError, TypeError):
        duration_seconds = 120
    
    # Get all occupied seats
    occupied_seats = VirtualSeat.objects.filter(
        classroom=classroom,
        student__isnull=False
    ).exclude(student=request.user)  # Exclude teacher
    
    if not occupied_seats.exists():
        return JsonResponse({'success': False, 'message': 'No students are present to participate in updates.'}, status=400)
    
    with transaction.atomic():
        # Create the update round
        update_round = UpdateRound.objects.create(
            classroom=classroom,
            duration_seconds=duration_seconds
        )
        
        # Select first student randomly
        first_seat = random.choice(occupied_seats)
        first_turn = UpdateTurn.objects.create(
            update_round=update_round,
            seat=first_seat
        )
        
        # Calculate remaining time for the timer
        remaining_seconds = update_round.duration_seconds
        
        # Broadcast update to all connected users
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'classroom_{classroom.id}',
                {
                    'type': 'update_round_started',
                    'update_round_id': update_round.id,
                    'duration_seconds': update_round.duration_seconds,
                    'current_turn_id': first_turn.id,
                    'current_speaker_id': first_turn.seat.student.id,
                    'current_speaker_username': first_turn.seat.student.username
                }
            )
        except ImportError:
            # Channels not available, continue without broadcasting
            pass
        
        return render(request, 'virtual_classroom/_update_round.html', {
            'classroom': classroom,
            'update_round': update_round,
            'current_turn': first_turn,
            'is_teacher': is_teacher,
            'remaining_seconds': remaining_seconds
        })


@login_required
@require_POST
@csrf_exempt
def end_update_turn(request, turn_id):
    """Student or teacher ends the current update turn."""
    turn = get_object_or_404(UpdateTurn, id=turn_id, ended_at__isnull=True)
    update_round = turn.update_round
    classroom = update_round.classroom
    
    # Verify the user is either the teacher or the student speaking
    is_teacher = request.user == classroom.session.course.teacher
    is_speaking_student = request.user == turn.seat.student
    
    if not (is_teacher or is_speaking_student):
        return JsonResponse({'success': False, 'message': 'You cannot end this turn.'}, status=403)
    
    with transaction.atomic():
        # End the current turn
        turn.ended_at = timezone.now()
        turn.save()
        
        # Find students who haven't gone yet
        remaining_seats = VirtualSeat.objects.filter(
            classroom=classroom,
            student__isnull=False
        ).exclude(
            student=classroom.session.course.teacher  # Exclude teacher
        ).exclude(
            id__in=UpdateTurn.objects.filter(update_round=update_round).values_list('seat_id', flat=True)
        )
        
        if remaining_seats.exists():
            # Select next student randomly
            next_seat = random.choice(remaining_seats)
            next_turn = UpdateTurn.objects.create(
                update_round=update_round,
                seat=next_seat
            )
            
            # Broadcast update to all connected users
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'classroom_{classroom.id}',
                    {
                        'type': 'update_turn_ended',
                        'update_round_id': update_round.id,
                        'next_turn_id': next_turn.id,
                        'next_speaker_id': next_seat.student.id,
                        'next_speaker_username': next_seat.student.username,
                        'completed': False
                    }
                )
            except ImportError:
                # Channels not available, continue without broadcasting
                pass
            
            return JsonResponse({
                'success': True,
                'message': 'Turn ended, next student selected.',
                'completed': False,
                'next_turn': {
                    'id': next_turn.id,
                    'student': {
                        'id': next_seat.student.id,
                        'username': next_seat.student.username
                    },
                    'started_at': next_turn.started_at.isoformat()
                }
            })
        else:
            # All students have gone, end the round
            update_round.ended_at = timezone.now()
            update_round.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Update round completed!',
                'completed': True,
                'round': {
                    'id': update_round.id,
                    'duration_seconds': update_round.duration_seconds,
                    'started_at': update_round.started_at.isoformat(),
                    'ended_at': update_round.ended_at.isoformat()
                }
            })
@login_required
def get_update_round_html(request, classroom_id):
    """Get the HTML for the update round container."""
    classroom = get_object_or_404(VirtualClassroom, id=classroom_id)
    
    # Check if the user is enrolled or is the teacher
    session = classroom.session
    is_teacher = request.user == session.course.teacher
    
    # Get active update round if any
    active_update_round = UpdateRound.objects.filter(
        classroom=classroom, 
        ended_at__isnull=True
    ).first()
    
    # Get current update turn if any
    current_turn = None
    remaining_seconds = 0
    
    if active_update_round:
        current_turn = UpdateTurn.objects.filter(
            update_round=active_update_round,
            ended_at__isnull=True
        ).first()
        
        # Calculate remaining time for the timer
        if active_update_round.started_at:
            elapsed_seconds = (timezone.now() - active_update_round.started_at).total_seconds()
            remaining_seconds = max(0, active_update_round.duration_seconds - int(elapsed_seconds))
    
    return render(request, 'virtual_classroom/_update_round.html', {
        'classroom': classroom,
        'update_round': active_update_round,
        'current_turn': current_turn,
        'is_teacher': is_teacher,
        'remaining_seconds': remaining_seconds
    })


@login_required
def get_current_speaker_html(request, turn_id):
    """Get the HTML for the current speaker section."""
    turn = get_object_or_404(UpdateTurn, id=turn_id, ended_at__isnull=True)
    classroom = turn.update_round.classroom
    
    # Check if the user is enrolled or is the teacher
    session = classroom.session
    is_teacher = request.user == session.course.teacher
    
    return render(request, 'virtual_classroom/_current_speaker.html', {
        'classroom': classroom,
        'current_turn': turn,
        'is_teacher': is_teacher
    })


@csrf_exempt
@login_required
@require_POST
def share_link(request):
    """Share a link in the virtual classroom."""
    print('Share link request received')
    if request.method == 'POST':
        print(f'POST data: {request.POST}')
        seat_id = request.POST.get('seat_id')
        link = request.POST.get('link')
        description = request.POST.get('description', '')
        print(f'Processing share_link request with seat_id: {seat_id}, link: {link}')
        
        if not seat_id:
            return JsonResponse({'error': 'Missing seat ID'}, status=400)
        
        if not link:
            return JsonResponse({
                'success': False, 
                'message': 'Please enter a valid URL to share'
            }, status=400)
        
        try:
            seat = VirtualSeat.objects.get(id=seat_id)
            classroom = seat.classroom
            
            # Create shared content record
            shared_content = SharedContent.objects.create(
                classroom=classroom,
                student=request.user,
                content_type='link',
                content_url=link,
                description=description
            )
            
            # Notify other users via WebSocket
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'classroom_{classroom.id}',
                {
                    'type': 'content_shared',
                    'student_name': request.user.username,
                    'content_type': 'link',
                    'description': description,
                    'content_url': link,
                    'shared_at': shared_content.created_at.isoformat()
                }
            )
            
            return JsonResponse({
                'status': 'success',
                'content_id': shared_content.id,
                'content_url': link
            })
            
        except VirtualSeat.DoesNotExist:
            return JsonResponse({'error': 'Invalid seat'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
