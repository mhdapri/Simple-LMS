from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from courses.api import build_course_list_cache_key


class NinjaApiTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="instructor",
            password="password123",
            email="instructor@example.com"
        )
        Group.objects.get_or_create(name="instructors")
        self.instructor.groups.add(Group.objects.get(name="instructors"))

    def test_register_and_login_flow(self):
        response = self.client.post(
            "/api/auth/register",
            {
                "username": "student1",
                "email": "student1@example.com",
                "password": "StrongPass123",
                "role": "student",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="student1").exists())

        login_response = self.client.post(
            "/api/auth/login",
            {
                "username": "student1",
                "password": "StrongPass123",
            },
            content_type="application/json",
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertIn("access_token", login_response.json())
        self.assertIn("refresh_token", login_response.json())

    def test_course_listing_and_detail(self):
        course = self.instructor.course_set.create(
            name="Django Basics",
            description="Intro",
            price=50000,
        )

        response = self.client.get("/api/courses")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["name"], "Django Basics")

        detail_response = self.client.get(f"/api/courses/{course.id}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["id"], course.id)

    def test_course_listing_is_cached(self):
        cache.clear()
        self.instructor.course_set.create(name="Caching Basics", description="Intro", price=10000)

        response = self.client.get("/api/courses?page=1&page_size=5&search=caching")
        self.assertEqual(response.status_code, 200)

        cache_key = build_course_list_cache_key(page=1, page_size=5, search="caching", teacher_id=None)
        self.assertIsNotNone(cache.get(cache_key))
