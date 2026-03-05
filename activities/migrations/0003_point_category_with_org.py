"""
Migration: 0003_point_category_with_org

Squashes previous migrations 0003/0004/0005.
Changes:
  - Creates PointCategory model with organization FK (scoped per-org, unique by org+code)
  - Adds Activity.point_category FK
  - Adds Activity.points field
  - Adds Activity.max_participants field
  - Updates ActivityRegistration.status choices (adds POINT_AWARDED)
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0002_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        # 1. Create PointCategory scoped to Organization
        migrations.CreateModel(
            name='PointCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('organization', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='point_categories',
                    to='core.organization',
                )),
                ('name', models.CharField(max_length=255)),
                ('code', models.CharField(max_length=50)),
                ('description', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Mục điểm rèn luyện',
                'verbose_name_plural': 'Mục điểm rèn luyện',
                'db_table': 'point_categories',
                'ordering': ['organization', 'code'],
            },
        ),
        # 2. Unique constraint: org + code must be unique together
        migrations.AddConstraint(
            model_name='pointcategory',
            constraint=models.UniqueConstraint(
                fields=['organization', 'code'],
                name='unique_org_point_category',
            ),
        ),
        # 3. Add FK to Activity
        migrations.AddField(
            model_name='activity',
            name='point_category',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='activities',
                to='activities.pointcategory',
            ),
        ),
        # 4. Add Activity.points
        migrations.AddField(
            model_name='activity',
            name='points',
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text='Số điểm rèn luyện nhận được khi hoàn thành hoạt động',
                max_digits=5,
            ),
        ),
        # 5. Add Activity.max_participants
        migrations.AddField(
            model_name='activity',
            name='max_participants',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text='Giới hạn số lượng sinh viên đăng ký. Để trống nếu không giới hạn.',
            ),
        ),
        # 6. Update ActivityRegistration.status choices (add POINT_AWARDED)
        migrations.AlterField(
            model_name='activityregistration',
            name='status',
            field=models.CharField(
                choices=[
                    ('REGISTERED', 'Đã đăng ký'),
                    ('CANCELED', 'Đã hủy'),
                    ('BANNED', 'Bị cấm'),
                    ('ATTENDED', 'Đã tham gia'),
                    ('POINT_AWARDED', 'Đã cộng điểm'),
                ],
                default='REGISTERED',
                max_length=20,
            ),
        ),
    ]
