from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path

from . import views

# Non-prefixed URLs
urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),  # Language selection URLs
]

# Language-prefixed URLs
urlpatterns += i18n_patterns(
    path("", views.index, name="index"),
    path("learn/", views.learn, name="learn"),
    path("teach/", views.teach, name="teach"),
    path("about/", views.about, name="about"),
    path("blog/", views.blog_list, name="blog"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog_detail"),
    # Authentication URLs
    # path("login/", auth_views.LoginView.as_view(), name="login"),
    # path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("accounts/profile/", views.profile, name="accounts_profile"),
    # Course Management
    path("accounts/", include("allauth.urls")),
    path("courses/create/", views.create_course, name="create_course"),
    path("courses/search/", views.course_search, name="course_search"),
    path("courses/<slug:slug>/", views.course_detail, name="course_detail"),
    path("courses/<slug:course_slug>/enroll/", views.enroll_course, name="enroll"),
    path("courses/<slug:slug>/add-session/", views.add_session, name="add_session"),
    path("courses/<slug:slug>/add-review/", views.add_review, name="add_review"),
    path("courses/<slug:slug>/update/", views.update_course, name="update_course"),
    path("courses/<slug:slug>/delete/", views.delete_course, name="delete_course"),
    # Payment URLs
    path(
        "courses/<slug:slug>/create-payment-intent/",
        views.create_payment_intent,
        name="create_payment_intent",
    ),
    path("stripe-webhook/", views.stripe_webhook, name="stripe_webhook"),
    # Admin and Utilities
    path("github_update/", views.github_update, name="github_update"),
    path("admin/", admin.site.urls),
    path("captcha/", include("captcha.urls")),
    path("subjects/", views.subjects, name="subjects"),
    # Progress tracking URLs
    path(
        "sessions/<int:session_id>/attendance/",
        views.mark_session_attendance,
        name="mark_session_attendance",
    ),
    path(
        "sessions/<int:session_id>/complete/",
        views.mark_session_completed,
        name="mark_session_completed",
    ),
    path(
        "enrollment/<int:enrollment_id>/progress/",
        views.student_progress,
        name="student_progress",
    ),
    path(
        "courses/<slug:slug>/progress/",
        views.course_progress_overview,
        name="course_progress_overview",
    ),
    path(
        "courses/<slug:slug>/materials/upload/",
        views.upload_material,
        name="upload_material",
    ),
    path(
        "courses/<slug:slug>/materials/<int:material_id>/delete/",
        views.delete_material,
        name="delete_material",
    ),
    path(
        "courses/<slug:slug>/materials/<int:material_id>/download/",
        views.download_material,
        name="download_material",
    ),
    path(
        "courses/<slug:slug>/marketing/",
        views.course_marketing,
        name="course_marketing",
    ),
    path(
        "courses/<slug:slug>/analytics/",
        views.course_analytics,
        name="course_analytics",
    ),
    path("calendar/feed/", views.calendar_feed, name="calendar_feed"),
    path(
        "calendar/session/<int:session_id>/",
        views.calendar_links,
        name="calendar_links",
    ),
    # Forum URLs
    path("forum/", views.forum_categories, name="forum_categories"),
    path("forum/<slug:slug>/", views.forum_category, name="forum_category"),
    path("forum/<slug:category_slug>/create/", views.create_topic, name="create_topic"),
    path(
        "forum/<slug:category_slug>/<int:topic_id>/",
        views.forum_topic,
        name="forum_topic",
    ),
    # Peer Networking URLs
    path("peers/", views.peer_connections, name="peer_connections"),
    path(
        "peers/connect/<int:user_id>/",
        views.send_connection_request,
        name="send_connection_request",
    ),
    path(
        "peers/handle/<int:connection_id>/<str:action>/",
        views.handle_connection_request,
        name="handle_connection_request",
    ),
    path("peers/messages/<int:user_id>/", views.peer_messages, name="peer_messages"),
    # Study Groups URLs
    path("courses/<int:course_id>/groups/", views.study_groups, name="study_groups"),
    path("groups/<int:group_id>/", views.study_group_detail, name="study_group_detail"),
    path("sessions/<int:session_id>/", views.session_detail, name="session_detail"),
    path("sitemap/", views.sitemap, name="sitemap"),
    prefix_default_language=True,
)
