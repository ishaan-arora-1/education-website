from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import redirect, render

from .forms import EducationalVideoForm
from .models import EducationalVideo
 
 
def educational_videos_list(request):
     """View for listing educational videos with optional category filtering."""
     # Get category filter from query params
     selected_category = request.GET.get('category')
 
     # Base queryset
     videos = EducationalVideo.objects.select_related('uploader').order_by('-uploaded_at')
 
     # Apply category filter if provided
     if selected_category:
         videos = videos.filter(category=selected_category)
         selected_category_display = dict(EducationalVideo.VIDEO_CATEGORY_CHOICES).get(selected_category)
     else:
         selected_category_display = None
 
     # Get category counts for sidebar
     category_counts = dict(
         EducationalVideo.objects.values_list('category')
         .annotate(count=Count('id'))
         .values_list('category', 'count')
     )
 
     # Paginate results
     paginator = Paginator(videos, 12)  # 12 videos per page
     page_number = request.GET.get('page', 1)
     page_obj = paginator.get_page(page_number)
 
     context = {
         'videos': page_obj,
         'is_paginated': paginator.num_pages > 1,
         'page_obj': page_obj,
         'category_choices': EducationalVideo.VIDEO_CATEGORY_CHOICES,
         'selected_category': selected_category,
         'selected_category_display': selected_category_display,
         'category_counts': category_counts,
     }
 
     return render(request, 'videos/list.html', context)
 
 
@login_required
def upload_educational_video(request):
     """View for uploading a new educational video."""
     if request.method == 'POST':
         form = EducationalVideoForm(request.POST)
         if form.is_valid():
             video = form.save(commit=False)
             video.uploader = request.user
             video.save()
 
             return redirect('educational_videos_list')
     else:
         form = EducationalVideoForm()
 
     return render(request, 'videos/upload.html', {'form': form})