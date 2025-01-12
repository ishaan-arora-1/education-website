from captcha.fields import CaptchaField, CaptchaTextInput
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from .models import Course, CourseMaterial, Profile, Review, Session, Subject


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    is_teacher = forms.BooleanField(required=False, label="Register as a teacher")
    captcha = CaptchaField()

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
            "is_teacher",
            "captcha",
        )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("bio", "expertise")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "expertise": forms.TextInput(attrs={"placeholder": "Your areas of expertise"}),
        }


class CourseCreationForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = (
            "title",
            "description",
            "learning_objectives",
            "prerequisites",
            "price",
            "max_students",
            "subject",
            "level",
            "tags",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "learning_objectives": forms.Textarea(attrs={"rows": 4}),
            "prerequisites": forms.Textarea(attrs={"rows": 4}),
            "tags": forms.TextInput(attrs={"placeholder": "Enter comma-separated tags"}),
        }

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price <= 0:
            raise forms.ValidationError("Price must be greater than zero")
        return price

    def clean_max_students(self):
        max_students = self.cleaned_data.get("max_students")
        if max_students <= 0:
            raise forms.ValidationError("Maximum number of students must be greater than zero")
        return max_students


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = (
            "title",
            "description",
            "learning_objectives",
            "prerequisites",
            "price",
            "max_students",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "learning_objectives": forms.Textarea(attrs={"rows": 4}),
            "prerequisites": forms.Textarea(attrs={"rows": 4}),
        }


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = [
            "title",
            "description",
            "start_time",
            "end_time",
            "is_virtual",
            "meeting_link",
            "location",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "start_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def clean_start_time(self):
        start_time = self.cleaned_data.get("start_time")
        if not start_time:
            raise forms.ValidationError("Start time is required.")
        return start_time

    def clean_end_time(self):
        end_time = self.cleaned_data.get("end_time")
        start_time = self.cleaned_data.get("start_time")

        if not end_time:
            raise forms.ValidationError("End time is required.")

        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("End time must be after start time.")

        return end_time

    def clean(self):
        cleaned_data = super().clean()
        is_virtual = cleaned_data.get("is_virtual")
        meeting_link = cleaned_data.get("meeting_link")
        location = cleaned_data.get("location")

        if is_virtual and not meeting_link:
            self.add_error("meeting_link", "Meeting link is required for virtual sessions.")
        elif not is_virtual and not location:
            self.add_error("location", "Location is required for in-person sessions.")

        return cleaned_data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 4}),
        }


class CourseMaterialForm(forms.ModelForm):
    class Meta:
        model = CourseMaterial
        fields = (
            "title",
            "description",
            "material_type",
            "file",
            "session",
            "is_downloadable",
            "order",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "order": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course:
            self.fields["session"].queryset = course.sessions.all()


class TailwindCaptchaTextInput(CaptchaTextInput):
    template_name = "captcha/widget.html"

    def __init__(self, attrs=None):
        # Add Tailwind classes to the input field and align to the right of the image
        default_attrs = {
            "class": "border border-gray-300 rounded p-2",  # Added margin-left to align right of the image
            "placeholder": "Enter CAPTCHA",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)


class TeacherSignupForm(forms.Form):
    email = forms.EmailField()
    subject = forms.CharField(max_length=100)
    captcha = CaptchaField(widget=TailwindCaptchaTextInput)

    def save(self):
        email = self.cleaned_data["email"]
        subject_name = self.cleaned_data["subject"]

        # Create user with email as username
        username = email.split("@")[0]
        random_password = get_random_string(length=30)
        user = User.objects.create_user(username=username, email=email, password=random_password)

        # Set user as teacher
        profile = user.profile
        profile.is_teacher = True
        profile.save()

        # Create subject
        subject, created = Subject.objects.get_or_create(
            name=subject_name,
            defaults={
                "slug": slugify(subject_name),
                "description": f"Courses about {subject_name}",
            },
        )

        return user, subject
