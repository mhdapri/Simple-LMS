import csv
import os
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from pymongo import MongoClient

from .models import Course, CourseMember


def get_mongo_collection(collection_name: str):
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    return db[collection_name]


@shared_task
def send_enrollment_email(user_id: int, course_id: int) -> dict:
    user = User.objects.filter(id=user_id).first()
    course = Course.objects.filter(id=course_id).first()
    if user and course:
        send_mail(
            subject=f"Enrollment confirmed for {course.name}",
            message=f"Hello {user.username}, you have successfully enrolled in {course.name}.",
            from_email=settings.DEFAULT_FROM_EMAIL or "noreply@example.com",
            recipient_list=[user.email] if user.email else [],
            fail_silently=True,
        )
    return {"user_id": user_id, "course_id": course_id, "status": "sent"}


@shared_task
def generate_certificate(user_id: int, course_id: int) -> dict:
    try:
        collection = get_mongo_collection("learning_analytics")
        collection.insert_one({
            "user_id": user_id,
            "course_id": course_id,
            "certificate_generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "generated",
        })
    except Exception:
        pass
    return {"user_id": user_id, "course_id": course_id, "status": "generated"}


@shared_task
def update_course_statistics() -> dict:
    courses = Course.objects.count()
    enrollments = CourseMember.objects.count()
    try:
        collection = get_mongo_collection("learning_analytics")
        collection.insert_one({
            "type": "course_statistics",
            "course_count": courses,
            "enrollment_count": enrollments,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass
    return {"course_count": courses, "enrollment_count": enrollments}


@shared_task
def export_course_report(course_id: int) -> dict:
    course = Course.objects.filter(id=course_id).first()
    output_dir = Path(settings.BASE_DIR) / "media" / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"course_{course_id}_report.csv"

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["course_id", "course_name", "enrollment_count"])
        writer.writerow([course.id if course else course_id, course.name if course else "", CourseMember.objects.filter(course_id=course_id).count()])

    return {"course_id": course_id, "path": str(output_path)}
