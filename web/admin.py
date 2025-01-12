from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Course, Enrollment, Profile, Review, Session, Subject


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
        ("Profile Information", {"fields": ("bio", "expertise")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "get_is_teacher",
    )

    def get_is_teacher(self, obj):
        return obj.profile.is_teacher if hasattr(obj, "profile") else False

    get_is_teacher.short_description = "Is Teacher"
    get_is_teacher.boolean = True


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


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
