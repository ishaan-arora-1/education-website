from django import forms
from django.contrib.auth.models import User

from .models import Course


class BlogCommentForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "class": "block w-full border border-gray-300 dark:border-gray-600 rounded p-2",
            }
        ),
        required=True,
    )


class MessageForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "class": "block w-full border border-gray-300 dark:border-gray-600 rounded p-2",
            }
        ),
        required=True,
    )


class LearningInquiryForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    interests = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="What topics are you interested in learning?",
    )
    experience_level = forms.ChoiceField(
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ]
    )


class TeachingInquiryForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    expertise = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="What subjects do you specialize in?",
    )
    experience = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Describe your teaching experience",
    )


class StudyGroupForm(forms.Form):
    name = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
    max_members = forms.IntegerField(
        min_value=2,
        max_value=50,
        initial=10,
        help_text="Choose a number between 2 and 50",
    )
    is_private = forms.BooleanField(required=False)


class CourseSearchForm(forms.Form):
    query = forms.CharField(required=False)
    min_price = forms.DecimalField(required=False, min_value=0)
    max_price = forms.DecimalField(required=False, min_value=0)
    subject = forms.CharField(required=False)


class CourseUpdateForm(forms.ModelForm):
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


class CourseReviewForm(forms.Form):
    rating = forms.IntegerField(min_value=1, max_value=5)
    comment = forms.CharField(widget=forms.Textarea)


class MaterialUploadForm(forms.Form):
    title = forms.CharField(max_length=200)
    description = forms.CharField(widget=forms.Textarea, required=False)
    file = forms.FileField()


class TopicCreationForm(forms.Form):
    title = forms.CharField(max_length=200)
    content = forms.CharField(widget=forms.Textarea)


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    bio = forms.CharField(widget=forms.Textarea, required=False)

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and self.cleaned_data.get("bio"):
            user.profile.bio = self.cleaned_data["bio"]
            user.profile.save()
        return user
