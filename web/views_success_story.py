from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SuccessStoryForm
from .models import SuccessStory


def success_story_list(request):
    """View for listing published success stories."""
    success_stories = SuccessStory.objects.filter(status="published").order_by("-published_at")
    
    # Paginate results
    paginator = Paginator(success_stories, 9)  # 9 stories per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        "success_stories": page_obj,
        "is_paginated": paginator.num_pages > 1,
        "page_obj": page_obj,
    }
    return render(request, "success_stories/list.html", context)


def success_story_detail(request, slug):
    """View for displaying a single success story."""
    success_story = get_object_or_404(SuccessStory, slug=slug, status="published")
    
    # Get related success stories (same author or similar content)
    related_stories = SuccessStory.objects.filter(
        status="published"
    ).exclude(
        id=success_story.id
    ).order_by("-published_at")[:3]
    
    context = {
        "success_story": success_story,
        "related_stories": related_stories,
    }
    return render(request, "success_stories/detail.html", context)


@login_required
def create_success_story(request):
    """View for creating a new success story."""
    if request.method == "POST":
        form = SuccessStoryForm(request.POST, request.FILES)
        if form.is_valid():
            success_story = form.save(commit=False)
            success_story.author = request.user
            success_story.save()
            messages.success(request, "Success story created successfully!")
            return redirect("success_story_detail", slug=success_story.slug)
    else:
        form = SuccessStoryForm()
    
    context = {
        "form": form,
    }
    return render(request, "success_stories/create.html", context)


@login_required
def edit_success_story(request, slug):
    """View for editing an existing success story."""
    success_story = get_object_or_404(SuccessStory, slug=slug, author=request.user)
    
    if request.method == "POST":
        form = SuccessStoryForm(request.POST, request.FILES, instance=success_story)
        if form.is_valid():
            form.save()
            messages.success(request, "Success story updated successfully!")
            return redirect("success_story_detail", slug=success_story.slug)
    else:
        form = SuccessStoryForm(instance=success_story)
    
    context = {
        "form": form,
        "success_story": success_story,
        "is_edit": True,
    }
    return render(request, "success_stories/create.html", context)


@login_required
def delete_success_story(request, slug):
    """View for deleting a success story."""
    success_story = get_object_or_404(SuccessStory, slug=slug, author=request.user)
    
    if request.method == "POST":
        success_story.delete()
        messages.success(request, "Success story deleted successfully!")
        return redirect("success_story_list")
    
    context = {
        "success_story": success_story,
    }
    return render(request, "success_stories/delete_confirm.html", context)
