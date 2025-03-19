from allauth.account.models import EmailAddress
from django.contrib import admin, messages
from django.contrib.auth import login
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db import models
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (
    Achievement,
    BlogComment,
    BlogPost,
    Cart,
    CartItem,
    Challenge,
    ChallengeSubmission,
    Course,
    CourseMaterial,
    CourseProgress,
    Donation,
    Enrollment,
    ForumCategory,
    ForumReply,
    ForumTopic,
    Goods,
    Notification,
    Order,
    OrderItem,
    Payment,
    ProductImage,
    Profile,
    ProgressTracker,
    Review,
    SearchLog,
    Session,
    SessionAttendance,
    Storefront,
    Subject,
    SuccessStory,
    WebRequest,
)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fields = (
        "bio",
        "expertise",
        "avatar",
        "is_teacher",
        "referral_code",
        "referred_by",
        "referral_earnings",
        "commission_rate",
    )
    raw_id_fields = ("referred_by",)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields["referred_by"].required = False
        formset.form.base_fields["referral_earnings"].initial = 0
        formset.form.base_fields["commission_rate"].initial = 10.0
        return formset


class EmailAddressInline(admin.TabularInline):
    model = EmailAddress
    can_delete = True
    verbose_name_plural = "Email Addresses"
    extra = 1


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
    inlines = (ProfileInline, EmailAddressInline)
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "get_enrollment_count")

    # Add email to the add_fieldsets
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
    )

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

    def save_model(self, request, obj, form, change):
        creating = not change  # True if creating new user, False if editing
        super().save_model(request, obj, form, change)

        if creating:
            # Get email from the form data
            email = form.data.get("emailaddress_set-0-email")
            if email:
                # Set the user's email field only
                obj.email = email
                obj.save()


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


@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "material_type", "session", "order", "is_downloadable")
    list_filter = ("material_type", "is_downloadable", "requires_enrollment", "created_at")
    search_fields = ("title", "description", "course__title", "session__title")
    ordering = ("course", "order", "created_at")
    raw_id_fields = ("course", "session")


@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "completion_percentage", "attendance_rate", "last_accessed")
    list_filter = ("last_accessed",)
    search_fields = ("enrollment__student__username", "enrollment__course__title")
    raw_id_fields = ("enrollment", "completed_sessions")


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "achievement_type", "title", "awarded_at")
    list_filter = ("achievement_type", "awarded_at")
    search_fields = ("student__username", "course__title", "title", "description")
    raw_id_fields = ("student", "course")


@admin.register(SessionAttendance)
class SessionAttendanceAdmin(admin.ModelAdmin):
    list_display = ("session", "student", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("session__title", "student__username", "notes")
    raw_id_fields = ("session", "student")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "notification_type", "read", "created_at")
    list_filter = ("notification_type", "read", "created_at")
    search_fields = ("user__username", "title", "message")
    raw_id_fields = ("user",)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "published_at", "created_at")
    list_filter = ("status", "created_at", "published_at")
    search_fields = ("title", "content", "author__username", "tags")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author",)


@admin.register(SuccessStory)
class SuccessStoryAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "published_at", "created_at")
    list_filter = ("status", "created_at", "published_at")
    search_fields = ("title", "content", "author__username")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author",)


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "is_approved", "created_at")
    list_filter = ("is_approved", "created_at")
    search_fields = ("post__title", "author__username", "content")
    raw_id_fields = ("post", "author", "parent")


@admin.register(ForumTopic)
class ForumTopicAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "is_pinned", "is_locked", "views", "created_at")
    list_filter = ("is_pinned", "is_locked", "created_at")
    search_fields = ("title", "content", "author__username")
    raw_id_fields = ("author", "category")


@admin.register(ForumReply)
class ForumReplyAdmin(admin.ModelAdmin):
    list_display = ("topic", "author", "is_solution", "created_at")
    list_filter = ("is_solution", "created_at")
    search_fields = ("topic__title", "author__username", "content")
    raw_id_fields = ("topic", "author")


@admin.register(ForumCategory)
class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "created_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "session", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("enrollment__student__username", "enrollment__course__title", "stripe_payment_intent_id")
    raw_id_fields = ("enrollment", "session")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("week_number", "title", "start_date", "end_date")


@admin.register(ChallengeSubmission)
class ChallengeSubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "challenge", "submitted_at")


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Storefront)
class StorefrontAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "teacher", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("teacher__username", "store_name", "store_description")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("teacher", "store_name", "is_active")}),
        ("Content", {"fields": ("store_description", "store_logo", "store_banner")}),
        ("Policies", {"fields": ("refund_policy", "privacy_policy")}),
        ("Metadata", {"fields": ("store_slug", "created_at", "updated_at")}),
    )
    autocomplete_fields = ["teacher"]

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ("teacher",)
        return self.readonly_fields


@admin.register(Goods)
class GoodsAdmin(admin.ModelAdmin):
    list_display = ("name", "storefront", "price", "stock_status", "product_type", "is_available")
    list_filter = ("product_type", "is_available", "created_at")
    search_fields = ("name", "description", "sku", "storefront__store_name")
    readonly_fields = ("sku", "created_at", "updated_at")
    raw_id_fields = ("storefront",)
    list_editable = ("is_available",)
    date_hierarchy = "created_at"
    fieldsets = (
        (None, {"fields": ("name", "storefront", "is_available")}),
        ("Pricing", {"fields": ("price", "discount_price")}),
        ("Inventory", {"fields": ("product_type", "stock", "sku", "file")}),
        ("Content", {"fields": ("description", "category", "images")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )

    def stock_status(self, obj):
        if obj.product_type == "digital":
            return "N/A"
        return f"{obj.stock} in stock" if obj.stock else "Out of stock"

    stock_status.short_description = "Stock"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("preview",)

    def preview(self, obj):
        return format_html('<img src="{}" height="50" />', obj.image.url) if obj.image else "-"

    preview.short_description = "Preview"


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("goods", "preview", "alt_text")
    search_fields = ("goods__name", "alt_text")
    readonly_fields = ("preview",)
    raw_id_fields = ("goods",)

    def preview(self, obj):
        return format_html('<img src="{}" height="50" />', obj.image.url) if obj.image else "-"

    preview.short_description = "Preview"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("goods", "quantity", "price_at_purchase", "discounted_price_at_purchase")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "tracking_number")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("user",)
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    actions = ["mark_as_completed"]

    fieldsets = (
        (None, {"fields": ("user", "status")}),
        ("Financials", {"fields": ("currency", "tax_rate")}),
        ("Fulfillment", {"fields": ("shipping_address", "tracking_number")}),
        ("Compliance", {"fields": ("terms_accepted", "transaction_log")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )

    def mark_as_completed(self, request, queryset):
        queryset.update(status="completed")

    mark_as_completed.short_description = "Mark selected orders as completed"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "goods", "quantity", "price_at_purchase")
    list_filter = ("order__status",)
    search_fields = ("goods__name", "order__id")
    readonly_fields = ("id",)
    raw_id_fields = ("order", "goods")

    def price_display(self, obj):
        if obj.discounted_price_at_purchase:
            return f"${obj.discounted_price_at_purchase} (Discounted from ${obj.price_at_purchase})"
        return f"${obj.price_at_purchase}"

    price_display.short_description = "Price"


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(ProgressTracker)
class ProgressTrackerAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "current_value", "target_value", "percentage", "public", "updated_at")
    list_filter = ("public", "color", "created_at")
    search_fields = ("title", "description", "user__username")
    readonly_fields = ("embed_code", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("user", "title", "description")}),
        ("Progress", {"fields": ("current_value", "target_value", "color")}),
        ("Embedding", {"fields": ("public", "embed_code")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("email", "amount", "donation_type", "status", "created_at", "display_name")
    list_filter = ("donation_type", "status", "created_at", "anonymous")
    search_fields = ("email", "message", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Donation Information",
            {"fields": ("user", "email", "amount", "donation_type", "status", "message", "anonymous")},
        ),
        (
            "Stripe Information",
            {"fields": ("stripe_payment_intent_id", "stripe_subscription_id", "stripe_customer_id")},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def display_name(self, obj):
        return obj.display_name

    display_name.short_description = "Name"
