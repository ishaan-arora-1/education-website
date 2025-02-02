from django.contrib import admin, messages
from django.contrib.auth import login
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db import models
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from .models import Cart, CartItem, Course, Enrollment, Profile, Review, SearchLog, Session, Subject, WebRequest


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_teacher", "expertise", "created_at", "updated_at")
    list_filter = ("is_teacher", "created_at", "updated_at")
    search_fields = ("user__username", "user__email", "expertise", "bio")
    ordering = ("-created_at",)
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("user", "is_teacher")}),
        ("Profile Information", {"fields": ("bio", "expertise", "avatar")}),
        ("Stripe Information", {"fields": ("stripe_account_id", "stripe_account_status", "commission_rate")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "get_enrollment_count")

    def get_enrollment_count(self, obj):
        count = obj.enrollments.count()
        if count > 0:
            url = reverse("admin:web_enrollment_changelist") + f"?student__id__exact={obj.id}"
            return format_html('<a href="{}">{} enrollments</a>', url, count)
        return "0 enrollments"

    get_enrollment_count.short_description = "Enrollments"
    get_enrollment_count.admin_order_field = "enrollments__count"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(models.Count("enrollments"))

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<id>/login_as_user/",
                self.admin_site.admin_view(self.login_as_user),
                name="auth_user_login_as",
            ),
        ]
        return custom_urls + urls

    def login_as_user(self, request, id):
        user = self.get_object(request, id)
        if not user:
            return self._get_obj_does_not_exist_redirect(request, "auth", "user", id)

        # Store the admin's ID and login as the user
        request.session["logged_in_as"] = {
            "original_user_id": request.user.id,
            "original_username": request.user.username,
            "target_username": user.username,
        }
        request.session.modified = True
        messages.success(request, f"You are now logged in as {user.username}")

        # Login as the selected user with the default auth backend
        from django.contrib.auth.backends import ModelBackend

        backend = ModelBackend()
        user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
        login(request, user)

        return HttpResponseRedirect("/")

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if request.user.is_superuser:
            return list_display + ("login_as_button",)
        return list_display

    def login_as_button(self, obj):
        if obj == self.model.objects.get(id=self.model._meta.pk.get_prep_value(obj.pk)):
            return format_html(
                '<a class="button" href="{}">Login as User</a>', reverse("admin:auth_user_login_as", args=[obj.pk])
            )

    login_as_button.short_description = ""
    login_as_button.allow_tags = True


class SessionInline(admin.TabularInline):
    model = Session
    extra = 1


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")
    ordering = ("order", "name")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "teacher", "price", "status")
    list_filter = ("subject", "level", "status", "is_featured")
    search_fields = ("title", "description", "teacher__username")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [SessionInline]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "start_time", "end_time", "is_virtual")
    list_filter = ("is_virtual", "start_time")
    search_fields = ("title", "description", "course__title")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "status", "enrollment_date", "completion_date")
    list_filter = ("status", "enrollment_date")
    search_fields = ("student__username", "course__title")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("student__username", "course__title", "comment")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("course", "session")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "item_count", "total", "created_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("user__username", "user__email", "session_key")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CartItemInline]
    raw_id_fields = ("user",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "course", "session", "price", "created_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("cart__user__username", "cart__user__email", "course__title", "session__title")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("cart", "course", "session")


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ("query", "results_count", "search_type", "user", "created_at")
    list_filter = ("search_type", "created_at")
    search_fields = ("query", "user__username", "user__email")
    readonly_fields = ("created_at", "filters_applied")
    ordering = ("-created_at",)
    raw_id_fields = ("user",)

    def has_add_permission(self, request):
        return False  # Search logs should only be created through the search interface

    def has_change_permission(self, request, obj=None):
        return False  # Search logs should not be editable


@admin.register(WebRequest)
class WebRequestAdmin(admin.ModelAdmin):
    list_display = ("path", "ip_address", "user", "count", "course", "get_agent", "created", "modified")
    list_filter = ("created", "modified")
    search_fields = ("path", "ip_address", "user", "agent", "referer")
    readonly_fields = ("created", "modified")
    ordering = ("-modified",)
    raw_id_fields = ("course",)

    def get_agent(self, obj):
        return obj.agent[:100] + "..." if len(obj.agent) > 100 else obj.agent

    get_agent.short_description = "User Agent"

    def has_add_permission(self, request):
        return False  # WebRequests should only be created through middleware

    def has_change_permission(self, request, obj=None):
        return False  # WebRequests should not be editable


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
