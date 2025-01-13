from allauth.account.forms import LoginForm, SignupForm
from captcha.fields import CaptchaField
from django import forms
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
    "CustomLoginForm",
]


class UserRegistrationForm(SignupForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=TailwindInput(attrs={"placeholder": "First Name"}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=TailwindInput(attrs={"placeholder": "Last Name"}),
    )
    is_teacher = forms.BooleanField(
        required=False,
        label="Register as a teacher",
        widget=TailwindCheckboxInput(),
    )
    captcha = CaptchaField(widget=TailwindCaptchaTextInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Update email field
        self.fields["email"].widget = TailwindEmailInput(
            attrs={
                "placeholder": "your.email@example.com",
                "value": self.initial.get("email", ""),
            }
        )
        # Update password field
        self.fields["password1"].widget = TailwindInput(
            attrs={
                "type": "password",
                "placeholder": "Choose a secure password",
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white"
                ),
            }
        )

        # Preserve values on form errors
        if self.data:
            for field_name in ["first_name", "last_name", "email"]:
                if field_name in self.data:
                    self.fields[field_name].widget.attrs["value"] = self.data[field_name]

    def save(self, request):
        # First call parent's save to create the user and send verification email
        user = super().save(request)

        # Then update the additional fields
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save()

        # Update the user's profile
        if self.cleaned_data.get("is_teacher"):
            user.profile.is_teacher = True
            user.profile.save()

        # Return the user object
        return user


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
            "image",
            "learning_objectives",
            "prerequisites",
            "price",
            "allow_individual_sessions",
            "max_students",
            "subject",
            "level",
            "tags",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "image": TailwindFileInput(
                attrs={
                    "accept": "image/*",
                    "help_text": "Course image must be 300x150 pixels",
                }
            ),
            "learning_objectives": forms.Textarea(attrs={"rows": 4}),
            "prerequisites": forms.Textarea(attrs={"rows": 4}),
            "allow_individual_sessions": TailwindCheckboxInput(
                attrs={"help_text": ("Allow students to register for individual sessions")}
            ),
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
            msg = "Maximum number of students must be greater than zero"
            raise forms.ValidationError(msg)
        return max_students


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "image",
            "learning_objectives",
            "prerequisites",
            "price",
            "allow_individual_sessions",
            "max_students",
            "subject",
            "level",
            "tags",
        ]
        widgets = {
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 4}),
            "image": TailwindFileInput(
                attrs={
                    "accept": "image/*",
                    "help_text": "Course image must be 300x150 pixels",
                }
            ),
            "learning_objectives": TailwindTextarea(attrs={"rows": 4}),
            "prerequisites": TailwindTextarea(attrs={"rows": 4}),
            "price": TailwindNumberInput(attrs={"min": "0", "step": "0.01"}),
            "allow_individual_sessions": TailwindCheckboxInput(
                attrs={"help_text": ("Allow students to register for individual sessions")}
            ),
            "max_students": TailwindNumberInput(attrs={"min": "1"}),
            "subject": TailwindSelect(),
            "level": TailwindSelect(),
            "tags": TailwindInput(attrs={"placeholder": "Enter comma-separated tags"}),
        }

    def clean_max_students(self):
        max_students = self.cleaned_data.get("max_students")
        if max_students <= 0:
            msg = "Maximum number of students must be greater than zero"
            raise forms.ValidationError(msg)
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
            "price",
        ]
        widgets = {
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 4}),
            "start_time": TailwindDateTimeInput(),
            "end_time": TailwindDateTimeInput(),
            "is_virtual": TailwindCheckboxInput(),
            "meeting_link": TailwindInput(attrs={"type": "url"}),
            "location": TailwindInput(),
            "price": TailwindNumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                    "help_text": ("Price for individual session registration"),
                }
            ),
        }
        help_texts = {
            "start_time": "Click to select the session start date and time",
            "end_time": "Click to select the session end date and time",
        }

    def clean(self):
        cleaned_data = super().clean()
        is_virtual = cleaned_data.get("is_virtual")
        meeting_link = cleaned_data.get("meeting_link")
        location = cleaned_data.get("location")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        price = cleaned_data.get("price")

        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after start time.")

        if is_virtual and not meeting_link:
            msg = "Meeting link is required for virtual sessions."
            self.add_error("meeting_link", msg)
        elif not is_virtual and not location:
            msg = "Location is required for in-person sessions."
            self.add_error("location", msg)

        if price is not None and price < 0:
            self.add_error("price", "Price cannot be negative.")

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


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].widget.attrs.update(
            {
                "class": (
                    "block w-full rounded-md border-0 py-2 px-4 "
                    "text-gray-900 dark:text-white shadow-sm "
                    "ring-1 ring-inset ring-gray-300 "
                    "dark:ring-gray-600 "
                    "placeholder:text-gray-400 "
                    "focus:ring-2 focus:ring-inset "
                    "focus:ring-orange-500 dark:bg-gray-700 "
                    "sm:text-base sm:leading-6"
                )
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": (
                    "block w-full rounded-md border-0 py-2 px-4 "
                    "text-gray-900 dark:text-white shadow-sm "
                    "ring-1 ring-inset ring-gray-300 "
                    "dark:ring-gray-600 "
                    "placeholder:text-gray-400 "
                    "focus:ring-2 focus:ring-inset "
                    "focus:ring-orange-500 dark:bg-gray-700 "
                    "sm:text-base sm:leading-6 pr-10"
                )
            }
        )
        self.fields["remember"].widget.attrs.update(
            {
                "class": (
                    "h-4 w-4 text-orange-500 "
                    "focus:ring-orange-500 "
                    "border-gray-300 dark:border-gray-600 "
                    "rounded cursor-pointer"
                )
            }
        )

    def clean(self):
        cleaned_data = super().clean()

        # Check if user exists and can log in
        if "login" in cleaned_data:
            email = cleaned_data["login"]
            try:
                User.objects.get(email=email)
            except User.DoesNotExist:
                raise forms.ValidationError(
                    "No account found with this email address. Please check the email or sign up."
                )

        return cleaned_data
