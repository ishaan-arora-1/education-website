from captcha.fields import CaptchaField
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.utils.crypto import get_random_string

from .models import Course, CourseMaterial, Profile, Review, Session, Subject
from .widgets import (
    TailwindCaptchaTextInput,
    TailwindCheckboxInput,
    TailwindDateTimeInput,
    TailwindEmailInput,
    TailwindFileInput,
    TailwindInput,
    TailwindNumberInput,
    TailwindSelect,
    TailwindTextarea,
)

__all__ = [
    "UserRegistrationForm",
    "ProfileForm",
    "CourseCreationForm",
    "CourseForm",
    "SessionForm",
    "ReviewForm",
    "CourseMaterialForm",
    "TeacherSignupForm",
    "ProfileUpdateForm",
]


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=TailwindEmailInput())
    first_name = forms.CharField(required=True, widget=TailwindInput())
    last_name = forms.CharField(required=True, widget=TailwindInput())
    is_teacher = forms.BooleanField(required=False, label="Register as a teacher", widget=TailwindCheckboxInput())
    captcha = CaptchaField(widget=TailwindCaptchaTextInput)

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
        widgets = {
            "username": TailwindInput(),
            "password1": TailwindInput(attrs={"type": "password"}),
            "password2": TailwindInput(attrs={"type": "password"}),
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("bio", "expertise")
        widgets = {
            "bio": TailwindTextarea(attrs={"rows": 4}),
            "expertise": TailwindInput(attrs={"placeholder": "Your areas of expertise"}),
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
        fields = [
            "title",
            "description",
            "learning_objectives",
            "prerequisites",
            "price",
            "max_students",
            "subject",
            "level",
            "tags",
        ]
        widgets = {
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 4}),
            "learning_objectives": TailwindTextarea(attrs={"rows": 4}),
            "prerequisites": TailwindTextarea(attrs={"rows": 4}),
            "price": TailwindNumberInput(attrs={"min": "0", "step": "0.01"}),
            "max_students": TailwindNumberInput(attrs={"min": "1"}),
            "subject": TailwindSelect(),
            "level": TailwindSelect(),
            "tags": TailwindInput(attrs={"placeholder": "Enter comma-separated tags"}),
        }

    def clean_max_students(self):
        max_students = self.cleaned_data.get("max_students")
        if max_students <= 0:
            raise forms.ValidationError("Maximum number of students must be greater than zero")
        return max_students


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
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 4}),
            "start_time": TailwindDateTimeInput(),
            "end_time": TailwindDateTimeInput(),
            "is_virtual": TailwindCheckboxInput(),
            "meeting_link": TailwindInput(attrs={"type": "url"}),
            "location": TailwindInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_virtual = cleaned_data.get("is_virtual")
        meeting_link = cleaned_data.get("meeting_link")
        location = cleaned_data.get("location")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after start time.")

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
            "rating": TailwindNumberInput(attrs={"min": "1", "max": "5"}),
            "comment": TailwindTextarea(attrs={"rows": 4}),
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
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 3}),
            "material_type": TailwindSelect(),
            "file": TailwindFileInput(),
            "session": TailwindSelect(),
            "is_downloadable": TailwindCheckboxInput(),
            "order": TailwindNumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course:
            self.fields["session"].queryset = course.sessions.all()


class TeacherSignupForm(forms.Form):
    email = forms.EmailField(widget=TailwindEmailInput())
    subject = forms.CharField(max_length=100, widget=TailwindInput())
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


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, widget=TailwindInput())
    last_name = forms.CharField(max_length=30, required=False, widget=TailwindInput())
    email = forms.EmailField(required=True, widget=TailwindEmailInput())
    bio = forms.CharField(
        required=False,
        widget=TailwindTextarea(attrs={"rows": 4}),
        help_text="Tell us about yourself",
    )
    expertise = forms.CharField(
        max_length=200,
        required=False,
        widget=TailwindInput(),
        help_text="List your areas of expertise (e.g. Python, Machine Learning, Web Development)",
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            try:
                profile = self.instance.profile
                self.fields["bio"].initial = profile.bio
                self.fields["expertise"].initial = profile.expertise
            except Profile.DoesNotExist:
                pass

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, created = Profile.objects.get_or_create(user=user)
            profile.bio = self.cleaned_data["bio"]
            profile.expertise = self.cleaned_data["expertise"]
            profile.save()
        return user
