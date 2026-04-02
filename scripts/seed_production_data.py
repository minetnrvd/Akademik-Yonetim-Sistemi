"""
Seed Scripti — Üretim benzeri demo verisi
==========================================
1. @example.com kullanıcılarını ve bağlı tüm verileri siler
2. 100 öğretmen + 350 öğrenci oluşturur (gerçek Türk isimleri)
3. Her öğretmene 2-4 ders atar; her öğrenciyi 2-4 derse kaydeder

Çalıştırma:
    .venv\Scripts\python.exe scripts/seed_production_data.py
"""

import sys
import random
import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app import app, db
from models import (
    User, Student, Class,
    AttendanceSession, AttendanceRecord,
    student_classes,
    PermissionAuditLog, AdminOperationLog,
    Announcement, Message,
    Course, CourseEnrollment, GradeRecord,
    StudentCalendarEvent,
)
from werkzeug.security import generate_password_hash

# -------------------------------------------------------------------
# İSİM HAVUZLARI
# -------------------------------------------------------------------
ERKEK_ISIMLER = [
    "Ahmet", "Mehmet", "Mustafa", "Ali", "Hüseyin", "Hasan", "İbrahim",
    "Ömer", "Yusuf", "Murat", "Emre", "Burak", "Can", "Kerem", "Berk",
    "Serkan", "Onur", "Tolga", "Tunç", "Umut", "Furkan", "Enes", "Kaan",
    "Oğuz", "Barış", "Erdem", "Çağrı", "Alp", "Cem", "Doğan",
    "Selim", "Fatih", "Tarık", "Recep", "Caner", "Alper", "Volkan",
    "Gökhan", "Serhat", "Taner", "Rıdvan", "Kadir", "Ferhat", "Soner",
    "Bahadır", "Orhan", "Sinan", "Koray", "Erdal", "Levent",
]

KADIN_ISIMLER = [
    "Fatma", "Ayşe", "Emine", "Hatice", "Zeynep", "Elif", "Merve",
    "Büşra", "Esra", "Selin", "Melis", "İrem", "Deniz", "Cansu",
    "Gizem", "Tuğçe", "Pınar", "Özge", "Serap", "Sibel",
    "Aslı", "Şeyma", "Yasemin", "Neslihan", "Gamze", "Hande",
    "Dilek", "Filiz", "Betül", "Songül", "Beril", "Damla",
    "Cemre", "Ece", "Arzu", "Güneş", "Lale", "Meral",
    "Nurgül", "Özlem", "Reyhan", "Semra", "Tülay", "Ülkü",
    "Vildan", "Asena", "Bahar", "Ceyda", "Derya", "Ebru",
]

SOYADLAR = [
    "Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Doğan", "Kılıç",
    "Arslan", "Taş", "Aydın", "Yıldız", "Özdemir", "Kaplan", "Çetin",
    "Yıldırım", "Kurt", "Özkan", "Şimşek", "Çakır", "Öztürk",
    "Güneş", "Polat", "Kara", "Koç", "Aslan", "Erdoğan", "Tekin",
    "Aktaş", "Bulut", "Korkmaz", "Acar", "Aksoy", "Ateş", "Avcı",
    "Güler", "Güven", "Işık", "Karahan", "Keskin", "Mutlu",
    "Özer", "Pekcan", "Sönmez", "Topal", "Uzun", "Vatansever",
    "Yalçın", "Zengin", "Durmuş", "Ercan", "Erbaş", "Karakoç",
    "Sarı", "Turan", "Uçar", "Uysal", "Başaran", "Ceylan",
    "Dinçer", "Erdem", "Gürbüz", "Hacıoğlu", "Karadağ", "Köse",
]

BOLUMLER = [
    "Bilgisayar Mühendisliği",
    "Elektrik-Elektronik Mühendisliği",
    "Makine Mühendisliği",
    "İşletme",
    "Uluslararası İlişkiler",
    "Hukuk",
    "Psikoloji",
    "Mimarlık",
    "Tıp",
    "Eczacılık",
]

DERSLER = [
    # Bilgisayar
    ("Algoritma ve Programlama I", "BM101"),
    ("Algoritma ve Programlama II", "BM102"),
    ("Veri Yapıları", "BM201"),
    ("Nesne Yönelimli Programlama", "BM202"),
    ("İşletim Sistemleri", "BM301"),
    ("Veritabanı Yönetim Sistemleri", "BM302"),
    ("Bilgisayar Ağları", "BM303"),
    ("Yazılım Mühendisliği", "BM401"),
    ("Yapay Zeka", "BM402"),
    ("Siber Güvenlik", "BM403"),
    ("Yazılım Test ve Kalite", "BM404"),
    ("Mobil Uygulama Geliştirme", "BM411"),
    # Elektrik
    ("Devre Analizi", "EE101"),
    ("Elektromanyetik Alan Teorisi", "EE201"),
    ("Sinyal ve Sistemler", "EE301"),
    ("Güç Sistemleri", "EE401"),
    # Makine
    ("Termodinamik", "ME201"),
    ("Akışkanlar Mekaniği", "ME301"),
    ("Mukavemet", "ME302"),
    # İşletme
    ("Genel Muhasebe", "MAN101"),
    ("Pazarlama Yönetimi", "MAN201"),
    ("Finansal Yönetim", "MAN301"),
    ("Stratejik Yönetim", "MAN401"),
    ("Girişimcilik", "MAN402"),
    # Uluslararası İlişkiler
    ("Uluslararası İlişkilere Giriş", "IR101"),
    ("Uluslararası Hukuk", "IR201"),
    ("Dış Politika Analizi", "IR301"),
    # Hukuk
    ("Medeni Hukuk", "LAW101"),
    ("Ceza Hukuku", "LAW201"),
    ("Anayasa Hukuku", "LAW301"),
    # Psikoloji
    ("Genel Psikoloji", "PSY101"),
    ("Gelişim Psikolojisi", "PSY201"),
    ("Klinik Psikoloji", "PSY301"),
    # Ortak
    ("İngilizce I", "ENG101"),
    ("İngilizce II", "ENG102"),
    ("Matematik I", "MAT101"),
    ("Matematik II", "MAT102"),
    ("Fizik I", "FIZ101"),
    ("Türk Dili ve Edebiyatı", "TDL101"),
    ("Atatürk İlkeleri ve İnkılap Tarihi", "ATA101"),
]

SEHIRLER = [
    "İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana",
    "Konya", "Gaziantep", "Kayseri", "Mersin", "Lefkoşa", "Girne",
    "Gazimağusa", "Lefke", "Trabzon", "Samsun", "Eskişehir", "Diyarbakır",
]


# -------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# -------------------------------------------------------------------
_used_emails: set[str] = set()
_used_student_numbers: set[str] = set()


def _slug(text: str) -> str:
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")
    return text.translate(tr_map).lower().replace(" ", ".")


def _unique_email(first: str, last: str, domain: str = "kyrenia.edu.tr") -> str:
    base = f"{_slug(first)}.{_slug(last)}"
    email = f"{base}@{domain}"
    counter = 1
    while email in _used_emails:
        email = f"{base}{counter}@{domain}"
        counter += 1
    _used_emails.add(email)
    return email


def _unique_student_number(year: int) -> str:
    while True:
        num = f"K{year}{random.randint(10000, 99999)}"
        if num not in _used_student_numbers:
            _used_student_numbers.add(num)
            return num


def _random_name(gender: str) -> tuple[str, str]:
    first = random.choice(ERKEK_ISIMLER if gender == "E" else KADIN_ISIMLER)
    last = random.choice(SOYADLAR)
    return first, last


def _random_date(start_year: int, end_year: int) -> datetime.date:
    y = random.randint(start_year, end_year)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    return datetime.date(y, m, d)


# -------------------------------------------------------------------
# SİLME
# -------------------------------------------------------------------
def purge_test_data():
    print("→ Test verileri siliniyor (@example.com)…")

    test_users = User.query.filter(User.email.like('%@example.com')).all()
    if not test_users:
        print("  Silinecek test kullanıcısı yok.")
        return

    test_ids = [u.id for u in test_users]
    test_student_ids = [s.id for s in Student.query.filter(Student.id.in_(test_ids)).all()]
    test_teacher_ids = [u.id for u in test_users if u.role == 'teacher']

    # 1. Öğrenci takvim etkinlikleri
    if test_student_ids:
        StudentCalendarEvent.query.filter(
            StudentCalendarEvent.student_id.in_(test_student_ids)
        ).delete(synchronize_session=False)

    # 2. GradeRecord → CourseEnrollment (öğrenci)
    if test_student_ids:
        enroll_ids = [
            e.id for e in CourseEnrollment.query.filter(
                CourseEnrollment.student_id.in_(test_student_ids)
            ).all()
        ]
        if enroll_ids:
            GradeRecord.query.filter(
                GradeRecord.enrollment_id.in_(enroll_ids)
            ).delete(synchronize_session=False)
        CourseEnrollment.query.filter(
            CourseEnrollment.student_id.in_(test_student_ids)
        ).delete(synchronize_session=False)

    # 3. AttendanceRecord (öğrenci)
    if test_student_ids:
        AttendanceRecord.query.filter(
            AttendanceRecord.student_id.in_(test_student_ids)
        ).delete(synchronize_session=False)

    # 4. student_classes (öğrenci)
    if test_student_ids:
        db.session.execute(
            student_classes.delete().where(
                student_classes.c.student_id.in_(test_student_ids)
            )
        )

    # 5. Student profilleri
    if test_student_ids:
        Student.query.filter(
            Student.id.in_(test_student_ids)
        ).delete(synchronize_session=False)

    # 6. Öğretmenlerin derslerinin oturum + kayıtları (Class tablosu)
    if test_teacher_ids:
        teacher_class_ids = [
            c.id for c in Class.query.filter(
                Class.teacher_id.in_(test_teacher_ids)
            ).all()
        ]
        if teacher_class_ids:
            sess_ids = [
                s.id for s in AttendanceSession.query.filter(
                    AttendanceSession.class_id.in_(teacher_class_ids)
                ).all()
            ]
            if sess_ids:
                AttendanceRecord.query.filter(
                    AttendanceRecord.session_id.in_(sess_ids)
                ).delete(synchronize_session=False)
                AttendanceSession.query.filter(
                    AttendanceSession.id.in_(sess_ids)
                ).delete(synchronize_session=False)
            db.session.execute(
                student_classes.delete().where(
                    student_classes.c.class_id.in_(teacher_class_ids)
                )
            )
            Class.query.filter(
                Class.id.in_(teacher_class_ids)
            ).delete(synchronize_session=False)

    # 7. Akademik portal dersler (Course tablosu) — öğretmenlerin
    if test_teacher_ids:
        course_ids = [
            c.id for c in Course.query.filter(
                Course.teacher_id.in_(test_teacher_ids)
            ).all()
        ]
        if course_ids:
            enroll_ids2 = [
                e.id for e in CourseEnrollment.query.filter(
                    CourseEnrollment.course_id.in_(course_ids)
                ).all()
            ]
            if enroll_ids2:
                GradeRecord.query.filter(
                    GradeRecord.enrollment_id.in_(enroll_ids2)
                ).delete(synchronize_session=False)
                CourseEnrollment.query.filter(
                    CourseEnrollment.course_id.in_(course_ids)
                ).delete(synchronize_session=False)
            Announcement.query.filter(
                Announcement.course_id.in_(course_ids)
            ).delete(synchronize_session=False)
            Course.query.filter(
                Course.id.in_(course_ids)
            ).delete(synchronize_session=False)

    # 8. Mesajlar
    Message.query.filter(
        (Message.sender_id.in_(test_ids)) | (Message.recipient_id.in_(test_ids))
    ).delete(synchronize_session=False)

    # 9. Duyurular
    Announcement.query.filter(
        Announcement.author_id.in_(test_ids)
    ).delete(synchronize_session=False)

    # 10. PermissionAuditLog
    PermissionAuditLog.query.filter(
        PermissionAuditLog.user_id.in_(test_ids)
    ).delete(synchronize_session=False)

    # 11. AdminOperationLog
    AdminOperationLog.query.filter(
        (AdminOperationLog.actor_user_id.in_(test_ids)) |
        (AdminOperationLog.target_user_id.in_(test_ids))
    ).delete(synchronize_session=False)

    # 12. User kayıtları
    User.query.filter(User.email.like('%@example.com')).delete(
        synchronize_session=False
    )

    db.session.commit()
    print(f"  {len(test_ids)} test kullanıcısı silindi.")


# -------------------------------------------------------------------
# OLUŞTURMA
# -------------------------------------------------------------------
def create_teachers(n: int = 100) -> list[User]:
    print(f"→ {n} öğretmen oluşturuluyor…")
    titles = [
        "Prof. Dr.", "Doç. Dr.", "Dr. Öğr. Üyesi",
        "Öğr. Gör.", "Arş. Gör. Dr.", "",
    ]
    title_weights = [15, 20, 25, 20, 10, 10]
    teachers = []
    password_hash = generate_password_hash("Ogretmen.123")

    for i in range(n):
        gender = random.choice(["E", "K"])
        first, last = _random_name(gender)
        title = random.choices(titles, weights=title_weights, k=1)[0]
        display_name = f"{title} {first} {last}".strip() if title else f"{first} {last}"
        email = _unique_email(first, last, "kyrenia.edu.tr")

        user = User(
            name=display_name,
            email=email,
            password_hash=password_hash,
            role="teacher",
            is_locked=False,
        )
        db.session.add(user)
        teachers.append(user)

        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{n} öğretmen eklendi…")

    db.session.flush()
    print(f"  ✓ {n} öğretmen oluşturuldu.")
    return teachers


def create_classes(teachers: list[User]) -> list[Class]:
    print("→ Dersler oluşturuluyor…")
    classes = []
    shuffled_courses = DERSLER.copy()
    random.shuffle(shuffled_courses)

    for idx, teacher in enumerate(teachers):
        # Her öğretmene 2-4 ders
        num_classes = random.randint(2, 4)
        for j in range(num_classes):
            course_idx = (idx * 4 + j) % len(shuffled_courses)
            course_name, course_code = shuffled_courses[course_idx]
            section = random.randint(1, 4)
            klass = Class(
                name=f"{course_name} ({course_code}-{section:02d})",
                teacher_id=teacher.id,
            )
            db.session.add(klass)
            classes.append(klass)

    db.session.flush()
    print(f"  ✓ {len(classes)} ders oluşturuldu.")
    return classes


def create_students(n: int = 350, classes: list[Class] = None) -> list[User]:
    print(f"→ {n} öğrenci oluşturuluyor…")
    password_hash = generate_password_hash("Ogrenci.123")
    students = []
    current_year = 2026

    for i in range(n):
        gender = random.choice(["E", "K"])
        first, last = _random_name(gender)
        email = _unique_email(first, last, "std.kyrenia.edu.tr")
        entry_year = random.randint(2020, 2025)
        student_number = _unique_student_number(entry_year)

        user = User(
            name=f"{first} {last}",
            email=email,
            password_hash=password_hash,
            role="student",
            is_locked=False,
        )
        db.session.add(user)
        db.session.flush()

        bolum = random.choice(BOLUMLER)
        term_num = (current_year - entry_year) * 2 + random.randint(1, 2)
        term_num = max(1, min(term_num, 8))

        profile = Student(
            id=user.id,
            student_number=student_number,
            first_name=first,
            last_name=last,
            gender="Erkek" if gender == "E" else "Kadın",
            birth_date=_random_date(1998, 2005),
            birth_place=random.choice(SEHIRLER),
            nationality="T.C.",
            registered_city=random.choice(SEHIRLER),
            university_academic_year=f"{entry_year}-{entry_year+1}",
            university_term=f"{term_num}. Dönem",
            university_faculty="Mühendislik ve Doğa Bilimleri Fakültesi"
                if "Mühendisliği" in bolum else "Sosyal Bilimler Fakültesi",
            university_department=bolum,
            university_scholarship_type=random.choice([
                "%100 Burslu", "%50 Burslu", "Ücretli", "Kısmi Burslu"
            ]),
        )
        db.session.add(profile)
        students.append(user)

        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{n} öğrenci eklendi…")

    db.session.flush()
    print(f"  ✓ {n} öğrenci oluşturuldu.")

    # Öğrencileri derslere kaydet
    if classes:
        print("→ Öğrenciler derslere kaydediliyor…")
        for user in students:
            num_classes = random.randint(2, 5)
            chosen = random.sample(classes, min(num_classes, len(classes)))
            student_profile = Student.query.get(user.id)
            if student_profile:
                for klass in chosen:
                    student_profile.classes.append(klass)
        print("  ✓ Kayıtlar tamamlandı.")

    return students


# -------------------------------------------------------------------
# ANA AKIŞ
# -------------------------------------------------------------------
def main():
    with app.app_context():
        # Korunan kullanıcıları göster
        real_users = User.query.filter(~User.email.like('%@example.com')).all()
        print("Korunan gerçek kullanıcılar:")
        for u in real_users:
            print(f"  [{u.role}] {u.email} — {u.name}")
        print()

        onay = input("Test verilerini sil ve 100 öğretmen + 350 öğrenci oluştur? (evet/hayır): ").strip().lower()
        if onay != "evet":
            print("İptal edildi.")
            return

        purge_test_data()
        teachers = create_teachers(100)
        classes = create_classes(teachers)
        create_students(350, classes)

        db.session.commit()

        # Özet
        print()
        print("=" * 50)
        print("ÖZET")
        print(f"  Öğretmen : {User.query.filter_by(role='teacher').count()}")
        print(f"  Öğrenci  : {User.query.filter_by(role='student').count()}")
        print(f"  Admin    : {User.query.filter_by(role='admin').count()}")
        print(f"  Ders     : {Class.query.count()}")
        print("=" * 50)
        print("Tüm öğretmen şifresi : Ogretmen.123")
        print("Tüm öğrenci şifresi  : Ogrenci.123")


if __name__ == "__main__":
    main()
