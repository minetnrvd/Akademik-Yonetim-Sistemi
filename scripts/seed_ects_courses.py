"""Set national credit (kredi) and ECTS (AKTS) on courses and add sample catalogue courses for term registration.

Idempotent: existing sample courses are updated, not duplicated.
Usage: python scripts/seed_ects_courses.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402
from models import Course, User, db  # noqa: E402

# (credit, ECTS) of the existing class-linked courses, matched by the course code at the start of the title.
EXISTING = {'CMP242': (3, 7), 'CMP246': (3, 7), 'CMP301': (4, 8), 'MAT201': (3, 6)}

# code, title, credit, ECTS, schedule slot (no clash with the existing Mon/Tue/Wed slots)
SAMPLE_COURSES = [
    ('CMP211', 'Veri Yapıları ve Algoritmalar', 4, 8, 'Mon-13:00-16:00'),
    ('CMP232', 'Nesne Yönelimli Programlama', 3, 7, 'Tue-13:00-16:00'),
    ('CMP263', 'Bilgisayar Ağları', 3, 7, 'Thu-09:00-12:00'),
    ('CMP351', 'Yazılım Mühendisliği', 3, 7, 'Thu-13:00-16:00'),
    ('CMP382', 'Yapay Zekâya Giriş', 4, 8, 'Fri-09:00-12:00'),
    ('MAT221', 'Olasılık ve İstatistik', 3, 6, 'Fri-13:00-15:00'),
    ('CMP315', 'İşletim Sistemleri', 3, 7, 'Wed-09:00-12:00'),
    ('ENG201', 'Akademik İngilizce', 3, 5, 'Tue-16:00-18:00'),
]


def main():
    with app.app_context():
        teachers = User.query.filter_by(role='teacher').order_by(User.id.asc()).all()
        if not teachers:
            print('No teacher found; create one first.')
            return

        updated = 0
        for course in Course.query.all():
            values = EXISTING.get((course.title or '').split(' ')[0])
            if values and (course.credit, course.ects) != values:
                course.credit, course.ects = values
                updated += 1

        added = 0
        for index, (code, title, credit, ects, slot) in enumerate(SAMPLE_COURSES):
            course = Course.query.filter_by(code=code).first()
            if course is None:
                course = Course(code=code, teacher_id=teachers[index % len(teachers)].id, capacity=60)
                db.session.add(course)
                added += 1
            course.title, course.credit, course.ects, course.schedule_slot = f'{code} {title}', credit, ects, slot

        db.session.commit()
        print(f'Credit/ECTS updated on {updated} course(s); {added} sample course(s) added.')


if __name__ == '__main__':
    main()
