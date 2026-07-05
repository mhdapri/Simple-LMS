from django.urls import path, include
from django.contrib import admin
from . import views

urlpatterns = [
    path('lab/course-list/baseline/', views.course_list_baseline), 
    path('lab/course-list/optimized/', views.course_list_optimized), 
    path('lab/course-members/baseline/', views.course_members_baseline), 
    path('lab/course-members/optimized/', views.course_members_optimized), 
    path('lab/course-dashboard/baseline/', views.course_dashboard_baseline), 
    path('lab/course-dashboard/optimized/', views.course_dashboard_optimized),
    path('lab/stats/', views.global_stats),
    path('lab/bulk-update/', views.bulk_update_price),

]
