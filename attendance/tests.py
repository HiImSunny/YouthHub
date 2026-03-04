"""
Tests for the attendance & points system.
Covers Phase 1-4 logic:
  - ActivityPoint model unique constraint
  - _do_award_student helper
  - award_student_points view
  - award_bulk_points view
  - activity_attendance_verify view (matrix query)
"""
import uuid
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from activities.models import Activity, ActivityRegistration, PointCategory
from attendance.models import ActivityPoint, AttendanceRecord, AttendanceSession
from attendance.views import _do_award_student
from core.models import Organization, Semester
from users.models import User


# ─── Fixtures ────────────────────────────────────────────────────────────────

def make_user(username, role='STUDENT', **kwargs):
    return User.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password='testpass123',
        full_name=f'Test {username.capitalize()}',
        role=role,
        **kwargs,
    )


def make_org():
    return Organization.objects.create(
        type=Organization.OrgType.UNION_SCHOOL,
        name='Đoàn Trường Test',
        code=f'ORG-{uuid.uuid4().hex[:6]}',
    )


def make_activity(org, created_by, point_category=None, points=5.0):
    code = f'ACT-{uuid.uuid4().hex[:6]}'
    return Activity.objects.create(
        title=f'Hoạt động {code}',
        code=code,
        activity_type=Activity.ActivityType.VOLUNTEER,
        start_time=timezone.now(),
        end_time=timezone.now() + timezone.timedelta(hours=2),
        location='Hall A',
        status=Activity.ActivityStatus.APPROVED,
        organization=org,
        created_by=created_by,
        point_category=point_category,
        points=Decimal(str(points)),
    )


def make_session(activity, name='Phiên 1'):
    return AttendanceSession.objects.create(
        activity=activity,
        name=name,
        start_time=timezone.now(),
        end_time=timezone.now() + timezone.timedelta(hours=1),
        qr_token=uuid.uuid4().hex,
        status=AttendanceSession.SessionStatus.OPEN,
    )


def make_record(session, student, status='VERIFIED'):
    return AttendanceRecord.objects.create(
        attendance_session=session,
        student=student,
        entered_student_code=student.username,
        status=status,
    )


# ─── Model Tests ─────────────────────────────────────────────────────────────

class ActivityModelTest(TestCase):
    """Test Activity.points field added in Phase 1."""

    def setUp(self):
        self.staff = make_user('staff1', role='STAFF')
        self.org = make_org()

    def test_activity_has_points_field(self):
        """Activity.points defaults to 0."""
        act = make_activity(self.org, self.staff, points=0)
        self.assertEqual(act.points, Decimal('0.00'))

    def test_activity_points_stored_correctly(self):
        """Activity.points stores decimal values accurately."""
        act = make_activity(self.org, self.staff, points=7.5)
        act.refresh_from_db()
        self.assertEqual(act.points, Decimal('7.5'))


class ActivityRegistrationStatusTest(TestCase):
    """Test new RegStatus values added in Phase 1."""

    def test_reg_status_has_attended(self):
        choices = [c[0] for c in ActivityRegistration.RegStatus.choices]
        self.assertIn('ATTENDED', choices)

    def test_reg_status_has_point_awarded(self):
        choices = [c[0] for c in ActivityRegistration.RegStatus.choices]
        self.assertIn('POINT_AWARDED', choices)


class ActivityPointUniqueConstraintTest(TestCase):
    """Test unique (student, activity) constraint — Phase 1 fix."""

    def setUp(self):
        self.staff = make_user('staff2', role='STAFF')
        self.student = make_user('sv001')
        self.org = make_org()
        self.activity = make_activity(self.org, self.staff, points=5)

    def test_cannot_award_same_student_twice(self):
        """Creating 2 ActivityPoint for same (student, activity) raises IntegrityError."""
        from django.db import IntegrityError
        ActivityPoint.objects.create(
            student=self.student,
            activity=self.activity,
            points=5,
            reason='first',
        )
        with self.assertRaises(IntegrityError):
            ActivityPoint.objects.create(
                student=self.student,
                activity=self.activity,
                points=5,
                reason='second',  # different reason, but same student+activity
            )

    def test_get_or_create_is_safe(self):
        """get_or_create should not raise on duplicate."""
        ActivityPoint.objects.create(
            student=self.student,
            activity=self.activity,
            points=5,
            reason='first',
        )
        obj, created = ActivityPoint.objects.get_or_create(
            student=self.student,
            activity=self.activity,
            defaults={'points': 5, 'reason': 'second'},
        )
        self.assertFalse(created)


class AttendanceRecordRedundantFKTest(TestCase):
    """Test AttendanceRecord no longer has direct activity FK — uses property instead."""

    def setUp(self):
        self.staff = make_user('staff3', role='STAFF')
        self.student = make_user('sv002')
        self.org = make_org()
        self.activity = make_activity(self.org, self.staff)
        self.session = make_session(self.activity)

    def test_activity_accessible_via_property(self):
        """record.activity returns correct activity via session."""
        record = make_record(self.session, self.student)
        self.assertEqual(record.activity, self.activity)

    def test_no_direct_activity_fk_in_db(self):
        """AttendanceRecord.activity is a property, not a DB column."""
        field_names = [f.name for f in AttendanceRecord._meta.get_fields()]
        self.assertNotIn('activity_id', field_names)


# ─── _do_award_student Tests ─────────────────────────────────────────────────

class DoAwardStudentTest(TestCase):
    """Unit tests for the _do_award_student helper."""

    def setUp(self):
        self.staff = make_user('staff4', role='STAFF')
        self.student = make_user('sv003')
        self.org = make_org()
        self.cat = PointCategory.objects.create(
            name='Loại C', code='CAT-C-TST'
        )
        self.activity = make_activity(self.org, self.staff, point_category=self.cat, points=5)
        self.session = make_session(self.activity)

    def test_creates_activity_point(self):
        """_do_award_student creates ActivityPoint with correct values."""
        make_record(self.session, self.student, status='PENDING')
        created, _ = _do_award_student(self.student, self.activity, self.staff)
        self.assertTrue(created)

        pt = ActivityPoint.objects.get(student=self.student, activity=self.activity)
        self.assertEqual(pt.points, Decimal('5'))
        self.assertEqual(pt.point_category, self.cat)
        self.assertEqual(pt.awarded_by, self.staff)
        self.assertIsNotNone(pt.awarded_at)

    def test_verifies_pending_records(self):
        """_do_award_student upgrades PENDING records to VERIFIED."""
        rec = make_record(self.session, self.student, status='PENDING')
        _do_award_student(self.student, self.activity, self.staff)
        rec.refresh_from_db()
        self.assertEqual(rec.status, 'VERIFIED')
        self.assertEqual(rec.verified_by, self.staff)
        self.assertIsNotNone(rec.approved_at)

    def test_does_not_double_verify_verified_records(self):
        """Already VERIFIED records are not affected."""
        rec = make_record(self.session, self.student, status='VERIFIED')
        _do_award_student(self.student, self.activity, self.staff)
        rec.refresh_from_db()
        self.assertEqual(rec.status, 'VERIFIED')

    def test_updates_registration_to_point_awarded(self):
        """ActivityRegistration status becomes POINT_AWARDED after award."""
        ActivityRegistration.objects.create(
            activity=self.activity,
            student=self.student,
            status='REGISTERED',
        )
        make_record(self.session, self.student)
        _do_award_student(self.student, self.activity, self.staff)

        reg = ActivityRegistration.objects.get(activity=self.activity, student=self.student)
        self.assertEqual(reg.status, 'POINT_AWARDED')

    def test_idempotent_second_call_returns_false(self):
        """Calling _do_award_student twice is safe — second call returns created=False."""
        make_record(self.session, self.student)
        created1, _ = _do_award_student(self.student, self.activity, self.staff)
        created2, _ = _do_award_student(self.student, self.activity, self.staff)
        self.assertTrue(created1)
        self.assertFalse(created2)
        # Still only 1 point record
        self.assertEqual(ActivityPoint.objects.filter(student=self.student, activity=self.activity).count(), 1)


# ─── View Tests ──────────────────────────────────────────────────────────────

class AwardStudentViewTest(TestCase):
    """Integration tests for award_student_points view."""

    def setUp(self):
        self.client = Client()
        self.staff = make_user('staff5', role='STAFF')
        self.student = make_user('sv004')
        self.org = make_org()
        self.activity = make_activity(self.org, self.staff, points=5)
        self.session = make_session(self.activity)
        make_record(self.session, self.student, status='PENDING')

    def _award_url(self):
        return reverse('attendance:award_student', kwargs={
            'activity_pk': self.activity.pk,
            'student_pk': self.student.pk,
        })

    def test_redirects_student_role(self):
        """Student cannot award points."""
        self.client.login(username='sv004', password='testpass123')
        resp = self.client.post(self._award_url())
        self.assertEqual(resp.status_code, 302)
        # Should redirect away from verify page
        self.assertNotIn('activity_verify', resp['Location'])

    def test_staff_can_award(self):
        """Staff can award points to student."""
        self.client.login(username='staff5', password='testpass123')
        resp = self.client.post(self._award_url())
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            ActivityPoint.objects.filter(student=self.student, activity=self.activity).exists()
        )

    def test_get_request_redirects(self):
        """GET request to award URL redirects (POST only)."""
        self.client.login(username='staff5', password='testpass123')
        resp = self.client.get(self._award_url())
        self.assertEqual(resp.status_code, 302)

    def test_award_twice_is_safe(self):
        """Awarding the same student twice doesn't create duplicate points."""
        self.client.login(username='staff5', password='testpass123')
        self.client.post(self._award_url())
        self.client.post(self._award_url())
        count = ActivityPoint.objects.filter(student=self.student, activity=self.activity).count()
        self.assertEqual(count, 1)


class AwardBulkViewTest(TestCase):
    """Integration tests for award_bulk_points view."""

    def setUp(self):
        self.client = Client()
        self.staff = make_user('staff6', role='STAFF')
        self.org = make_org()
        self.activity = make_activity(self.org, self.staff, points=10)
        self.session1 = make_session(self.activity, 'Phiên 1')
        self.session2 = make_session(self.activity, 'Phiên 2')

        # sv_full: attended both sessions
        self.sv_full = make_user('sv_full')
        make_record(self.session1, self.sv_full, status='VERIFIED')
        make_record(self.session2, self.sv_full, status='VERIFIED')

        # sv_partial: attended only 1 session
        self.sv_partial = make_user('sv_partial')
        make_record(self.session1, self.sv_partial, status='VERIFIED')

    def _bulk_url(self):
        return reverse('attendance:award_bulk', kwargs={'activity_pk': self.activity.pk})

    def test_eligible_only_awards_only_fully_attended(self):
        """eligible_only=1 only awards students who attended all sessions."""
        self.client.login(username='staff6', password='testpass123')
        self.client.post(self._bulk_url(), {'eligible_only': '1'})

        self.assertTrue(
            ActivityPoint.objects.filter(student=self.sv_full, activity=self.activity).exists()
        )
        self.assertFalse(
            ActivityPoint.objects.filter(student=self.sv_partial, activity=self.activity).exists()
        )

    def test_bulk_without_eligible_only_awards_all(self):
        """Without eligible_only, awards all students who checked in at least once."""
        self.client.login(username='staff6', password='testpass123')
        self.client.post(self._bulk_url(), {})

        self.assertTrue(
            ActivityPoint.objects.filter(student=self.sv_full, activity=self.activity).exists()
        )
        self.assertTrue(
            ActivityPoint.objects.filter(student=self.sv_partial, activity=self.activity).exists()
        )

    def test_bulk_idempotent(self):
        """Running bulk award twice doesn't duplicate points."""
        self.client.login(username='staff6', password='testpass123')
        self.client.post(self._bulk_url(), {})
        self.client.post(self._bulk_url(), {})

        count = ActivityPoint.objects.filter(activity=self.activity).count()
        # sv_full + sv_partial = 2, run twice still = 2
        self.assertEqual(count, 2)

    def test_student_cannot_bulk_award(self):
        """Student role is rejected."""
        self.client.login(username='sv_full', password='testpass123')
        resp = self.client.post(self._bulk_url(), {})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ActivityPoint.objects.filter(activity=self.activity).count(), 0)


class ActivityVerifyViewTest(TestCase):
    """Integration tests for activity_attendance_verify matrix view."""

    def setUp(self):
        self.client = Client()
        self.staff = make_user('staff7', role='STAFF')
        self.student1 = make_user('sv_a')
        self.student2 = make_user('sv_b')
        self.org = make_org()
        self.activity = make_activity(self.org, self.staff, points=5)
        self.session = make_session(self.activity)
        make_record(self.session, self.student1)

    def _verify_url(self):
        return reverse('attendance:activity_verify', kwargs={'activity_pk': self.activity.pk})

    def test_staff_can_access_verify(self):
        """Staff can access the attendance matrix page."""
        self.client.login(username='staff7', password='testpass123')
        resp = self.client.get(self._verify_url())
        self.assertEqual(resp.status_code, 200)

    def test_student_cannot_access_verify(self):
        """Student is redirected from verify page."""
        self.client.login(username='sv_a', password='testpass123')
        resp = self.client.get(self._verify_url())
        self.assertEqual(resp.status_code, 302)

    def test_matrix_shows_correct_student_count(self):
        """Context includes correct student rows."""
        self.client.login(username='staff7', password='testpass123')
        resp = self.client.get(self._verify_url())
        # Only sv_a checked in
        self.assertEqual(resp.context['total_students'], 1)

    def test_matrix_includes_registered_but_not_checkedin(self):
        """Students who registered but didn't check in appear in matrix."""
        # sv_b registered but has no attendance record
        ActivityRegistration.objects.create(
            activity=self.activity,
            student=self.student2,
            status='REGISTERED',
        )
        self.client.login(username='staff7', password='testpass123')
        resp = self.client.get(self._verify_url())
        # Both sv_a (checked in) and sv_b (registered only) should appear
        self.assertEqual(resp.context['total_students'], 2)

    def test_fully_attended_count(self):
        """fully_attended_count is correct when all sessions are checked."""
        self.client.login(username='staff7', password='testpass123')
        resp = self.client.get(self._verify_url())
        # Activity has 1 session, sv_a checked in → fully attended
        self.assertEqual(resp.context['fully_attended_count'], 1)
