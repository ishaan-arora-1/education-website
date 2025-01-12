import os

from allauth.account.signals import user_signed_up
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("info", "Information"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES, default="info")
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, default="")
    expertise = models.CharField(max_length=200, blank=True, default="")
    is_teacher = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class", blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Course(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    image = models.ImageField(
        upload_to="course_images/%Y/%m/%d/",
        help_text="Course image (300x150 pixels)",
        blank=True,
        null=True,
    )
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses_teaching")
    description = models.TextField(blank=True, default="")
    learning_objectives = models.TextField()
    prerequisites = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    allow_individual_sessions = models.BooleanField(
        default=False, help_text="Allow students to register for individual sessions"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    max_students = models.IntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="courses",
    )

    level = models.CharField(
        max_length=20,
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ],
        default="beginner",
    )
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    is_featured = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def available_spots(self):
        return self.max_students - self.enrollments.count()

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum(review.rating for review in reviews) / len(reviews)

    def clean(self):
        from django.core.exceptions import ValidationError
        from PIL import Image

        super().clean()

        if self.image:
            # Open the uploaded image
            img = Image.open(self.image)

            # Check dimensions
            if img.size != (300, 150):
                raise ValidationError(
                    {
                        "image": "Image dimensions must be 300x150 pixels. Current dimensions are {}x{}".format(
                            img.size[0], img.size[1]
                        )
                    }
                )


class Session(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_virtual = models.BooleanField(default=True)
    meeting_link = models.URLField(blank=True)
    meeting_id = models.CharField(max_length=100, blank=True)  # For storing Google meeting ID
    location = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Price for individual session registration"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    def save(self, *args, **kwargs):
        # Handle virtual meeting creation/updates
        is_new = self._state.adding
        old_instance = None if is_new else Session.objects.get(pk=self.pk)

        # First save to get the ID
        super().save(*args, **kwargs)

        if self.is_virtual:
            from .calendar_sync import create_calendar_event, update_calendar_event

            if is_new:
                event_id = create_calendar_event(self)
                if event_id:
                    self.meeting_id = event_id
                    # Update without triggering save() again
                    Session.objects.filter(pk=self.pk).update(meeting_id=event_id)
            elif old_instance and (
                old_instance.start_time != self.start_time
                or old_instance.end_time != self.end_time
                or old_instance.title != self.title
            ):
                update_calendar_event(self)

    def delete(self, *args, **kwargs):
        # Delete associated calendar event if exists
        if self.is_virtual and self.meeting_id:
            from .calendar_sync import delete_calendar_event

            delete_calendar_event(self)
        super().delete(*args, **kwargs)


class CourseMaterial(models.Model):
    MATERIAL_TYPES = [
        ("video", "Video Lesson"),
        ("document", "Document"),
        ("presentation", "Presentation"),
        ("exercise", "Exercise"),
        ("quiz", "Quiz"),
        ("other", "Other"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="materials")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPES)
    file = models.FileField(upload_to="course_materials/%Y/%m/%d/")
    session = models.ForeignKey(
        Session,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials",
    )
    order = models.PositiveIntegerField(default=0)
    is_downloadable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def file_extension(self):
        return os.path.splitext(self.file.name)[1].lower()

    @property
    def file_size(self):
        try:
            return self.file.size
        except FileNotFoundError:
            return 0


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    enrollment_date = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["student", "course"]

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"


class SessionAttendance(models.Model):
    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("excused", "Excused"),
        ("late", "Late"),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="attendances")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session_attendances")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="absent")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["session", "student"]

    def __str__(self):
        return f"{self.student.username} - {self.session.title} ({self.status})"


class CourseProgress(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="progress")
    completed_sessions = models.ManyToManyField(Session, related_name="completed_by")
    last_accessed = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    @property
    def completion_percentage(self):
        total_sessions = self.enrollment.course.sessions.count()
        if total_sessions == 0:
            return 0
        completed = self.completed_sessions.count()
        return int((completed / total_sessions) * 100)

    @property
    def attendance_rate(self):
        total_past_sessions = self.enrollment.course.sessions.filter(start_time__lt=timezone.now()).count()
        if total_past_sessions == 0:
            return 100
        attended = SessionAttendance.objects.filter(
            student=self.enrollment.student,
            session__course=self.enrollment.course,
            status__in=["present", "late"],
        ).count()
        return int((attended / total_past_sessions) * 100)

    def __str__(self):
        return f"{self.enrollment.student.username}'s progress in {self.enrollment.course.title}"


class Achievement(models.Model):
    TYPES = [
        ("attendance", "Perfect Attendance"),
        ("completion", "Course Completion"),
        ("participation", "Active Participation"),
        ("excellence", "Academic Excellence"),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="achievements")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="achievements")
    achievement_type = models.CharField(max_length=20, choices=TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    awarded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.title}"


class Review(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_given")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["student", "course"]

    def __str__(self):
        return f"{self.student.username}'s review of {self.course.title}"


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="payments",
        help_text="The enrollment this payment is associated with",
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        help_text="Specific session this payment is for, if any",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    stripe_payment_intent_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.session:
            return f"Payment for {self.enrollment} - {self.session.title}"
        return f"Payment for {self.enrollment}"


class ForumCategory(models.Model):
    """Categories for organizing forum discussions."""

    name = models.CharField(max_length=100)
    description = models.TextField()
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class")
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Forum Categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class ForumTopic(models.Model):
    """Individual forum topics/threads."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, related_name="topics")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_topics")
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title


class ForumReply(models.Model):
    """Replies to forum topics."""

    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_replies")
    content = models.TextField()
    is_solution = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Forum Replies"
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply by {self.author.username} on {self.topic.title}"


class PeerConnection(models.Model):
    """Connections between users for networking."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("blocked", "Blocked"),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_connections")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_connections")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["sender", "receiver"]

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.status})"


class PeerMessage(models.Model):
    """Direct messages between connected peers."""

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"


class StudyGroup(models.Model):
    """Study groups for collaborative learning."""

    name = models.CharField(max_length=200)
    description = models.TextField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="study_groups")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_groups")
    members = models.ManyToManyField(User, related_name="joined_groups")
    max_members = models.IntegerField(default=10)
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile instance when a new User is created."""
    if created and not hasattr(instance, "profile"):
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the Profile instance when the User is saved."""
    if hasattr(instance, "profile"):
        instance.profile.save()
    else:
        Profile.objects.create(user=instance)


class BlogPost(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blog_posts")
    content = models.TextField()
    excerpt = models.TextField(blank=True)
    featured_image = models.ImageField(upload_to="blog/images/%Y/%m/%d/", blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.status == "published" and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class BlogComment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blog_comments")
    content = models.TextField()
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"


@receiver(user_signed_up)
def set_user_type(sender, request, user, **kwargs):
    """Set the user type (teacher/student) when they sign up."""
    is_teacher = request.POST.get("is_teacher") == "on"
    profile = user.profile
    profile.is_teacher = is_teacher
    profile.save()


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart", null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Guest Cart ({self.session_key})"

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False, session_key__isnull=True)
                    | models.Q(user__isnull=True, session_key__isnull=False)
                ),
                name="cart_user_or_session_key",
            )
        ]

    @property
    def total(self):
        return sum(item.total for item in self.items.all())

    @property
    def item_count(self):
        return self.items.count()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            ("cart", "course"),
            ("cart", "session"),
        ]

    def clean(self):
        if not self.course and not self.session:
            raise ValidationError("Either a course or a session must be selected")
        if self.course and self.session:
            raise ValidationError("Cannot select both course and session")
        if self.session and not self.session.course.allow_individual_sessions:
            raise ValidationError("This course does not allow individual session registration")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total(self):
        if self.course:
            return self.course.price
        return self.session.price or 0

    def __str__(self):
        if self.course:
            return f"{self.course.title} (Full Course)"
        return f"{self.session.title} (Individual Session)"
