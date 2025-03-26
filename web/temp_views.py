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
