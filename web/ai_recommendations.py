from collections import defaultdict

import numpy as np
from django.db.models import Avg, Case, Count, When
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import Course, CourseMaterial, CourseProgress, Enrollment, Review, Session
from .recommendations import get_popular_courses


def get_course_content_features(course):
    """Extract and combine all textual content from a course."""
    content = [
        course.title,
        course.description,
        course.learning_objectives,
        course.prerequisites,
        course.tags,
        course.subject,
        course.level,
    ]

    # Add session information
    sessions = Session.objects.filter(course=course)
    for session in sessions:
        content.extend([session.title, session.description])

    # Add material information
    materials = CourseMaterial.objects.filter(course=course)
    for material in materials:
        content.extend([material.title, material.description])

    return " ".join(filter(None, content))


def build_content_similarity_matrix():
    """Build a content-based similarity matrix for all courses."""
    courses = Course.objects.filter(status="published")
    course_contents = [get_course_content_features(course) for course in courses]

    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(course_contents)

    # Calculate similarity matrix
    similarity_matrix = cosine_similarity(tfidf_matrix)

    return {course.id: sim for course, sim in zip(courses, similarity_matrix)}


def get_user_course_history(user):
    """Analyze user's course history and behavior."""
    enrollments = Enrollment.objects.filter(student=user)
    history = defaultdict(dict)

    for enrollment in enrollments:
        # Get progress information
        progress = CourseProgress.objects.filter(enrollment=enrollment).first()
        if progress:
            completion_rate = progress.completion_percentage
            attendance_rate = progress.attendance_rate
        else:
            completion_rate = attendance_rate = 0

        # Get review information
        review = Review.objects.filter(student=user, course=enrollment.course).first()
        rating = review.rating if review else None

        history[enrollment.course.id] = {
            "completion_rate": completion_rate,
            "attendance_rate": attendance_rate,
            "rating": rating,
            "subject": enrollment.course.subject,
            "level": enrollment.course.level,
            "tags": enrollment.course.tags.split(","),
        }

    return history


def analyze_learning_patterns(user):
    """Analyze user's learning patterns and preferences."""
    history = get_user_course_history(user)
    patterns = {
        "preferred_categories": defaultdict(int),
        "preferred_levels": defaultdict(int),
        "preferred_tags": defaultdict(int),
        "avg_completion_rate": 0,
        "avg_attendance_rate": 0,
        "avg_rating": 0,
    }

    if not history:
        return patterns

    # Analyze preferences
    for course_data in history.values():
        patterns["preferred_subjects"][course_data["subject"]] += 1
        patterns["preferred_levels"][course_data["level"]] += 1
        for tag in course_data["tags"]:
            if tag.strip():
                patterns["preferred_tags"][tag.strip()] += 1

        if course_data["completion_rate"]:
            patterns["avg_completion_rate"] += course_data["completion_rate"]
        if course_data["attendance_rate"]:
            patterns["avg_attendance_rate"] += course_data["attendance_rate"]
        if course_data["rating"]:
            patterns["avg_rating"] += course_data["rating"]

    # Calculate averages
    num_courses = len(history)
    patterns["avg_completion_rate"] /= num_courses if num_courses > 0 else 1
    patterns["avg_attendance_rate"] /= num_courses if num_courses > 0 else 1
    patterns["avg_rating"] /= num_courses if num_courses > 0 else 1

    return patterns


def get_ai_recommendations(user, limit=6):
    """
    Generate AI-driven course recommendations using:
    1. Content-based similarity
    2. User learning patterns
    3. Collaborative filtering signals
    """
    if not user.is_authenticated:
        return get_popular_courses(limit)

    # Get user's learning patterns
    patterns = analyze_learning_patterns(user)

    # Get content similarity matrix
    similarity_matrix = build_content_similarity_matrix()

    # Get base queryset of available courses
    available_courses = (
        Course.objects.filter(status="published")
        .exclude(enrollments__student=user)
        .annotate(
            avg_rating=Avg("reviews__rating"),
            enrollment_count=Count("enrollments"),
            completion_rate=Avg("enrollments__progress__completion_percentage"),
        )
    )

    # Score each course based on multiple factors
    course_scores = {}
    for course in available_courses:
        score = 0

        # Content similarity score
        if user.enrollments.exists():
            enrolled_courses = user.enrollments.values_list("course_id", flat=True)
            similarity_scores = [
                similarity_matrix[course.id][enrolled_course_id]
                for enrolled_course_id in enrolled_courses
                if course.id in similarity_matrix and enrolled_course_id in similarity_matrix
            ]
            if similarity_scores:
                score += np.mean(similarity_scores) * 0.4  # 40% weight

        # Learning pattern match score
        if patterns["preferred_categories"]:
            subject_weight = patterns["preferred_categories"].get(course.subject, 0)
            score += (subject_weight / max(patterns["preferred_categories"].values())) * 0.2  # 20% weight

        if patterns["preferred_levels"]:
            level_weight = patterns["preferred_levels"].get(course.level, 0)
            score += (level_weight / max(patterns["preferred_levels"].values())) * 0.1  # 10% weight

        # Course performance score
        if course.avg_rating:
            score += (course.avg_rating / 5.0) * 0.15  # 15% weight
        if course.completion_rate:
            score += (course.completion_rate / 100.0) * 0.15  # 15% weight

        course_scores[course.id] = score

    # Sort courses by score and return top recommendations
    sorted_courses = sorted(course_scores.items(), key=lambda x: x[1], reverse=True)
    recommended_course_ids = [course_id for course_id, _ in sorted_courses[:limit]]

    # Preserve order while fetching courses
    preserved = Case(*[When(id=id, then=pos) for pos, id in enumerate(recommended_course_ids)])
    return available_courses.filter(id__in=recommended_course_ids).order_by(preserved)
