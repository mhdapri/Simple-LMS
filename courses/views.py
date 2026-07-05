from django.db.models import Avg, Count, Max, Min, Prefetch
from django.http import JsonResponse
from .models import Comment, Course, CourseContent, CourseMember

# =============================================================================
# BAGIAN 1 - Views dengan N+1 Problem (Baseline)
# =============================================================================

def course_list_baseline(request):
    """Mengambil semua kursus tanpa optimasi (N+1 pada field teacher)"""
    courses = Course.objects.all()
    data = []
    for course in courses:
        data.append({
            "id": course.id,
            "name": course.name,
            "teacher": course.teacher.username,  # Ini memicu query baru setiap loop
        })
    return JsonResponse(data, safe=False)

def course_members_baseline(request):
    """Mengambil anggota tanpa optimasi (N+1 pada user dan course)"""
    members = CourseMember.objects.all()
    data = []
    for m in members:
        data.append({
            "user": m.user_id.username,
            "course": m.course_id.name,
            "role": m.roles
        })
    return JsonResponse(data, safe=False)

def course_dashboard_baseline(request):
    """Dashboard sederhana tanpa optimasi"""
    courses = Course.objects.all()
    data = []
    for c in courses:
        data.append({
            "course": c.name,
            "total_content": c.coursecontent_set.count(), # Query setiap loop
        })
    return JsonResponse(data, safe=False)


# =============================================================================
# BAGIAN 2 - Views Teroptimasi (Select & Prefetch Related)
# =============================================================================

def course_list_optimized(request):
    """Menggunakan select_related untuk join tabel User (Teacher)"""
    courses = Course.objects.select_related('teacher').all()
    data = [{"name": c.name, "teacher": c.teacher.username} for c in courses]
    return JsonResponse(data, safe=False)

def course_members_optimized(request):
    """Menggunakan select_related untuk join user_id dan course_id"""
    members = CourseMember.objects.select_related('user_id', 'course_id').all()
    data = [{"user": m.user_id.username, "course": m.course_id.name} for m in members]
    return JsonResponse(data, safe=False)

def course_dashboard_optimized(request):
    """Menggunakan Prefetch untuk mengambil count konten sekaligus"""
    courses = Course.objects.annotate(total_content=Count('coursecontent'))
    data = [{"course": c.name, "total_content": c.total_content} for c in courses]
    return JsonResponse(data, safe=False)

# Fungsi tambahan agar tidak error jika dipanggil
def some_view(request):
    return JsonResponse({"status": "ok"})

def global_stats(request):
    """Kalkulasi harga dan jumlah total kursus dalam 1 query saja"""
    stats = Course.objects.aggregate(
        total_course=Count('id'),
        harga_termahal=Max('price'),
        harga_termurah=Min('price'),
        rata_rata_harga=Avg('price')
    )
    return JsonResponse(stats)


def bulk_update_price(request):
    """Update harga semua kursus (naik 10%) secara massal"""
    # Menggunakan F() expression untuk update langsung di database
    updated_count = Course.objects.all().update(price=F('price') * 1.1)
    return JsonResponse({
        "status": "success",
        "message": f"Berhasil memperbarui harga {updated_count} mata kuliah."
    })

# Fungsi dummy untuk mengetes koneksi route
def some_view(request):
    return JsonResponse({"status": "Aplikasi LMS Siap!"})