import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='nama matkul')),
                ('description', models.TextField(default='-', verbose_name='deskripsi')),
                ('price', models.IntegerField(default=10000, verbose_name='harga')),
                ('image', models.ImageField(blank=True, null=True, upload_to='', verbose_name='gambar')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('teacher', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='pengajar',
                )),
            ],
            options={
                'verbose_name': 'Mata Kuliah',
                'verbose_name_plural': 'Mata Kuliah',
            },
        ),
        migrations.CreateModel(
            name='CourseMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('roles', models.CharField(
                    choices=[('std', 'Siswa'), ('ast', 'Asisten')],
                    default='std',
                    max_length=3,
                    verbose_name='peran',
                )),
                ('course_id', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    to='courses.course',
                    verbose_name='matkul',
                )),
                ('user_id', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='siswa',
                )),
            ],
            options={
                'verbose_name': 'Anggota Kelas',
                'verbose_name_plural': 'Anggota Kelas',
            },
        ),
        migrations.CreateModel(
            name='CourseContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='judul konten')),
                ('description', models.TextField(default='-', verbose_name='deskripsi')),
                ('video_url', models.CharField(blank=True, max_length=200, null=True, verbose_name='URL Video')),
                ('file_attachment', models.FileField(blank=True, null=True, upload_to='', verbose_name='File')),
                ('course_id', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    to='courses.course',
                    verbose_name='matkul',
                )),
                ('parent_id', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.RESTRICT,
                    to='courses.coursecontent',
                    verbose_name='induk',
                )),
            ],
            options={
                'verbose_name': 'Konten Kelas',
                'verbose_name_plural': 'Konten Kelas',
            },
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('comment', models.TextField(verbose_name='komentar')),
                ('content_id', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='courses.coursecontent',
                    verbose_name='konten',
                )),
                ('member_id', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='courses.coursemember',
                    verbose_name='pengguna',
                )),
            ],
            options={
                'verbose_name': 'Komentar',
                'verbose_name_plural': 'Komentar',
            },
        ),
    ]
