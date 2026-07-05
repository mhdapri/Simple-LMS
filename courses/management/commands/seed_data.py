"""
Management command untuk mengisi database dengan data dummy.

Jalankan dengan:
    python manage.py seed_data

Data yang dibuat:
    - 20 User pengajar (dosen01 - dosen20)
    - 80 User mahasiswa (mhs001 - mhs080)
    - 100 Course (mata kuliah)
    - 500 CourseMember (anggota kelas)
    - 300 CourseContent (konten/materi kelas)
    - 1000+ Comment (komentar pada konten)

Semua operasi INSERT menggunakan bulk_create (sesuai Modul 05 Bagian 6).
Command ini idempoten: aman dijalankan berulang kali tanpa membuat duplikat.

Referensi: Modul 05 - Bagian 6: Bulk Operations
"""

import random
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from courses.models import Course, CourseMember, CourseContent, Comment


# =============================================================================
# Kamus data Indonesia untuk menghasilkan konten yang realistis
# =============================================================================

FIRST_NAMES = [
    'Budi', 'Siti', 'Ahmad', 'Dewi', 'Reza',
    'Putri', 'Andi', 'Rina', 'Hendra', 'Yuli',
    'Fajar', 'Nisa', 'Dimas', 'Ayu', 'Rizki',
    'Lestari', 'Wahyu', 'Maya', 'Bagas', 'Citra',
]

LAST_NAMES = [
    'Santoso', 'Wijaya', 'Kusuma', 'Rahayu', 'Pratama',
    'Sari', 'Hidayat', 'Permata', 'Nugroho', 'Lestari',
    'Wibowo', 'Mahendra', 'Putra', 'Dewi', 'Susanto',
    'Kurniawan', 'Handoko', 'Utama', 'Saputra', 'Prabowo',
]

SUBJECTS = [
    'Pemrograman Web',
    'Basis Data',
    'Algoritma dan Struktur Data',
    'Jaringan Komputer',
    'Sistem Operasi',
    'Kecerdasan Buatan',
    'Pemrograman Mobile',
    'Keamanan Siber',
    'Rekayasa Perangkat Lunak',
    'Pemrograman Python',
    'Pemrograman Java',
    'Manajemen Proyek TI',
    'Analisis dan Desain Sistem',
    'Komputasi Awan',
    'Data Mining',
    'Statistika',
    'Matematika Diskrit',
    'Arsitektur Komputer',
    'Grafika Komputer',
    'Interaksi Manusia Komputer',
]

CONTENT_PREFIXES = [
    'Pengantar',
    'Konsep Dasar',
    'Praktikum',
    'Latihan',
    'Kuis',
    'Modul',
    'Materi',
    'Diskusi',
    'Proyek',
    'Tugas',
]

CONTENT_TOPICS = [
    'Variabel dan Tipe Data',
    'Struktur Kontrol',
    'Fungsi dan Prosedur',
    'Array dan List',
    'Object Oriented Programming',
    'Database Design',
    'Query SQL',
    'Normalisasi Database',
    'REST API',
    'Autentikasi dan Otorisasi',
    'Deployment Aplikasi',
    'Unit Testing',
    'Debugging dan Profiling',
    'Optimasi Kode',
    'Git dan Version Control',
    'Docker dan Containerisasi',
    'Arsitektur Microservices',
    'Design Pattern',
    'Clean Code',
    'Dokumentasi API',
]

COMMENTS = [
    'Materi ini sangat membantu, terima kasih!',
    'Apakah ada referensi tambahan untuk topik ini?',
    'Saya belum paham bagian ini, bisa dijelaskan lagi?',
    'Keren sekali materinya, langsung saya coba praktikkan.',
    'Tugas ini cukup menantang tapi sangat bermanfaat!',
    'Mohon bantuannya untuk soal ini, sudah dicoba tapi masih bingung.',
    'Sudah dicoba tapi masih error, kira-kira kenapa ya?',
    'Terima kasih penjelasannya, sekarang sudah lebih jelas.',
    'Apakah boleh menggunakan library lain selain yang disebutkan?',
    'Saya setuju dengan pendapat teman di atas.',
    'Kapan deadline pengumpulan tugasnya?',
    'Boleh minta contoh kode yang sudah selesai sebagai referensi?',
    'Bagian ini yang paling susah menurut saya, perlu penjelasan lebih.',
    'Alhamdulillah, sudah berhasil mengerjakan!',
    'Materinya sangat relevan dengan kebutuhan industri saat ini.',
    'Apakah ada video penjelasan tambahan untuk materi ini?',
    'Terima kasih atas feedback-nya, sangat membantu perbaikan.',
    'Sudah saya coba ulang dan berhasil, terima kasih!',
    'Materinya padat dan informatif, suka sekali gaya penjelasannya.',
    'Ada yang bisa bantu explain perbedaannya dengan konsep sebelumnya?',
]

PRICES = [50000, 75000, 100000, 125000, 150000, 200000, 250000]


class Command(BaseCommand):
    help = 'Seed database dengan data dummy untuk Lab 05 Optimasi Database'

    def handle(self, *args, **options):
        # Seed random agar hasil konsisten setiap kali dijalankan
        random.seed(42)

        self.stdout.write(self.style.HTTP_INFO('=' * 55))
        self.stdout.write(self.style.HTTP_INFO('  Seeding Data - Lab 05: Optimasi Database'))
        self.stdout.write(self.style.HTTP_INFO('=' * 55))

        teachers = self._seed_teachers()
        students = self._seed_students()
        courses = self._seed_courses(teachers)
        members = self._seed_members(courses, students)
        contents = self._seed_contents(courses)
        self._seed_comments(contents, members)

        self._print_summary()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Seeding selesai! Sekarang coba:'))
        self.stdout.write('  http://localhost:8000/courses/          ← amati query di Silk')
        self.stdout.write('  http://localhost:8000/silk/             ← dashboard profiling')
        self.stdout.write('  http://localhost:8000/admin/            ← manajemen data')

    # -------------------------------------------------------------------------
    # Step 1: Buat 20 User pengajar
    # -------------------------------------------------------------------------
    def _seed_teachers(self):
        self.stdout.write('\n[1/6] Membuat pengajar (dosen01 - dosen20)...')

        existing = set(
            User.objects.filter(username__startswith='dosen')
            .values_list('username', flat=True)
        )

        to_create = []
        for i in range(1, 21):
            username = f'dosen{i:02d}'
            if username not in existing:
                fname = FIRST_NAMES[(i - 1) % len(FIRST_NAMES)]
                lname = LAST_NAMES[(i - 1) % len(LAST_NAMES)]
                to_create.append(User(
                    username=username,
                    first_name=fname,
                    last_name=lname,
                    email=f'{username}@univ.ac.id',
                    is_staff=False,
                    # make_password() diperlukan karena bulk_create tidak memanggil
                    # set_password() → password harus di-hash sebelum bulk_create
                    password=make_password('password123'),
                ))

        if to_create:
            User.objects.bulk_create(to_create, ignore_conflicts=True)

        teachers = list(User.objects.filter(username__startswith='dosen'))
        self.stdout.write(f'  → {len(teachers)} pengajar tersedia')
        return teachers

    # -------------------------------------------------------------------------
    # Step 2: Buat 80 User mahasiswa
    # -------------------------------------------------------------------------
    def _seed_students(self):
        self.stdout.write('\n[2/6] Membuat mahasiswa (mhs001 - mhs080)...')

        existing = set(
            User.objects.filter(username__startswith='mhs')
            .values_list('username', flat=True)
        )

        to_create = []
        for i in range(1, 81):
            username = f'mhs{i:03d}'
            if username not in existing:
                to_create.append(User(
                    username=username,
                    first_name=random.choice(FIRST_NAMES),
                    last_name=random.choice(LAST_NAMES),
                    email=f'{username}@student.univ.ac.id',
                    password=make_password('password123'),
                ))

        if to_create:
            User.objects.bulk_create(to_create, ignore_conflicts=True)

        students = list(User.objects.filter(username__startswith='mhs'))
        self.stdout.write(f'  → {len(students)} mahasiswa tersedia')
        return students

    # -------------------------------------------------------------------------
    # Step 3: Buat 100 Course
    # -------------------------------------------------------------------------
    def _seed_courses(self, teachers):
        self.stdout.write('\n[3/6] Membuat 100 mata kuliah...')

        existing_count = Course.objects.count()
        to_create = []

        for i in range(existing_count, 100):
            subject = SUBJECTS[i % len(SUBJECTS)]
            # Jika subject sudah dipakai, tambahkan kelas (A, B, C, ...)
            kelas_idx = i // len(SUBJECTS)
            name = subject if kelas_idx == 0 else f'{subject} - Kelas {chr(65 + kelas_idx - 1)}'
            to_create.append(Course(
                name=name,
                description=(
                    f'Mata kuliah {subject} membahas konsep dasar hingga lanjutan '
                    f'dengan pendekatan teori dan praktikum. Mahasiswa akan mampu '
                    f'menerapkan ilmu ini di dunia kerja.'
                ),
                price=random.choice(PRICES),
                teacher=random.choice(teachers),
            ))

        if to_create:
            Course.objects.bulk_create(to_create, batch_size=500)

        courses = list(Course.objects.all()[:100])
        self.stdout.write(f'  → {Course.objects.count()} mata kuliah tersedia')
        return courses

    # -------------------------------------------------------------------------
    # Step 4: Buat 500 CourseMember
    # -------------------------------------------------------------------------
    def _seed_members(self, courses, students):
        self.stdout.write('\n[4/6] Membuat 500 anggota kelas...')

        existing_count = CourseMember.objects.count()
        # Buat set pasangan (course_id, user_id) yang sudah ada untuk cek duplikat
        existing_pairs = set(
            CourseMember.objects.values_list('course_id_id', 'user_id_id')
        )

        to_create = []
        attempts = 0
        target = 500 - existing_count

        while len(to_create) < target and attempts < 10000:
            attempts += 1
            course = random.choice(courses)
            student = random.choice(students)
            pair = (course.id, student.id)

            if pair not in existing_pairs:
                existing_pairs.add(pair)
                role = 'ast' if random.random() < 0.1 else 'std'  # 10% asisten
                to_create.append(CourseMember(
                    course_id=course,
                    user_id=student,
                    roles=role,
                ))

        if to_create:
            CourseMember.objects.bulk_create(to_create, batch_size=500, ignore_conflicts=True)

        members = list(CourseMember.objects.all())
        self.stdout.write(f'  → {CourseMember.objects.count()} anggota kelas tersedia')
        return members

    # -------------------------------------------------------------------------
    # Step 5: Buat 300 CourseContent
    # -------------------------------------------------------------------------
    def _seed_contents(self, courses):
        self.stdout.write('\n[5/6] Membuat 300 konten kelas...')

        existing_count = CourseContent.objects.count()
        to_create = []

        for i in range(existing_count, 300):
            course = courses[i % len(courses)]
            prefix = CONTENT_PREFIXES[i % len(CONTENT_PREFIXES)]
            topic = random.choice(CONTENT_TOPICS)
            to_create.append(CourseContent(
                name=f'{prefix} {topic}',
                description=(
                    f'Materi {prefix.lower()} mengenai {topic.lower()} '
                    f'dalam konteks {course.name}. '
                    f'Pelajari konsep ini dengan seksama sebelum mengerjakan latihan.'
                ),
                course_id=course,
                parent_id=None,  # Top-level content (tanpa induk)
            ))

        if to_create:
            CourseContent.objects.bulk_create(to_create, batch_size=500)

        contents = list(CourseContent.objects.all()[:300])
        self.stdout.write(f'  → {CourseContent.objects.count()} konten tersedia')
        return contents

    # -------------------------------------------------------------------------
    # Step 6: Buat 1000+ Comment
    # -------------------------------------------------------------------------
    def _seed_comments(self, contents, members):
        self.stdout.write('\n[6/6] Membuat 1000+ komentar...')

        existing_count = Comment.objects.count()
        target = 1000 - existing_count

        if target <= 0:
            self.stdout.write(f'  → {Comment.objects.count()} komentar tersedia (skip)')
            return

        # Pre-build dict: course_id → list of members untuk efisiensi
        # Ini menghindari query per komentar saat mencari member yang sesuai
        members_by_course = {}
        for member in members:
            cid = member.course_id_id
            if cid not in members_by_course:
                members_by_course[cid] = []
            members_by_course[cid].append(member)

        to_create = []
        fallback_members = members[:20]  # Fallback jika course tidak punya member

        for _ in range(target):
            content = random.choice(contents)
            course_members = members_by_course.get(content.course_id_id, fallback_members)
            member = random.choice(course_members)
            to_create.append(Comment(
                content_id=content,
                member_id=member,
                comment=random.choice(COMMENTS),
            ))

        Comment.objects.bulk_create(to_create, batch_size=500)
        self.stdout.write(f'  → {Comment.objects.count()} komentar tersedia')

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    def _print_summary(self):
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('-' * 55))
        self.stdout.write(self.style.HTTP_INFO('  Ringkasan Data'))
        self.stdout.write(self.style.HTTP_INFO('-' * 55))
        self.stdout.write(
            f"  User pengajar   : {User.objects.filter(username__startswith='dosen').count()}"
        )
        self.stdout.write(
            f"  User mahasiswa  : {User.objects.filter(username__startswith='mhs').count()}"
        )
        self.stdout.write(f'  Course          : {Course.objects.count()}')
        self.stdout.write(f'  CourseMember    : {CourseMember.objects.count()}')
        self.stdout.write(f'  CourseContent   : {CourseContent.objects.count()}')
        self.stdout.write(f'  Comment         : {Comment.objects.count()}')
        self.stdout.write(self.style.HTTP_INFO('-' * 55))
