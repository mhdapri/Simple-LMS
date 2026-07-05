import json
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional

import jwt
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django_ratelimit.decorators import ratelimit
from ninja import NinjaAPI, Query, Schema
from ninja.errors import HttpError
from ninja.security import HttpBearer
from pymongo import MongoClient

from .models import Course, CourseContent, CourseMember, LessonProgress
from .tasks import send_enrollment_email, generate_certificate


def build_course_list_cache_key(page: int, page_size: int, search: Optional[str] = None, teacher_id: Optional[int] = None) -> str:
    return f"courses:list:{page}:{page_size}:{search or ''}:{teacher_id or 0}"


def get_mongo_collection(collection_name: str):
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    return db[collection_name]


def log_activity(action: str, user_id: Optional[int] = None, course_id: Optional[int] = None, payload: Optional[dict] = None) -> None:
    try:
        collection = get_mongo_collection("activity_logs")
        document = {
            "action": action,
            "user_id": user_id,
            "course_id": course_id,
            "payload": payload or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        collection.insert_one(document)
    except Exception:
        pass

api = NinjaAPI(title="Simple LMS API", version="1.0.0", docs_url="/docs")


class RegisterSchema(Schema):
    username: str
    email: str
    password: str
    role: str = "student"
    first_name: str = ""
    last_name: str = ""


class LoginSchema(Schema):
    username: str
    password: str


class RefreshSchema(Schema):
    refresh_token: str


class TokenResponse(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(Schema):
    id: int
    username: str
    email: Optional[str] = None
    first_name: str = ""
    last_name: str = ""
    role: str


class CourseOut(Schema):
    id: int
    name: str
    description: str
    price: int
    teacher_id: int
    teacher_name: str
    created_at: datetime
    updated_at: datetime


class CourseCreateSchema(Schema):
    name: str
    description: str = ""
    price: int = 10000


class CourseUpdateSchema(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None


class CourseListQuery(Schema):
    search: Optional[str] = None
    teacher_id: Optional[int] = None
    page: int = 1
    page_size: int = 10


class EnrollmentCreateSchema(Schema):
    course_id: int


class LessonProgressSchema(Schema):
    content_id: int


class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        payload = decode_token(token)
        if not payload:
            return None
        if payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        user = User.objects.filter(id=user_id, is_active=True).first()
        return user


jwt_auth = JWTAuth()


def create_tokens(user: User) -> dict:
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": str(user.id),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=30)).timestamp()),
    }
    refresh_payload = {
        "sub": str(user.id),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=7)).timestamp()),
    }
    return {
        "access_token": jwt.encode(access_payload, settings.SECRET_KEY, algorithm="HS256"),
        "refresh_token": jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm="HS256"),
    }


def decode_token(token: str):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return None


def get_current_user(request):
    user = getattr(request, "user", None)
    if user:
        return user

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None
    return User.objects.filter(id=user_id, is_active=True).first()


def get_user_role(user: User) -> str:
    if user.is_superuser:
        return "admin"
    names = {group.name.lower() for group in user.groups.all()}
    if "admins" in names or "admin" in names:
        return "admin"
    if "instructors" in names or "instructor" in names:
        return "instructor"
    if "students" in names or "student" in names:
        return "student"
    return "student"


def assign_role(user: User, role: str) -> None:
    role_key = (role or "student").lower()
    group_name = {
        "student": "students",
        "instructor": "instructors",
        "admin": "admins",
    }.get(role_key, "students")
    Group.objects.get_or_create(name=group_name)
    user.groups.clear()
    user.groups.add(Group.objects.get(name=group_name))


def role_required(*required_roles):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = get_current_user(request)
            if not user:
                raise HttpError(401, "Authentication required")
            if not user.is_active:
                raise HttpError(403, "User is inactive")
            role = get_user_role(user)
            if role not in required_roles:
                raise HttpError(403, "Permission denied")
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


is_instructor = role_required("instructor", "admin")
is_admin = role_required("admin")
is_student = role_required("student", "instructor", "admin")


@api.post("/auth/register", response={201: TokenResponse}, tags=["auth"])
def register(request, payload: RegisterSchema):
    if User.objects.filter(username=payload.username).exists():
        raise HttpError(400, "Username already exists")

    user = User.objects.create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    assign_role(user, payload.role)
    tokens = create_tokens(user)
    return 201, TokenResponse(**tokens)


@api.post("/auth/login", response={200: TokenResponse}, tags=["auth"])
@ratelimit(key="ip", rate=f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_WINDOW}s", block=True)
def login(request, payload: LoginSchema):
    user = authenticate(username=payload.username, password=payload.password)
    if not user:
        raise HttpError(401, "Invalid credentials")
    tokens = create_tokens(user)
    return 200, TokenResponse(**tokens)


@api.post("/auth/refresh", response={200: TokenResponse}, tags=["auth"])
def refresh_token(request, payload: RefreshSchema):
    decoded = decode_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise HttpError(401, "Invalid refresh token")
    user = User.objects.filter(id=decoded.get("sub"), is_active=True).first()
    if not user:
        raise HttpError(401, "Invalid refresh token")
    tokens = create_tokens(user)
    return 200, TokenResponse(**tokens)


@api.get("/auth/me", auth=jwt_auth, response=UserOut, tags=["auth"])
def me(request):
    user = get_current_user(request)
    if not user:
        raise HttpError(401, "Authentication required")
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=get_user_role(user),
    )


@api.put("/auth/me", auth=jwt_auth, response=UserOut, tags=["auth"])
def update_me(request, payload: RegisterSchema):
    user = get_current_user(request)
    if not user:
        raise HttpError(401, "Authentication required")

    if payload.username and payload.username != user.username:
        if User.objects.filter(username=payload.username).exclude(id=user.id).exists():
            raise HttpError(400, "Username already exists")
        user.username = payload.username
    if payload.email:
        user.email = payload.email
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.password:
        user.set_password(payload.password)
    if payload.role:
        assign_role(user, payload.role)
    user.save()
    return UserOut(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=get_user_role(user),
    )


@api.get("/courses", response=dict, tags=["courses"])
@ratelimit(key="ip", rate=f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_WINDOW}s", block=True)
def list_courses(request, filters: CourseListQuery = Query(...)):
    cache_key = build_course_list_cache_key(filters.page, filters.page_size, filters.search, filters.teacher_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    queryset = Course.objects.select_related("teacher").all()

    if filters.search:
        queryset = queryset.filter(name__icontains=filters.search)
    if filters.teacher_id:
        queryset = queryset.filter(teacher_id=filters.teacher_id)

    queryset = queryset.order_by("-created_at")
    paginator = Paginator(queryset, filters.page_size)
    page_obj = paginator.get_page(filters.page)

    results = [
        {
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "price": course.price,
            "teacher_id": course.teacher_id,
            "teacher_name": course.teacher.username,
            "created_at": course.created_at,
            "updated_at": course.updated_at,
        }
        for course in page_obj.object_list
    ]

    response_payload = {
        "count": paginator.count,
        "page": filters.page,
        "page_size": filters.page_size,
        "results": results,
    }
    cache.set(cache_key, response_payload, 300)
    return response_payload


@api.get("/courses/{course_id}", response=CourseOut, tags=["courses"])
def course_detail(request, course_id: int):
    cache_key = f"courses:detail:{course_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    course = get_object_or_404(Course.objects.select_related("teacher"), id=course_id)
    payload = CourseOut(
         id=course.id,
         name=course.name,
         description=course.description,
         price=course.price,
         teacher_id=course.teacher_id,
         teacher_name=course.teacher.username,
         created_at=course.created_at,
         updated_at=course.updated_at,
    )
    cache.set(cache_key, payload, 300)
    return payload
        id=course.id,
        name=course.name,
        description=course.description,
        price=course.price,
        teacher_id=course.teacher_id,
        teacher_name=course.teacher.username,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


@api.post("/courses", auth=jwt_auth, response={201: CourseOut}, tags=["courses"])
@is_instructor
def create_course(request, payload: CourseCreateSchema):
    user = get_current_user(request)
    course = Course.objects.create(
        name=payload.name,
        description=payload.description,
        price=payload.price,
        teacher=user,
    )
    cache.delete_many([build_course_list_cache_key(1, 10, None, None), build_course_list_cache_key(1, 5, None, None)])
    cache.delete_pattern("courses:list:*")
    log_activity("course_created", user_id=user.id, course_id=course.id)
    return 201, CourseOut(
        id=course.id,
        name=course.name,
        description=course.description,
        price=course.price,
        teacher_id=course.teacher_id,
        teacher_name=course.teacher.username,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


@api.patch("/courses/{course_id}", auth=jwt_auth, response=CourseOut, tags=["courses"])
@is_instructor
def update_course(request, course_id: int, payload: CourseUpdateSchema):
    user = get_current_user(request)
    course = get_object_or_404(Course, id=course_id)
    if course.teacher_id != user.id and get_user_role(user) != "admin":
        raise HttpError(403, "Only the course owner or admin can update this course")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(course, field, value)
    course.save()
    cache.delete(f"courses:detail:{course.id}")
    cache.delete_pattern("courses:list:*")
    log_activity("course_updated", user_id=user.id, course_id=course.id)
    return CourseOut(
        id=course.id,
        name=course.name,
        description=course.description,
        price=course.price,
        teacher_id=course.teacher_id,
        teacher_name=course.teacher.username,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


@api.delete("/courses/{course_id}", auth=jwt_auth, tags=["courses"])
@is_admin
def delete_course(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)
    course.delete()
    cache.delete_pattern("courses:list:*")
    cache.delete(f"courses:detail:{course_id}")
    log_activity("course_deleted", course_id=course_id)
    return {"deleted": True, "course_id": course_id}


@api.post("/enrollments", auth=jwt_auth, response={201: dict}, tags=["enrollments"])
@is_student
def enroll_course(request, payload: EnrollmentCreateSchema):
    user = get_current_user(request)
    course = get_object_or_404(Course, id=payload.course_id)
    member, created = CourseMember.objects.get_or_create(
        course_id=course,
        user_id=user,
        defaults={"roles": "std"},
    )
    log_activity("enrolled", user_id=user.id, course_id=course.id)
    send_enrollment_email.delay(user.id, course.id)
    return 201, {
        "message": "Enrolled successfully" if created else "Already enrolled",
        "course_id": course.id,
        "role": member.roles,
    }


@api.get("/enrollments/my-courses", auth=jwt_auth, response=list[dict], tags=["enrollments"])
@is_student
def my_courses(request):
    user = get_current_user(request)
    enrollments = CourseMember.objects.filter(user_id=user).select_related("course_id")
    return [
        {
            "course_id": enrollment.course_id.id,
            "name": enrollment.course_id.name,
            "role": enrollment.roles,
        }
        for enrollment in enrollments
    ]


@api.post("/enrollments/{course_id}/progress", auth=jwt_auth, response=dict, tags=["enrollments"])
@is_student
def mark_lesson_complete(request, course_id: int, payload: LessonProgressSchema):
    user = get_current_user(request)
    course = get_object_or_404(Course, id=course_id)
    member = get_object_or_404(CourseMember, course_id=course, user_id=user)
    content = get_object_or_404(CourseContent, id=payload.content_id, course_id=course)
    progress, created = LessonProgress.objects.get_or_create(member=member, content=content)
    log_activity("lesson_completed", user_id=user.id, course_id=course.id, payload={"content_id": content.id})
    if created:
        generate_certificate.delay(user.id, course.id)
    return {
        "message": "Lesson marked complete" if created else "Lesson already completed",
        "course_id": course.id,
        "content_id": content.id,
        "completed": True,
    }
