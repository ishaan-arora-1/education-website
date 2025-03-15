from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import redirect, render, get_object_or_404

from .forms import EducationalVideoForm
from .models import EducationalVideo, Subject


def educational_videos_list(request):
    """View for listing educational videos with optional category filtering."""
    # Get category filter from query params
    selected_category = request.GET.get("category")

    # Base queryset
    videos = EducationalVideo.objects.select_related("uploader", "category").order_by("-uploaded_at")

    # Apply category filter if provided
    if selected_category:
        videos = videos.filter(category__slug=selected_category)
        selected_category_obj = get_object_or_404(Subject, slug=selected_category)
        selected_category_display = selected_category_obj.name
    else:
        selected_category_display = None

    # Get category counts for sidebar
    category_counts = dict(
        EducationalVideo.objects.values("category__name", "category__slug")
        .annotate(count=Count("id"))
        .values_list("category__slug", "count")
    )

    # Get all subjects for the dropdown
    subjects = Subject.objects.all().order_by("order", "name")

    # Paginate results
    paginator = Paginator(videos, 12)  # 12 videos per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "videos": page_obj,
        "is_paginated": paginator.num_pages > 1,
        "page_obj": page_obj,
        "subjects": subjects,
        "selected_category": selected_category,
        "selected_category_display": selected_category_display,
        "category_counts": category_counts,
    }

    return render(request, "videos/list.html", context)


@login_required
def upload_educational_video(request):
    """View for uploading a new educational video."""
    if request.method == "POST":
        form = EducationalVideoForm(request.POST)
        if form.is_valid():
            video = form.save(commit=False)
            video.uploader = request.user
            video.save()

            return redirect("educational_videos_list")
    else:
        form = EducationalVideoForm()

    return render(request, "videos/upload.html", {"form": form})
