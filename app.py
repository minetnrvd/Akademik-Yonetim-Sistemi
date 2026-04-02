import os
import datetime
import secrets
import socket
import hmac
import time
import re
import logging
import smtplib
import qrcode
import csv
import json
from collections import deque, defaultdict
from io import StringIO
from functools import wraps
from email.message import EmailMessage
from urllib.parse import urlparse, quote
from urllib.request import Request, urlopen
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response, g
from sqlalchemy import text, func
from models import db, User, Student, Class, AttendanceSession, AttendanceRecord, Course, CourseEnrollment, GradeRecord, CourseRegistrationPolicy, CourseEnrollmentAudit, Announcement, StudentCalendarEvent, UserCalendarEvent, PermissionAuditLog, AdminOperationLog


LANGUAGES = ('en', 'tr')
DEFAULT_LANGUAGE = 'en'
MAX_PERMISSION_AUDIT_EVENTS = 500
PERMISSION_AUDIT_EVENTS = deque(maxlen=MAX_PERMISSION_AUDIT_EVENTS)
RATE_LIMIT_EVENTS = {}
REQUEST_METRICS = {
    'since_utc': datetime.datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z'),
    'total_requests': 0,
    'error_4xx': 0,
    'error_5xx': 0,
    'by_endpoint': {},
}

TRANSLATIONS = {
    'en': {
        'language': 'Language',
        'site_title': 'QR Attendance System',
        'english': 'English',
        'turkish': 'Turkish',
        'language_updated': 'Language updated.',
        'skip_to_content': 'Skip to content',
        'login': 'Login',
        'register': 'Register',
        'email': 'Email',
        'password': 'Password',
        'remember_me': 'Remember Me',
        'dont_have_account': "Don't have an account?",
        'already_registered': 'Already registered?',
        'welcome_short': 'Welcome.',
        'student': 'Student',
        'teacher': 'Teacher',
        'name': 'Name',
        'student_number': 'Student Number',
        'student_home': 'Student Home',
        'welcome_user_continue': 'Welcome, {name}. Continue using the cards below.',
        'my_account': 'My Account',
        'logout': 'Logout',
        'announcements': 'Announcements',
        'no_announcements': 'No announcements available.',
        'weather': 'Weather',
        'enter_city': 'Enter city',
        'update': 'Update',
        'use_current_location': 'Use My Current Location',
        'source': 'Source',
        'automatic_location': 'Automatic location',
        'manual_city': 'Manual city',
        'city': 'City',
        'condition': 'Condition',
        'temperature': 'Temperature',
        'humidity': 'Humidity',
        'weather_service_unavailable': 'Weather service is temporarily unavailable.',
        'calendar_and_upcoming': 'Calendar and Upcoming Items',
        'calendar_view': 'Calendar View',
        'previous_month': 'Previous',
        'next_month': 'Next',
        'select_day_prompt': 'Select a day from the calendar.',
        'selected_day': 'Selected Day',
        'no_events_this_day': 'No event for this day.',
        'today': 'Today',
        'events': 'Events',
        'upcoming_counts': 'Upcoming exams: {exams} | Upcoming activities: {activities}',
        'add_item': 'Add Item',
        'title': 'Title',
        'event_type': 'Event Type',
        'exam': 'Exam',
        'activity': 'Activity',
        'event_date': 'Event Date',
        'optional_note': 'Optional note',
        'add_to_calendar': 'Add to Calendar',
        'upcoming_exams_activities': 'Upcoming Exams and Activities',
        'date': 'Date',
        'delete': 'Delete',
        'no_upcoming_item': 'No upcoming item in your calendar.',
        'page_not_found': 'Page Not Found',
        'page_not_found_404': 'Page Not Found (404)',
        'requested_page_not_found': 'The page you requested could not be found.',
        'check_url_or_dashboard': 'Please check the URL or go back to your dashboard.',
        'teacher_dashboard': 'Teacher Dashboard',
        'go_to_login': 'Go to Login',
        'server_error': 'Server Error',
        'something_went_wrong_500': 'Something Went Wrong (500)',
        'unexpected_server_error': 'An unexpected server error occurred.',
        'try_again_moment': 'Please try again in a moment.',
        'attendance_successful': 'Attendance Successful',
        'attendance_recorded': 'Attendance Recorded',
        'class': 'Class',
        'week': 'Week',
        'your_attendance_confirmed': 'Your attendance has been successfully confirmed.',
        'return_to_student_dashboard': 'Return to Student Dashboard',
        'class_details': 'Class Details',
        'students': 'Students',
        'student_name': 'Student Name',
        'full_name': 'Full Name',
        'first_name': 'First Name',
        'last_name': 'Last Name',
        'gender': 'Gender',
        'birth_date': 'Birth Date',
        'birth_place': 'Birth Place',
        'citizenship': 'Citizenship',
        'identity_number': 'Identity Number',
        'nationality': 'Nationality',
        'registered_city': 'Registered City',
        'registered_district': 'Registered District',
        'passport_number': 'Passport Number',
        'active_box': 'Active Box',
        'passport_details': 'Passport Details',
        'issued_date': 'Issue Date',
        'issued_place': 'Issue Place',
        'valid_until': 'Validity Date',
        'active_status_box': 'Active',
        'other_information': 'Other Information',
        'marital_status': 'Marital Status',
        'blood_type': 'Blood Type',
        'veteran_martyr_relative_q': 'Veteran/Martyr Relative?',
        'disabled_q': 'Disabled?',
        'disability_type': 'Disability Type',
        'disability_rate': 'Disability Rate',
        'working_information': 'Working Information',
        'is_employed_q': 'Is Employed?',
        'is_group_company_q': 'Group Company?',
        'company_name': 'Company Name',
        'work_type': 'Work Type',
        'employment_start_date': 'Employment Start Date',
        'student_affairs_edit_note': 'If you want to make changes, please apply to Student Affairs.',
        'expand': 'Expand',
        'collapse': 'Collapse',
        'role_label': 'Role',
        'student_number_label': 'Student Number',
        'attended_sessions': 'Attended Sessions',
        'absences': 'Absences',
        'passed_q': 'Passed?',
        'yes': 'Yes',
        'no': 'No',
        'no_students_in_class': 'No students in this class yet.',
        'back': 'Back',
        'create_class': 'Create Class',


        'create_new_class': 'Create New Class',
        'class_name': 'Class Name',
        'create': 'Create',
        'join_class': 'Join Class',
        'search_class': 'Search class...',
        'join': 'Join',
        'absence_title': 'Absence',
        'absence_subtitle': 'All attendance operations for {name} are managed here.',
        'back_to_home': 'Back to Home',
        'enrolled_courses': 'Enrolled Courses',
        'active_attendance': 'Active Attendance',
        'total_sessions': 'Total Sessions',
        'average_absence': 'Average Absence',
        'search_course': 'Search course...',
        'search': 'Search',
        'course_based_absence': 'Course-Based Absence',
        'total': 'Total',
        'attended': 'Attended',
        'status': 'Status',
        'active': 'Active',
        'attendance_already_marked': 'Attendance already marked',
        'mark_attendance': 'Mark Attendance',
        'no_active_attendance': 'No active attendance',
        'absence_history': 'Absence History',
        'no_enrolled_course_found': 'No enrolled course found.',
        'active_attendance_alerts': 'Active Attendance Alerts',
        'ends': 'Ends',
        'no_active_attendance_alerts': 'No active attendance alerts.',
        'join_course': 'Join Course',
        'no_additional_course': 'No additional course available to join.',
        'my_attendance_history': 'My Attendance History',
        'present': 'Present',
        'absent': 'Absent',
        'no_confirmed_attendance': 'No confirmed attendance sessions for this class yet.',
        'account_settings': 'Account Settings',
        'change_password': 'Change Password',
        'current_password': 'Current Password',
        'new_password': 'New Password',
        'confirm_new_password': 'Confirm New Password',
        'account_deletion': 'Account Deletion',
        'student_delete_account_disabled': 'Account deletion is disabled for students. Your profile and attendance history are kept for record integrity.',
        'delete_account': 'Delete Account',
        'delete_account_warning': 'This action cannot be undone. Enter your password to delete your account.',
        'my_attendance_history_title': 'My Attendance History',
        'attendance_history': 'Attendance History',
        'back_to_dashboard': 'Back to Dashboard',
        'filters': 'Filters',
        'search_week': 'Search week',
        'start': 'Start',
        'end': 'End',
        'filter': 'Filter',
        'clear_filters': 'Clear filters',
        'download_csv': 'Download CSV',
        'summary': 'Summary',
        'detail': 'Detail',
        'no_recorded_attendance': 'No recorded attendance sessions yet.',
        'confirm_delete_attendance_session': 'Are you sure you want to delete this attendance session?',
        'attendance_detail': 'Attendance Detail',
        'absence_pct': 'Absence %',
        'total_classes': 'Total Classes',
        'absence_percent_label': 'Absence (%)',
        'no_students_found_class': 'No students found in this class yet.',
        'qr_code': 'QR Code',
        'token': 'Token',
        'attendance_link': 'Attendance Link',
        'qr_help_text': 'Make sure your phone is on the same network and this app is reachable via this URL.',
        'download': 'Download',
        'print_or_pdf': 'Print / Save as PDF',
        'welcome_teacher': 'Welcome, {name}',
        'start_attendance': 'Start Attendance',
        'week_placeholder': 'Week (e.g. 1)',
        'start_and_open_qr': 'Start and Open QR',
        'create_class_first': 'You need to create a class first.',
        'current_classes_and_qr': 'Current Classes and QR Codes',
        'students_count': 'Students: {count}',
        'session_active': 'Session Active',
        'no_active_session': 'No Active Session',
        'class_qr_code': 'Class QR Code',
        'fullscreen': 'Fullscreen',
        'qr_not_generated': 'QR code has not been generated.',
        'active_attendance_session': 'Active Attendance Session',
        'live_attendance': 'Live Attendance',
        'ends_at': 'Ends At',
        'finish_attendance': 'Finish Attendance',
        'no_active_session_note': 'There is no active attendance session yet. You can create one above using Start Attendance.',
        'you_have_not_created_class': 'You have not created any class yet.',
        'popup_blocked': 'New tab was blocked. Please allow pop-ups.',
        'pass': 'Pass',
        'fail': 'Fail',
        'academic_status': 'Academic Status',
        'active_value': 'Active',
        'program': 'Program',
        'university_undergraduate_program': 'University Undergraduate Program',
        'course_count': 'Course Count',
        'grading_system': 'Grading System',
        'letter_grade_400': 'Letter Grade (4.00)',
        'guardian_full_name': 'Guardian Full Name',
        'relationship': 'Relationship',
        'emergency_phone': 'Emergency Phone',
        'note': 'Note',
        'not_set_yet': 'Not set yet',
        'family_note': 'These fields can be edited via forms in the next step.',
        'document_status': 'Document Status',
        'registration_document': 'Registration Document',
        'student_certificate': 'Student Certificate',
        'documents_note': 'The documents module will be expanded on this screen.',
        'no_uploaded_document': 'No uploaded document yet',
        'pending': 'Pending',
        'can_be_requested': 'Can be requested',
        'phone': 'Phone',
        'address': 'Address',
        'contact_preference': 'Contact Preference',
        'total_debt': 'Total Debt',
        'total_paid': 'Total Paid',
        'current_balance': 'Current Balance',
        'current_account_note': 'The current account module will be detailed here.',
        'last_payment': 'Last Payment',
        'payment_method': 'Payment Method',
        'scheduled_payment': 'Scheduled Payment',
        'payment_note': 'The payment module can be expanded in the next step.',
        'no_record_found': 'No record found',
        'undefined': 'Undefined',
        'none': 'None',
        'current_term': 'Current Term',
        'registered_course_count': 'Registered Course Count',
        'registered_courses': 'Registered Courses',
        'status_label': 'Status',
        'no_registered_course': 'No registered course yet',
        'active_term': 'Active Term',
        'student_label': 'Student',
        'gpa_4': 'GPA (4.00)',
        'weighted_credits': 'Weighted Credits',
        'no_graded_data': 'No graded course data yet.',
        'calculated_from_courses': 'Calculated from {count} graded course(s).',
        'transcript_table_not_initialized': 'Transcript table is not initialized yet.',
        'today': 'Today',
        'upcoming_academic_events': 'Upcoming Academic Events',
        'term_window': 'Term Window',
        'configured_by_admin': 'Configured by administration',
        'academic_calendar_note': 'Academic calendar events will be listed here in detail.',
        'upcoming_exams': 'Upcoming Exams',
        'completed_exams': 'Completed Exams',
        'next_exam_date': 'Next Exam Date',
        'not_scheduled': 'Not scheduled',
        'exam_module_note': 'Exam management module can be expanded in the next step.',
        'already_enrolled_named': "You are already enrolled in '{name}'.",
        'no_class_found_named': "No class found with the name '{name}'.",
        'identity_information': 'Identity Information',
        'identity_information_desc': 'Student identity and core profile details.',
        'education_information': 'Education Information',
        'education_information_desc': 'Department, program, term, and academic status.',
        'education_reset_note': 'This section has been cleared. We will rebuild it from scratch.',
        'university_information': 'University Information',
        'entry_place': 'Entry Place',
        'entry_type': 'Entry Type',
        'academic_year': 'Academic Year',
        'term': 'Term',
        'faculty': 'Faculty',
        'department': 'Department',
        'scholarship_type': 'Scholarship Type',
        'placement_type': 'Placement Type',
        'score_type': 'Score Type',
        'achievement_score': 'Achievement Score',
        'placement_score': 'Placement Score',
        'preference_order': 'Preference Order',
        'highschool_information': 'High School Information',
        'highschool_name': 'High School Name',
        'highschool_info': 'High School Info',
        'highschool_graduation_date': 'Graduation Date',
        'family_information': 'Family Information',
        'family_information_desc': 'Family contact and relative information.',
        'documents': 'Documents',
        'documents_desc': 'Document and certificate operations.',
        'contact': 'Contact',
        'contact_desc': 'Contact preferences and address details.',
        'current_account': 'Current Account',
        'current_account_desc': 'Balance, debt, and receivable summary.',
        'payments': 'Payments',
        'payments_desc': 'Payment history and new payment actions.',
        'absence': 'Absence',
        'absence_desc': 'Complete attendance workflow and absence analysis.',
        'term_courses': 'Term Courses',
        'term_courses_desc': 'Current term course list and load.',
        'transcript': 'Transcript',
        'transcript_desc': 'Grade summary and GPA overview.',
        'academic_calendar': 'Academic Calendar',
        'academic_calendar_desc': 'Important dates and academic events.',
        'exams': 'Exams',
        'exams_desc': 'Upcoming and completed exam information.',
        'modules': 'Modules',
    },
    'tr': {
        'language': 'Dil',
        'site_title': 'QR Yoklama Sistemi',
        'english': 'Ingilizce',
        'turkish': 'Turkce',
        'language_updated': 'Dil guncellendi.',
        'skip_to_content': 'Icerige gec',
        'login': 'Giris',
        'register': 'Kayit Ol',
        'email': 'E-posta',
        'password': 'Sifre',
        'remember_me': 'Beni Hatirla',
        'dont_have_account': 'Hesabin yok mu?',
        'already_registered': 'Zaten kayitli misin?',
        'welcome_short': 'Hos geldin.',
        'student': 'Ogrenci',
        'teacher': 'Ogretmen',
        'name': 'Ad Soyad',
        'student_number': 'Ogrenci Numarasi',
        'student_home': 'Ogrenci Ana Sayfasi',
        'welcome_user_continue': 'Hos geldin, {name}. Asagidaki kartlarla devam edebilirsin.',
        'my_account': 'Hesabim',
        'logout': 'Cikis',
        'announcements': 'Duyurular',
        'no_announcements': 'Henuz duyuru yok.',
        'weather': 'Hava Durumu',
        'enter_city': 'Sehir girin',
        'update': 'Guncelle',
        'use_current_location': 'Mevcut Konumumu Kullan',
        'source': 'Kaynak',
        'automatic_location': 'Otomatik konum',
        'manual_city': 'Manuel sehir',
        'city': 'Sehir',
        'condition': 'Durum',
        'temperature': 'Sicaklik',
        'humidity': 'Nem',
        'weather_service_unavailable': 'Hava durumu servisi su an kullanilamiyor.',
        'calendar_and_upcoming': 'Takvim ve Yaklasan Ogeler',
        'calendar_view': 'Takvim Gorunumu',
        'previous_month': 'Onceki',
        'next_month': 'Sonraki',
        'select_day_prompt': 'Takvimden bir gun secin.',
        'selected_day': 'Secilen Gun',
        'no_events_this_day': 'Bu gun icin etkinlik yok.',
        'today': 'Bugun',
        'events': 'Etkinlikler',
        'upcoming_counts': 'Yaklasan sinav: {exams} | Yaklasan etkinlik: {activities}',
        'add_item': 'Oge Ekle',
        'title': 'Baslik',
        'event_type': 'Etkinlik Turu',
        'exam': 'Sinav',
        'activity': 'Etkinlik',
        'event_date': 'Etkinlik Tarihi',
        'optional_note': 'Istege bagli not',
        'add_to_calendar': 'Takvime Ekle',
        'upcoming_exams_activities': 'Yaklasan Sinavlar ve Etkinlikler',
        'date': 'Tarih',
        'delete': 'Sil',
        'no_upcoming_item': 'Takviminde yaklasan oge yok.',
        'page_not_found': 'Sayfa Bulunamadi',
        'page_not_found_404': 'Sayfa Bulunamadi (404)',
        'requested_page_not_found': 'Istedigin sayfa bulunamadi.',
        'check_url_or_dashboard': 'Lutfen URL adresini kontrol et ya da paneline don.',
        'teacher_dashboard': 'Ogretmen Paneli',
        'go_to_login': 'Giris Sayfasina Git',
        'server_error': 'Sunucu Hatasi',
        'something_went_wrong_500': 'Bir Seyler Ters Gitti (500)',
        'unexpected_server_error': 'Beklenmeyen bir sunucu hatasi olustu.',
        'try_again_moment': 'Lutfen birazdan tekrar dene.',
        'attendance_successful': 'Yoklama Basarili',
        'attendance_recorded': 'Yoklama Kaydedildi',
        'class': 'Ders',
        'week': 'Hafta',
        'your_attendance_confirmed': 'Yoklaman basariyla onaylandi.',
        'return_to_student_dashboard': 'Ogrenci Paneline Don',
        'class_details': 'Ders Detaylari',
        'students': 'Ogrenciler',
        'student_name': 'Ogrenci Adi',
        'full_name': 'Ad Soyad',
        'first_name': 'Ad',
        'last_name': 'Soyad',
        'gender': 'Cinsiyet',
        'birth_date': 'Dogum Tarihi',
        'birth_place': 'Dogum Yeri',
        'citizenship': 'Vatandaslik',
        'identity_number': 'Kimlik Numarasi',
        'nationality': 'Uyruk',
        'registered_city': 'Kayitli Il',
        'registered_district': 'Kayitli Ilce',
        'passport_number': 'Pasaport No',
        'active': 'Aktif',
        'passport_details': 'Pasaport Detaylari',
        'issued_date': 'Verilme Tarihi',
        'issued_place': 'Verilme Yeri',
        'valid_until': 'Gecerlilik Tarihi',
        'active_status_box': 'Aktif',
        'other_information': 'Diger Bilgiler',
        'marital_status': 'Medeni Durum',
        'blood_type': 'Kan Grubu',
        'veteran_martyr_relative_q': 'Gazi/Sehit Yakini mi?',
        'disabled_q': 'Engelli mi?',
        'disability_type': 'Engel Turu',
        'disability_rate': 'Engel Orani',
        'working_information': 'Calisma Bilgileri',
        'is_employed_q': 'Calisiyor mu?',
        'is_group_company_q': 'Grup Sirketi mi?',
        'company_name': 'Sirket Adi',
        'work_type': 'Calisma Sekli',
        'employment_start_date': 'Ise Giris Tarihi',
        'student_affairs_edit_note': 'Duzenleme Yapmak Istiyorsaniz Lutfen Ogrenci Islerine Basvurun',
        'expand': 'Ac',
        'collapse': 'Kapat',
        'role_label': 'Rol',
        'student_number_label': 'Ogrenci Numarasi',
        'attended_sessions': 'Katildigi Oturum',
        'absences': 'Devamsizlik',
        'passed_q': 'Gecti mi?',
        'yes': 'Evet',
        'no': 'Hayir',
        'no_students_in_class': 'Bu derste henuz ogrenci yok.',
        'back': 'Geri',
        'create_class': 'Ders Olustur',
        'create_new_class': 'Yeni Ders Olustur',
        'class_name': 'Ders Adi',
        'create': 'Olustur',
        'join_class': 'Derse Katil',
        'search_class': 'Ders ara...',
        'join': 'Katil',
        'absence_title': 'Devamsizlik',
        'absence_subtitle': '{name} icin tum yoklama islemleri burada yonetilir.',
        'back_to_home': 'Ana Sayfaya Don',
        'enrolled_courses': 'Kayitli Dersler',
        'active_attendance': 'Aktif Yoklama',
        'total_sessions': 'Toplam Oturum',
        'average_absence': 'Ortalama Devamsizlik',
        'search_course': 'Ders ara...',
        'search': 'Ara',
        'course_based_absence': 'Ders Bazli Devamsizlik',
        'total': 'Toplam',
        'attended': 'Katilim',
        'status': 'Durum',
        'attendance_already_marked': 'Yoklama zaten isaretli',
        'mark_attendance': 'Yoklama Isaretle',
        'no_active_attendance': 'Aktif yoklama yok',
        'absence_history': 'Devamsizlik Gecmisi',
        'no_enrolled_course_found': 'Kayitli ders bulunamadi.',
        'active_attendance_alerts': 'Aktif Yoklama Uyarilari',
        'ends': 'Biter',
        'no_active_attendance_alerts': 'Aktif yoklama uyarisi yok.',
        'join_course': 'Derse Katil',
        'no_additional_course': 'Katilinabilecek ek ders yok.',
        'my_attendance_history': 'Yoklama Gecmisim',
        'present': 'Var',
        'absent': 'Yok',
        'no_confirmed_attendance': 'Bu ders icin henuz onayli yoklama oturumu yok.',
        'account_settings': 'Hesap Ayarlari',
        'change_password': 'Sifre Degistir',
        'current_password': 'Mevcut Sifre',
        'new_password': 'Yeni Sifre',
        'confirm_new_password': 'Yeni Sifreyi Onayla',
        'account_deletion': 'Hesap Silme',
        'student_delete_account_disabled': 'Ogrenciler icin hesap silme kapatilidir. Profilin ve yoklama gecmisin kayit butunlugu icin saklanir.',
        'delete_account': 'Hesabi Sil',
        'delete_account_warning': 'Bu islem geri alinamaz. Hesabini silmek icin sifreni gir.',
        'my_attendance_history_title': 'Yoklama Gecmisim',
        'attendance_history': 'Yoklama Gecmisi',
        'back_to_dashboard': 'Panele Don',
        'filters': 'Filtreler',
        'search_week': 'Hafta ara',
        'start': 'Baslangic',
        'end': 'Bitis',
        'filter': 'Filtrele',
        'clear_filters': 'Filtreleri temizle',
        'download_csv': 'CSV Indir',
        'summary': 'Ozet',
        'detail': 'Detay',
        'no_recorded_attendance': 'Henuz kayitli yoklama oturumu yok.',
        'confirm_delete_attendance_session': 'Bu yoklama oturumunu silmek istedigine emin misin?',
        'attendance_detail': 'Yoklama Detayi',
        'absence_pct': 'Devamsizlik %',
        'total_classes': 'Toplam Ders',
        'absence_percent_label': 'Devamsizlik (%)',
        'no_students_found_class': 'Bu derste henuz ogrenci bulunamadi.',
        'qr_code': 'QR Kod',
        'token': 'Token',
        'attendance_link': 'Yoklama Baglantisi',
        'qr_help_text': 'Telefonunun ayni agda oldugundan ve uygulamanin bu URL uzerinden erisilebilir oldugundan emin ol.',
        'download': 'Indir',
        'print_or_pdf': 'Yazdir / PDF Kaydet',
        'welcome_teacher': 'Hos geldin, {name}',
        'start_attendance': 'Yoklama Baslat',
        'week_placeholder': 'Hafta (ornek: 1)',
        'start_and_open_qr': 'Baslat ve QR Ac',
        'create_class_first': 'Once bir ders olusturman gerekiyor.',
        'current_classes_and_qr': 'Mevcut Dersler ve QR Kodlari',
        'students_count': 'Ogrenci: {count}',
        'session_active': 'Oturum Aktif',
        'no_active_session': 'Aktif Oturum Yok',
        'class_qr_code': 'Ders QR Kodu',
        'fullscreen': 'Tam Ekran',
        'qr_not_generated': 'QR kodu henuz uretilmedi.',
        'active_attendance_session': 'Aktif Yoklama Oturumu',
        'live_attendance': 'Canli Yoklama',
        'ends_at': 'Biter',
        'finish_attendance': 'Yoklamayi Bitir',
        'no_active_session_note': 'Henuz aktif yoklama oturumu yok. Yukaridan Yoklama Baslat ile olusturabilirsin.',
        'you_have_not_created_class': 'Henuz hic ders olusturmadin.',
        'popup_blocked': 'Yeni sekme engellendi. Lutfen acilir pencerelere izin ver.',
        'pass': 'Gecti',
        'fail': 'Kaldi',
        'academic_status': 'Akademik Durum',
        'active_value': 'Aktif',
        'program': 'Program',
        'university_undergraduate_program': 'Universite Lisans Programi',
        'course_count': 'Ders Sayisi',
        'grading_system': 'Notlandirma Sistemi',
        'letter_grade_400': 'Harf Notu (4.00)',
        'guardian_full_name': 'Veli Ad Soyad',
        'relationship': 'Yakinlik',
        'emergency_phone': 'Acil Durum Telefonu',
        'note': 'Not',
        'not_set_yet': 'Henuz ayarlanmadi',
        'family_note': 'Bu alanlar bir sonraki adimda formlar ile duzenlenebilir.',
        'document_status': 'Belge Durumu',
        'registration_document': 'Kayit Belgesi',
        'student_certificate': 'Ogrenci Belgesi',
        'documents_note': 'Belgeler modulu bu ekranda genisletilecektir.',
        'no_uploaded_document': 'Henuz yuklenmis belge yok',
        'pending': 'Beklemede',
        'can_be_requested': 'Talep edilebilir',
        'phone': 'Telefon',
        'address': 'Adres',
        'contact_preference': 'Iletisim Tercihi',
        'total_debt': 'Toplam Borc',
        'total_paid': 'Toplam Odenen',
        'current_balance': 'Guncel Bakiye',
        'current_account_note': 'Cari hesap modulu burada detaylandirilacaktir.',
        'last_payment': 'Son Odeme',
        'payment_method': 'Odeme Yontemi',
        'scheduled_payment': 'Planli Odeme',
        'payment_note': 'Odeme modulu bir sonraki adimda genisletilebilir.',
        'no_record_found': 'Kayit bulunamadi',
        'undefined': 'Tanimsiz',
        'none': 'Yok',
        'current_term': 'Guncel Donem',
        'registered_course_count': 'Kayitli Ders Sayisi',
        'registered_courses': 'Kayitli Dersler',
        'status_label': 'Durum',
        'no_registered_course': 'Henuz kayitli ders yok',
        'active_term': 'Aktif Donem',
        'student_label': 'Ogrenci',
        'gpa_4': 'GPA (4.00)',
        'weighted_credits': 'Agirlikli Kredi',
        'no_graded_data': 'Henuz notlandirilmis ders verisi yok.',
        'calculated_from_courses': '{count} notlandirilmis ders uzerinden hesaplandi.',
        'transcript_table_not_initialized': 'Transkript tablosu henuz hazir degil.',
        'today': 'Bugun',
        'upcoming_academic_events': 'Yaklasan Akademik Etkinlikler',
        'term_window': 'Donem Araligi',
        'configured_by_admin': 'Yonetim tarafindan tanimlanir',
        'academic_calendar_note': 'Akademik takvim etkinlikleri burada detayli listelenecektir.',
        'upcoming_exams': 'Yaklasan Sinavlar',
        'completed_exams': 'Tamamlanan Sinavlar',
        'next_exam_date': 'Sonraki Sinav Tarihi',
        'not_scheduled': 'Planlanmadi',
        'exam_module_note': 'Sinav yonetimi modulu bir sonraki adimda genisletilebilir.',
        'already_enrolled_named': "'{name}' dersine zaten kayitlisin.",
        'no_class_found_named': "'{name}' adinda bir ders bulunamadi.",
        'identity_information': 'Kimlik Bilgileri',
        'identity_information_desc': 'Ogrenci kimligi ve temel profil bilgileri.',
        'education_information': 'Egitim Bilgileri',
        'education_information_desc': 'Bolum, program, donem ve akademik durum.',
        'education_reset_note': 'Bu bolum temizlendi. Burayi sifirdan birlikte olusturacagiz.',
        'university_information': 'Universite Bilgileri',
        'entry_place': 'Giris Yeri',
        'entry_type': 'Giris Tipi',
        'academic_year': 'Akademik Yil',
        'term': 'Donem',
        'faculty': 'Fakulte',
        'department': 'Bolum',
        'scholarship_type': 'Burs Turu',
        'placement_type': 'Yerlesme Turu',
        'score_type': 'Puan Turu',
        'achievement_score': 'Basari Puani',
        'placement_score': 'Yerlesme Puani',
        'preference_order': 'Tercih Sirasi',
        'highschool_information': 'Lise Bilgileri',
        'highschool_name': 'Lise Adi',
        'highschool_info': 'Lise Bilgisi',
        'highschool_graduation_date': 'Mezuniyet Tarihi',
        'family_information': 'Aile Bilgileri',
        'family_information_desc': 'Aile iletisimi ve yakin bilgileri.',
        'documents': 'Belgeler',
        'documents_desc': 'Belge ve sertifika islemleri.',
        'contact': 'Iletisim',
        'contact_desc': 'Iletisim tercihleri ve adres bilgileri.',
        'current_account': 'Cari Hesap',
        'current_account_desc': 'Bakiye, borc ve alacak ozeti.',
        'payments': 'Odemeler',
        'payments_desc': 'Odeme gecmisi ve yeni odeme islemleri.',
        'absence': 'Devamsizlik',
        'absence_desc': 'Tam yoklama akisiyla devamsizlik analizi.',
        'term_courses': 'Donem Dersleri',
        'term_courses_desc': 'Guncel donem ders listesi ve yuk bilgisi.',
        'transcript': 'Transkript',
        'transcript_desc': 'Not ozeti ve ortalama gorunumu.',
        'academic_calendar': 'Akademik Takvim',
        'academic_calendar_desc': 'Onemli tarihler ve akademik etkinlikler.',
        'exams': 'Sinavlar',
        'exams_desc': 'Yaklasan ve tamamlanan sinav bilgileri.',
        'modules': 'Moduller',
    },
}


def _detect_local_ip() -> str:
    """Best-effort local network IP detection for phone-accessible QR links."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def _safe_int_env(name: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    raw = (os.getenv(name) or '').strip()
    value = default
    if raw:
        try:
            value = int(raw)
        except ValueError:
            value = default

    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def _configure_app_logging(flask_app: Flask):
    log_dir = (os.getenv('APP_LOG_DIR') or os.path.join(flask_app.root_path, 'logs')).strip()
    log_file = (os.getenv('APP_LOG_FILE') or 'app.log').strip() or 'app.log'
    max_bytes = _safe_int_env('APP_LOG_MAX_BYTES', 5 * 1024 * 1024, minimum=1024, maximum=200 * 1024 * 1024)
    backup_count = _safe_int_env('APP_LOG_BACKUP_COUNT', 7, minimum=1, maximum=90)
    level_name = (os.getenv('APP_LOG_LEVEL') or 'INFO').strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_file)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8',
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    flask_app.logger.handlers.clear()
    flask_app.logger.setLevel(level)
    flask_app.logger.addHandler(file_handler)
    flask_app.logger.addHandler(stream_handler)

    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(level)
    if not any(isinstance(handler, RotatingFileHandler) for handler in werkzeug_logger.handlers):
        werkzeug_logger.addHandler(file_handler)


def _normalize_samesite(value: str | None) -> str:
    normalized = (value or 'Lax').strip().lower()
    if normalized == 'strict':
        return 'Strict'
    if normalized == 'none':
        return 'None'
    return 'Lax'


def _resolve_app_database_uri() -> str:
    """Resolve SQLAlchemy DB URI with secure/env-aware precedence.

    Priority:
    1) DATABASE_URL (primary app/runtime setting)
    2) ALEMBIC_DB_URL (migration rehearsal compatibility)
    3) local SQLite fallback
    """
    env_url = (os.getenv('DATABASE_URL') or os.getenv('ALEMBIC_DB_URL') or '').strip()
    if env_url:
        # SQLAlchemy expects postgresql:// prefix; accept Heroku-style postgres:// too.
        if env_url.startswith('postgres://'):
            return env_url.replace('postgres://', 'postgresql://', 1)
        return env_url
    return 'sqlite:///attendance.db'

# ------------------ APP INIT ------------------
app = Flask(__name__)
# Stable fallback secret for local development so debug reloads do not invalidate sessions.
app.secret_key = os.getenv('FLASK_SECRET_KEY') or 'dev-local-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = _resolve_app_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Base URL encoded in QR codes for phone scanning (example: http://192.168.1.25:5000)
app.config['QR_BASE_URL'] = os.getenv('QR_BASE_URL', f"http://{_detect_local_ip()}:5000").rstrip('/')
app.config['ATTENDANCE_WINDOW_MINUTES'] = _safe_int_env('ATTENDANCE_WINDOW_MINUTES', 180, minimum=1, maximum=24 * 60)
app.config['FORCE_CANONICAL_HOST'] = os.getenv('FORCE_CANONICAL_HOST', '0') == '1'
# Session/cookie security defaults (can be overridden by environment variables).
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_NAME'] = os.getenv('SESSION_COOKIE_NAME', 'qr_attendance_session')
app.config['SESSION_COOKIE_SAMESITE'] = _normalize_samesite(os.getenv('SESSION_COOKIE_SAMESITE', 'Lax'))
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', '0') == '1'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=_safe_int_env('REMEMBER_ME_DAYS', 30, minimum=1, maximum=30))
app.config['SESSION_REFRESH_EACH_REQUEST'] = False
app.config['LOGIN_RATE_LIMIT_MAX_ATTEMPTS'] = _safe_int_env('LOGIN_RATE_LIMIT_MAX_ATTEMPTS', 8, minimum=1, maximum=100)
app.config['LOGIN_RATE_LIMIT_WINDOW_SECONDS'] = _safe_int_env('LOGIN_RATE_LIMIT_WINDOW_SECONDS', 300, minimum=10, maximum=3600)
app.config['LOGIN_LOCK_MAX_FAILURES'] = _safe_int_env('LOGIN_LOCK_MAX_FAILURES', 5, minimum=1, maximum=50)
app.config['LOGIN_LOCK_WINDOW_SECONDS'] = _safe_int_env('LOGIN_LOCK_WINDOW_SECONDS', 900, minimum=30, maximum=86400)
app.config['ADMIN_MUTATION_RATE_LIMIT_MAX'] = _safe_int_env('ADMIN_MUTATION_RATE_LIMIT_MAX', 30, minimum=1, maximum=200)
app.config['ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS'] = _safe_int_env('ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS', 60, minimum=10, maximum=3600)
app.config['PASSWORD_MIN_LENGTH'] = _safe_int_env('PASSWORD_MIN_LENGTH', 10, minimum=8, maximum=128)
app.config['METRICS_SLOW_REQUEST_MS'] = _safe_int_env('METRICS_SLOW_REQUEST_MS', 750, minimum=50, maximum=60000)
app.config['HEALTH_WARN_ERROR_RATE_PCT'] = _safe_int_env('HEALTH_WARN_ERROR_RATE_PCT', 5, minimum=0, maximum=100)
app.config['HEALTH_WARN_P95_MS'] = _safe_int_env('HEALTH_WARN_P95_MS', 1000, minimum=50, maximum=120000)
app.config['EMAIL_DRY_RUN'] = os.getenv('EMAIL_DRY_RUN', '1') == '1'
app.config['EMAIL_SMTP_HOST'] = (os.getenv('EMAIL_SMTP_HOST') or '').strip()
app.config['EMAIL_SMTP_PORT'] = _safe_int_env('EMAIL_SMTP_PORT', 587, minimum=1, maximum=65535)
app.config['EMAIL_SMTP_USER'] = (os.getenv('EMAIL_SMTP_USER') or '').strip()
app.config['EMAIL_SMTP_PASSWORD'] = (os.getenv('EMAIL_SMTP_PASSWORD') or '').strip()
app.config['EMAIL_USE_TLS'] = os.getenv('EMAIL_USE_TLS', '1') == '1'
app.config['EMAIL_FROM'] = (os.getenv('EMAIL_FROM') or 'noreply@qr-attendance.local').strip()
app.config['EMAIL_TIMEOUT_SECONDS'] = _safe_int_env('EMAIL_TIMEOUT_SECONDS', 10, minimum=1, maximum=120)
db.init_app(app)
_configure_app_logging(app)


@app.before_request
def enforce_canonical_host():
    """Keep navigation on one host (LAN IP) to prevent mixed 127/192 session flow issues."""
    if not app.config.get('FORCE_CANONICAL_HOST'):
        return None

    base = urlparse(app.config['QR_BASE_URL'])
    canonical_host = base.netloc
    current_host = request.host

    if not canonical_host or current_host == canonical_host:
        return None

    if current_host.startswith('127.0.0.1') or current_host.startswith('localhost'):
        target = f"{base.scheme}://{canonical_host}{request.full_path}"
        return redirect(target.rstrip('?'))

    return None


@app.before_request
def mark_request_start_time():
    g.request_start_ts = time.perf_counter()


@app.before_request
def enforce_account_lock_policy():
    user_id = session.get('user_id')
    if not user_id:
        return None

    if request.endpoint in {'static', 'login', 'logout', 'set_language'}:
        return None

    user = db.session.get(User, user_id)
    if not user:
        session.clear()
        return redirect(url_for('login'))

    if not user.is_locked:
        return None

    lang = _get_language()
    session.clear()
    session['lang'] = lang
    flash('Hesabınız kilitlenmiş. Lütfen bir yönetici ile iletişime geçin.', 'danger')
    return redirect(url_for('login'))

# --- DB Migration Helpers (SQLite) ---
# Adds new columns if they don't exist yet (works with SQLite and PostgreSQL).
def _ensure_column(table: str, column: str, definition: str):
    with app.app_context():
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(db.engine)
        existing = {col['name'] for col in inspector.get_columns(table)}
        if column not in existing:
            normalized_definition = definition
            if db.engine.dialect.name == 'postgresql' and definition.strip().upper() == 'DATETIME':
                normalized_definition = 'TIMESTAMP'
            with db.engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {normalized_definition}"))


def _attendance_url(token: str) -> str:
    return f"{app.config['QR_BASE_URL']}/attendance/{token}"


def _session_deadline(session_obj: AttendanceSession) -> datetime.datetime:
    return session_obj.date + datetime.timedelta(minutes=app.config['ATTENDANCE_WINDOW_MINUTES'])


def _auto_finalize_expired_sessions(class_id: int | None = None):
    query = AttendanceSession.query.filter_by(active=True)
    if class_id is not None:
        query = query.filter_by(class_id=class_id)

    now = datetime.datetime.now()
    changed = False
    for sess in query.all():
        if now >= _session_deadline(sess):
            sess.active = False
            sess.confirmed = True
            changed = True

    if changed:
        db.session.commit()


def _is_safe_next_url(target: str) -> bool:
    if not target:
        return False
    ref = urlparse(request.host_url)
    test = urlparse(target)
    return test.scheme in ('http', 'https', '') and (not test.netloc or test.netloc == ref.netloc)


def _is_rate_limited(scope: str, key: str, limit: int, window_seconds: int, now_ts: float | None = None) -> bool:
    if limit <= 0 or window_seconds <= 0:
        return False

    bucket_key = f"{scope}:{key}"
    bucket = RATE_LIMIT_EVENTS.setdefault(bucket_key, deque())
    current_ts = now_ts if now_ts is not None else datetime.datetime.now(datetime.UTC).timestamp()
    cutoff_ts = current_ts - window_seconds

    while bucket and bucket[0] <= cutoff_ts:
        bucket.popleft()

    if len(bucket) >= limit:
        return True

    bucket.append(current_ts)
    return False


def _record_login_failure_and_lock(user: User | None, email: str, now_ts: float | None = None) -> bool:
    """Track failed login attempts by email and lock matching user if threshold is reached."""
    if not user:
        return False

    max_failures = int(app.config.get('LOGIN_LOCK_MAX_FAILURES', 0) or 0)
    window_seconds = int(app.config.get('LOGIN_LOCK_WINDOW_SECONDS', 0) or 0)
    if max_failures <= 0 or window_seconds <= 0:
        return False

    bucket_key = f"loginfail:{email.strip().lower()}"
    bucket = RATE_LIMIT_EVENTS.setdefault(bucket_key, deque())
    current_ts = now_ts if now_ts is not None else datetime.datetime.now(datetime.UTC).timestamp()
    cutoff_ts = current_ts - window_seconds

    while bucket and bucket[0] <= cutoff_ts:
        bucket.popleft()

    bucket.append(current_ts)

    if len(bucket) < max_failures or user.is_locked:
        return False

    user.is_locked = True
    db.session.commit()
    return True


def _clear_login_failure_history(email: str):
    RATE_LIMIT_EVENTS.pop(f"loginfail:{email.strip().lower()}", None)


def _admin_mutation_rate_key() -> str:
    actor_id = session.get('user_id') or 'anonymous'
    endpoint = request.endpoint or 'unknown'
    ip = request.remote_addr or 'unknown'
    return f"{actor_id}:{endpoint}:{ip}"


def _get_language() -> str:
    lang = (session.get('lang') or DEFAULT_LANGUAGE).lower()
    return lang if lang in LANGUAGES else DEFAULT_LANGUAGE


def _t(key: str, **kwargs) -> str:
    lang = _get_language()
    template = TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


def _lang_text(tr_text: str, en_text: str) -> str:
    return tr_text if _get_language() == 'tr' else en_text


def _get_or_create_csrf_token() -> str:
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


def _is_csrf_token_valid() -> bool:
    session_token = session.get('_csrf_token')
    form_token = (request.form.get('csrf_token') or '').strip()
    header_token = (request.headers.get('X-CSRF-Token') or '').strip()
    provided_token = form_token or header_token

    if not session_token or not provided_token:
        return False
    return hmac.compare_digest(session_token, provided_token)


@app.context_processor
def inject_i18n_helpers():
    return {
        't': _t,
        'lang_text': _lang_text,
        'current_lang': _get_language(),
        'csrf_token': _get_or_create_csrf_token,
    }


def csrf_protect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and not _is_csrf_token_valid():
            flash('Güvenlik doğrulaması başarısız. Lütfen tekrar deneyin.', 'danger')
            fallback = request.referrer or url_for('login')
            return redirect(fallback)
        return f(*args, **kwargs)
    return decorated_function


def rate_limit_protect(scope: str, limit_config_key: str, window_config_key: str, key_builder):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            limit = int(app.config.get(limit_config_key, 0) or 0)
            window_seconds = int(app.config.get(window_config_key, 0) or 0)
            key = key_builder() if callable(key_builder) else str(key_builder)

            if _is_rate_limited(scope, key, limit, window_seconds):
                flash('Çok fazla istek gönderildi. Lütfen bekleyip tekrar deneyin.', 'danger')
                fallback = request.referrer or url_for('login')
                return redirect(fallback)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _percentile(values, pct):
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(round((pct / 100.0) * (len(sorted_values) - 1)))
    index = max(0, min(index, len(sorted_values) - 1))
    return float(sorted_values[index])


def _build_health_snapshot():
    db_ok = True
    db_error = None
    try:
        db.session.execute(text('SELECT 1'))
    except Exception as exc:
        db.session.rollback()
        db_ok = False
        db_error = str(exc)

    total_requests = int(REQUEST_METRICS['total_requests'])
    error_total = int(REQUEST_METRICS['error_4xx']) + int(REQUEST_METRICS['error_5xx'])
    error_rate_pct = (error_total / total_requests * 100.0) if total_requests else 0.0

    avg_values = []
    p95_source = []
    for bucket in REQUEST_METRICS['by_endpoint'].values():
        if bucket['count'] > 0:
            avg = bucket['total_ms'] / bucket['count']
            avg_values.append(avg)
            p95_source.append(avg)

    global_avg_ms = (sum(avg_values) / len(avg_values)) if avg_values else 0.0
    p95_ms = _percentile(p95_source, 95)

    warn_error_rate = float(app.config.get('HEALTH_WARN_ERROR_RATE_PCT', 5))
    warn_p95 = float(app.config.get('HEALTH_WARN_P95_MS', 1000))

    status = 'healthy'
    reasons = []
    if not db_ok:
        status = 'unhealthy'
        reasons.append('database_check_failed')
    elif error_rate_pct >= warn_error_rate or p95_ms >= warn_p95:
        status = 'degraded'
        if error_rate_pct >= warn_error_rate:
            reasons.append('error_rate_threshold_exceeded')
        if p95_ms >= warn_p95:
            reasons.append('latency_threshold_exceeded')

    return {
        'status': status,
        'reasons': reasons,
        'generated_at_utc': datetime.datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z'),
        'since_utc': REQUEST_METRICS['since_utc'],
        'database_ok': db_ok,
        'database_error': db_error,
        'totals': {
            'requests': total_requests,
            'error_4xx': int(REQUEST_METRICS['error_4xx']),
            'error_5xx': int(REQUEST_METRICS['error_5xx']),
            'error_rate_pct': round(error_rate_pct, 2),
        },
        'latency_ms': {
            'global_avg': round(global_avg_ms, 2),
            'p95_estimate': round(p95_ms, 2),
            'slow_threshold': int(app.config.get('METRICS_SLOW_REQUEST_MS', 750)),
            'warn_threshold': int(warn_p95),
        },
        'thresholds': {
            'warn_error_rate_pct': warn_error_rate,
            'warn_p95_ms': warn_p95,
        },
    }


@app.after_request
def collect_request_metrics(response):
    started_at = getattr(g, 'request_start_ts', None)
    if started_at is None:
        return response

    duration_ms = (time.perf_counter() - started_at) * 1000.0
    endpoint = request.endpoint or 'unknown'
    method = request.method
    status_code = int(response.status_code)

    REQUEST_METRICS['total_requests'] += 1
    if 400 <= status_code < 500:
        REQUEST_METRICS['error_4xx'] += 1
    if status_code >= 500:
        REQUEST_METRICS['error_5xx'] += 1

    key = f"{method} {endpoint}"
    bucket = REQUEST_METRICS['by_endpoint'].get(key)
    if not bucket:
        bucket = {
            'count': 0,
            'total_ms': 0.0,
            'max_ms': 0.0,
            'min_ms': duration_ms,
            'last_status': status_code,
            'last_seen_utc': datetime.datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z'),
        }
        REQUEST_METRICS['by_endpoint'][key] = bucket

    bucket['count'] += 1
    bucket['total_ms'] += duration_ms
    bucket['max_ms'] = max(bucket['max_ms'], duration_ms)
    bucket['min_ms'] = min(bucket['min_ms'], duration_ms)
    bucket['last_status'] = status_code
    bucket['last_seen_utc'] = datetime.datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z')

    slow_ms = int(app.config.get('METRICS_SLOW_REQUEST_MS', 750) or 750)
    if duration_ms >= slow_ms:
        app.logger.warning(
            'Slow request detected: endpoint=%s method=%s status=%s duration_ms=%.2f',
            endpoint,
            method,
            status_code,
            duration_ms,
        )

    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
    response.headers.setdefault(
        'Content-Security-Policy',
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; font-src 'self' data:",
    )

    return response


def _fetch_weather(city: str | None = None, lat: float | None = None, lon: float | None = None) -> dict | None:
    """Fetch current weather from wttr.in using coordinates when available, with city fallback."""
    query = None
    display_city = city

    if lat is not None and lon is not None:
        query = f"{lat:.4f},{lon:.4f}"
        display_city = f"{lat:.4f}, {lon:.4f}"
    elif city:
        query = quote(city.strip())

    if not query:
        return None

    try:
        req = Request(
            f"https://wttr.in/{query}?format=j1",
            headers={"User-Agent": "qr-attendance-portal/1.0"},
        )
        with urlopen(req, timeout=3.0) as resp:
            payload = json.loads(resp.read().decode('utf-8'))

        current = (payload.get('current_condition') or [{}])[0]
        desc_list = current.get('weatherDesc') or [{}]
        nearest = (payload.get('nearest_area') or [{}])[0]
        area_name = ((nearest.get('areaName') or [{}])[0]).get('value') if nearest else None
        return {
            'city': area_name or display_city or 'Unknown',
            'temperature_c': current.get('temp_C', '-'),
            'condition': desc_list[0].get('value', 'Unknown'),
            'humidity': current.get('humidity', '-'),
            'wind_kmph': current.get('windspeedKmph', '-'),
            'source': 'location' if lat is not None and lon is not None else 'city',
            'ok': True,
        }
    except Exception:
        return {
            'city': display_city or 'Unknown',
            'temperature_c': '-',
            'condition': 'Unavailable',
            'humidity': '-',
            'wind_kmph': '-',
            'source': 'location' if lat is not None and lon is not None else 'city',
            'ok': False,
        }

with app.app_context():
    db.create_all()

    # Add columns if they do not exist yet.
    _ensure_column('classes', 'qr_token', 'TEXT')
    _ensure_column('classes', 'qr_filename', 'TEXT')
    _ensure_column('users', 'is_locked', 'BOOLEAN DEFAULT 0')
    _ensure_column('attendance_sessions', 'active', 'BOOLEAN DEFAULT 0')
    _ensure_column('attendance_sessions', 'confirmed', 'BOOLEAN DEFAULT 0')
    _ensure_column('courses', 'capacity', 'INTEGER DEFAULT 60')
    _ensure_column('courses', 'schedule_slot', 'TEXT')
    _ensure_column('announcements', 'starts_at', 'DATETIME')
    _ensure_column('announcements', 'ends_at', 'DATETIME')
    _ensure_column('students', 'first_name', 'TEXT')
    _ensure_column('students', 'last_name', 'TEXT')
    _ensure_column('students', 'gender', 'TEXT')
    _ensure_column('students', 'birth_date', 'DATE')
    _ensure_column('students', 'birth_place', 'TEXT')
    _ensure_column('students', 'identity_number', 'TEXT')
    _ensure_column('students', 'nationality', 'TEXT')
    _ensure_column('students', 'registered_city', 'TEXT')
    _ensure_column('students', 'registered_district', 'TEXT')
    _ensure_column('students', 'passport_number', 'TEXT')
    _ensure_column('students', 'passport_active', 'BOOLEAN DEFAULT 0')
    _ensure_column('students', 'passport_issue_date', 'DATE')
    _ensure_column('students', 'passport_issue_place', 'TEXT')
    _ensure_column('students', 'passport_expiry_date', 'DATE')
    _ensure_column('students', 'marital_status', 'TEXT')
    _ensure_column('students', 'blood_type', 'TEXT')
    _ensure_column('students', 'is_veteran_martyr_relative', 'BOOLEAN DEFAULT 0')
    _ensure_column('students', 'is_disabled', 'BOOLEAN DEFAULT 0')
    _ensure_column('students', 'disability_type', 'TEXT')
    _ensure_column('students', 'disability_rate', 'TEXT')
    _ensure_column('students', 'is_employed', 'BOOLEAN DEFAULT 0')
    _ensure_column('students', 'is_group_company', 'BOOLEAN DEFAULT 0')
    _ensure_column('students', 'company_name', 'TEXT')
    _ensure_column('students', 'work_type', 'TEXT')
    _ensure_column('students', 'employment_start_date', 'DATE')
    _ensure_column('students', 'university_entry_place', 'TEXT')
    _ensure_column('students', 'university_entry_type', 'TEXT')
    _ensure_column('students', 'university_academic_year', 'TEXT')
    _ensure_column('students', 'university_term', 'TEXT')
    _ensure_column('students', 'university_faculty', 'TEXT')
    _ensure_column('students', 'university_department', 'TEXT')
    _ensure_column('students', 'university_scholarship_type', 'TEXT')
    _ensure_column('students', 'university_placement_type', 'TEXT')
    _ensure_column('students', 'university_score_type', 'TEXT')
    _ensure_column('students', 'university_achievement_score', 'TEXT')
    _ensure_column('students', 'university_placement_score', 'TEXT')
    _ensure_column('students', 'university_preference_order', 'TEXT')
    _ensure_column('students', 'highschool_name', 'TEXT')
    _ensure_column('students', 'highschool_info', 'TEXT')
    _ensure_column('students', 'highschool_graduation_date', 'DATE')

    # Generate/update class QR files in URL format for all classes.
    qr_folder = os.path.join(app.root_path, "static", "qrcodes")
    if not os.path.exists(qr_folder):
        os.makedirs(qr_folder)

    for cls in Class.query.all():
        if not cls.qr_token:
            cls.qr_token = secrets.token_hex(4)
        if not cls.qr_filename:
            cls.qr_filename = f"{cls.name}_qr_{cls.qr_token}.png"

        qr_path = os.path.join(qr_folder, cls.qr_filename)
        img = qrcode.make(_attendance_url(cls.qr_token))
        img.save(qr_path)
    db.session.commit()

# ------------------ LOGIN REQUIRED DECORATOR ------------------
def login_required_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Lütfen önce giriş yapın!', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Lütfen önce giriş yapın!', 'danger')
                return redirect(url_for('login', next=request.url))
            if session.get('role') != required_role:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Day 3: Minimal permission layer on top of existing role guards.
PERMISSIONS = {
    'TEACHER_DASHBOARD_VIEW': 'teacher.dashboard.view',
    'TEACHER_CLASS_HISTORY_READ': 'teacher.class.history.read',
    'TEACHER_CLASS_HISTORY_EXPORT': 'teacher.class.history.export',
    'TEACHER_SESSION_STATS_READ': 'teacher.session.stats.read',
    'TEACHER_SESSION_READ': 'teacher.session.read',
    'TEACHER_SESSION_DELETE': 'teacher.session.delete',
    'TEACHER_ACCOUNT_READ': 'teacher.account.read',
    'TEACHER_ACCOUNT_UPDATE': 'teacher.account.update',
    'TEACHER_CLASS_CREATE': 'teacher.class.create',
    'TEACHER_QR_VIEW': 'teacher.qr.view',
    'TEACHER_CLASS_READ': 'teacher.class.read',
    'TEACHER_SESSION_CREATE': 'teacher.session.create',
    'TEACHER_SESSION_UPDATE_ATTENDANCE': 'teacher.session.update_attendance',
    'TEACHER_SESSION_STOP': 'teacher.session.stop',
    'TEACHER_REPORT_READ': 'teacher.report.read',
    'TEACHER_DASHBOARD_CALENDAR_UPDATE': 'teacher.dashboard.calendar.update',
    'STUDENT_ACCOUNT_READ': 'student.account.read',
    'STUDENT_ACCOUNT_UPDATE': 'student.account.update',
    'STUDENT_DASHBOARD_VIEW': 'student.dashboard.view',
    'STUDENT_DASHBOARD_CALENDAR_UPDATE': 'student.dashboard.calendar.update',
    'STUDENT_ABSENCE_READ': 'student.absence.read',
    'STUDENT_ABSENCE_UPDATE': 'student.absence.update',
    'STUDENT_IDENTITY_READ': 'student.identity.read',
    'STUDENT_EDUCATION_READ': 'student.education.read',
    'STUDENT_FAMILY_READ': 'student.family.read',
    'STUDENT_DOCUMENTS_READ': 'student.documents.read',
    'STUDENT_CONTACT_READ': 'student.contact.read',
    'STUDENT_CURRENT_ACCOUNT_READ': 'student.current_account.read',
    'STUDENT_PAYMENT_READ': 'student.payment.read',
    'STUDENT_TERM_COURSES_READ': 'student.term_courses.read',
    'STUDENT_TERM_COURSES_UPDATE': 'student.term_courses.update',
    'STUDENT_TRANSCRIPT_READ': 'student.transcript.read',
    'STUDENT_ACADEMIC_CALENDAR_READ': 'student.academic_calendar.read',
    'STUDENT_EXAMS_READ': 'student.exams.read',
    'STUDENT_CLASS_HISTORY_READ': 'student.class.history.read',
    'STUDENT_ATTENDANCE_MARK': 'student.attendance.mark',
    'STUDENT_REPORT_READ': 'student.report.read',
    'ADMIN_DASHBOARD_VIEW': 'admin.dashboard.view',
    'ADMIN_DASHBOARD_CALENDAR_UPDATE': 'admin.dashboard.calendar.update',
    'ADMIN_USER_READ': 'admin.user.read',
    'ADMIN_USER_UPDATE_ROLE': 'admin.user.update_role',
    'ADMIN_USER_LOCK_TOGGLE': 'admin.user.lock_toggle',
    'ADMIN_USER_PASSWORD_RESET': 'admin.user.password_reset',
    'ADMIN_CLASS_ASSIGN_TEACHER': 'admin.class.assign_teacher',
    'ADMIN_AUDIT_READ': 'admin.audit.read',
    'ADMIN_METRICS_READ': 'admin.metrics.read',
    'ADMIN_PERMISSION_MATRIX_READ': 'admin.permission_matrix.read',
    'ADMIN_NOTIFICATION_SEND': 'admin.notification.send',
    'ADMIN_COURSE_REGISTRATION_MANAGE': 'admin.course_registration.manage',
    'ADMIN_COURSE_REGISTRATION_OVERRIDE': 'admin.course_registration.override',
}

PERMISSION_MAP = {
    'teacher_dashboard': PERMISSIONS['TEACHER_DASHBOARD_VIEW'],
    'teacher_attendance_hub': PERMISSIONS['TEACHER_DASHBOARD_VIEW'],
    'teacher_grade_entry': PERMISSIONS['TEACHER_CLASS_READ'],
    'teacher_course_roster': PERMISSIONS['TEACHER_CLASS_READ'],
    'teacher_class_history': PERMISSIONS['TEACHER_CLASS_HISTORY_READ'],
    'export_teacher_class_history': PERMISSIONS['TEACHER_CLASS_HISTORY_EXPORT'],
    'session_stats': PERMISSIONS['TEACHER_SESSION_STATS_READ'],
    'teacher_history_redirect': PERMISSIONS['TEACHER_CLASS_HISTORY_READ'],
    'session_detail': PERMISSIONS['TEACHER_SESSION_READ'],
    'delete_session': PERMISSIONS['TEACHER_SESSION_DELETE'],
    'teacher_account': PERMISSIONS['TEACHER_ACCOUNT_READ'],
    'create_class': PERMISSIONS['TEACHER_CLASS_READ'],
    'view_qr': PERMISSIONS['TEACHER_QR_VIEW'],
    'class_detail': PERMISSIONS['TEACHER_CLASS_READ'],
    'create_session': PERMISSIONS['TEACHER_SESSION_CREATE'],
    'update_attendance': PERMISSIONS['TEACHER_SESSION_UPDATE_ATTENDANCE'],
    'stop_session': PERMISSIONS['TEACHER_SESSION_STOP'],
    'student_account': PERMISSIONS['STUDENT_ACCOUNT_READ'],
    'student_dashboard': PERMISSIONS['STUDENT_DASHBOARD_VIEW'],
    'student_absence': PERMISSIONS['STUDENT_ABSENCE_READ'],
    'student_identity_info': PERMISSIONS['STUDENT_IDENTITY_READ'],
    'student_education_info': PERMISSIONS['STUDENT_EDUCATION_READ'],
    'student_family_info': PERMISSIONS['STUDENT_FAMILY_READ'],
    'student_documents_info': PERMISSIONS['STUDENT_DOCUMENTS_READ'],
    'student_contact_info': PERMISSIONS['STUDENT_CONTACT_READ'],
    'student_current_account': PERMISSIONS['STUDENT_CURRENT_ACCOUNT_READ'],
    'student_payment_info': PERMISSIONS['STUDENT_PAYMENT_READ'],
    'student_term_courses': PERMISSIONS['STUDENT_TERM_COURSES_READ'],
    'student_term_courses_update': PERMISSIONS['STUDENT_TERM_COURSES_UPDATE'],
    'student_transcript': PERMISSIONS['STUDENT_TRANSCRIPT_READ'],
    'student_academic_calendar': PERMISSIONS['STUDENT_ACADEMIC_CALENDAR_READ'],
    'student_exams': PERMISSIONS['STUDENT_EXAMS_READ'],
    'student_class_history': PERMISSIONS['STUDENT_CLASS_HISTORY_READ'],
    'mark_attendance': PERMISSIONS['STUDENT_ATTENDANCE_MARK'],
    'admin_dashboard': PERMISSIONS['ADMIN_DASHBOARD_VIEW'],
    'admin_user_inventory': PERMISSIONS['ADMIN_USER_READ'],
    'admin_update_user_role': PERMISSIONS['ADMIN_USER_UPDATE_ROLE'],
    'admin_toggle_user_lock': PERMISSIONS['ADMIN_USER_LOCK_TOGGLE'],
    'admin_reset_user_password': PERMISSIONS['ADMIN_USER_PASSWORD_RESET'],
    'admin_class_assignments': PERMISSIONS['ADMIN_CLASS_ASSIGN_TEACHER'],
    'admin_assign_class_teacher': PERMISSIONS['ADMIN_CLASS_ASSIGN_TEACHER'],
    'admin_permission_audit_report': PERMISSIONS['ADMIN_AUDIT_READ'],
    'admin_operation_audit_report': PERMISSIONS['ADMIN_AUDIT_READ'],
    'admin_health_status_report': PERMISSIONS['ADMIN_METRICS_READ'],
    'admin_permission_matrix': PERMISSIONS['ADMIN_PERMISSION_MATRIX_READ'],
    'admin_notifications': PERMISSIONS['ADMIN_NOTIFICATION_SEND'],
    'admin_course_registration_window': PERMISSIONS['ADMIN_COURSE_REGISTRATION_MANAGE'],
    'admin_course_registration_override': PERMISSIONS['ADMIN_COURSE_REGISTRATION_OVERRIDE'],
}

ROLE_PERMISSIONS = {
    'teacher': {
        PERMISSIONS['TEACHER_DASHBOARD_VIEW'],
        PERMISSIONS['TEACHER_CLASS_HISTORY_EXPORT'],
        PERMISSIONS['TEACHER_SESSION_STATS_READ'],
        PERMISSIONS['TEACHER_CLASS_HISTORY_READ'],
        PERMISSIONS['TEACHER_SESSION_READ'],
        PERMISSIONS['TEACHER_SESSION_DELETE'],
        PERMISSIONS['TEACHER_ACCOUNT_READ'],
        PERMISSIONS['TEACHER_ACCOUNT_UPDATE'],
        PERMISSIONS['TEACHER_CLASS_CREATE'],
        PERMISSIONS['TEACHER_QR_VIEW'],
        PERMISSIONS['TEACHER_CLASS_READ'],
        PERMISSIONS['TEACHER_SESSION_CREATE'],
        PERMISSIONS['TEACHER_SESSION_UPDATE_ATTENDANCE'],
        PERMISSIONS['TEACHER_SESSION_STOP'],
        PERMISSIONS['TEACHER_REPORT_READ'],
        PERMISSIONS['TEACHER_DASHBOARD_CALENDAR_UPDATE'],
    },
    'student': {
        PERMISSIONS['STUDENT_ACCOUNT_READ'],
        PERMISSIONS['STUDENT_ACCOUNT_UPDATE'],
        PERMISSIONS['STUDENT_DASHBOARD_VIEW'],
        PERMISSIONS['STUDENT_DASHBOARD_CALENDAR_UPDATE'],
        PERMISSIONS['STUDENT_ABSENCE_READ'],
        PERMISSIONS['STUDENT_ABSENCE_UPDATE'],
        PERMISSIONS['STUDENT_IDENTITY_READ'],
        PERMISSIONS['STUDENT_EDUCATION_READ'],
        PERMISSIONS['STUDENT_FAMILY_READ'],
        PERMISSIONS['STUDENT_DOCUMENTS_READ'],
        PERMISSIONS['STUDENT_CONTACT_READ'],
        PERMISSIONS['STUDENT_CURRENT_ACCOUNT_READ'],
        PERMISSIONS['STUDENT_PAYMENT_READ'],
        PERMISSIONS['STUDENT_TERM_COURSES_READ'],
        PERMISSIONS['STUDENT_TERM_COURSES_UPDATE'],
        PERMISSIONS['STUDENT_TRANSCRIPT_READ'],
        PERMISSIONS['STUDENT_ACADEMIC_CALENDAR_READ'],
        PERMISSIONS['STUDENT_EXAMS_READ'],
        PERMISSIONS['STUDENT_CLASS_HISTORY_READ'],
        PERMISSIONS['STUDENT_ATTENDANCE_MARK'],
        PERMISSIONS['STUDENT_REPORT_READ'],
    },
    'admin': set(PERMISSIONS.values()),
}


def has_permission(role, permission_key):
    if not permission_key:
        return True
    role_permissions = ROLE_PERMISSIONS.get(role, set())
    return permission_key in role_permissions


def _log_permission_denied(permission_key):
    event = {
        'timestamp': datetime.datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z'),
        'user_id': session.get('user_id'),
        'role': session.get('role'),
        'endpoint': request.endpoint,
        'permission': permission_key,
        'method': request.method,
        'path': request.path,
        'ip': request.remote_addr,
    }
    PERMISSION_AUDIT_EVENTS.appendleft(event)

    try:
        db.session.add(
            PermissionAuditLog(
                user_id=event['user_id'],
                role=event['role'],
                endpoint=event['endpoint'],
                permission=event['permission'],
                method=event['method'],
                path=event['path'],
                ip=event['ip'],
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to persist permission audit event')

    app.logger.warning(
        'Permission denied: user_id=%s role=%s endpoint=%s permission=%s method=%s path=%s ip=%s',
        session.get('user_id'),
        session.get('role'),
        request.endpoint,
        permission_key,
        request.method,
        request.path,
        request.remote_addr,
    )


def ensure_permission(permission_key, redirect_endpoint='login'):
    if has_permission(session.get('role'), permission_key):
        return None

    _log_permission_denied(permission_key)
    flash('Bu işlemi gerçekleştirme yetkiniz yok.', 'danger')
    return redirect(url_for(redirect_endpoint))


def ensure_teacher_class_ownership(class_obj, on_fail='login', fail_message=None):
    if class_obj and class_obj.teacher_id == session.get('user_id'):
        return None

    app.logger.warning(
        'Teacher ownership denied: user_id=%s class_id=%s endpoint=%s',
        session.get('user_id'),
        getattr(class_obj, 'id', None),
        request.endpoint,
    )

    if on_fail == 'json':
        return jsonify({'error': 'forbidden'}), 403

    if fail_message:
        flash(fail_message, 'danger')
    return redirect(url_for(on_fail))


def ensure_teacher_session_ownership(session_obj, on_fail='login', fail_message=None):
    if not session_obj:
        return redirect(url_for(on_fail))
    return ensure_teacher_class_ownership(session_obj.class_obj, on_fail=on_fail, fail_message=fail_message)


def ensure_student_class_membership(student_obj, class_obj, on_fail='student_absence', fail_message=None):
    if student_obj and class_obj and class_obj in student_obj.classes:
        return None

    app.logger.warning(
        'Student membership denied: user_id=%s student_id=%s class_id=%s endpoint=%s',
        session.get('user_id'),
        getattr(student_obj, 'id', None),
        getattr(class_obj, 'id', None),
        request.endpoint,
    )

    if fail_message:
        flash(fail_message, 'danger')
    return redirect(url_for(on_fail))


def ensure_student_event_ownership(student_obj, event_obj, on_fail='student_dashboard', fail_message=None):
    if student_obj and event_obj and event_obj.student_id == student_obj.id:
        return None

    app.logger.warning(
        'Student event ownership denied: user_id=%s student_id=%s event_id=%s endpoint=%s',
        session.get('user_id'),
        getattr(student_obj, 'id', None),
        getattr(event_obj, 'id', None),
        request.endpoint,
    )

    if fail_message:
        flash(fail_message, 'warning')
    return redirect(url_for(on_fail))


def ensure_user_calendar_event_ownership(user_obj, event_obj, on_fail='login', fail_message=None):
    if user_obj and event_obj and event_obj.user_id == user_obj.id:
        return None

    app.logger.warning(
        'User calendar event ownership denied: user_id=%s event_id=%s endpoint=%s',
        getattr(user_obj, 'id', None),
        getattr(event_obj, 'id', None),
        request.endpoint,
    )

    if fail_message:
        flash(fail_message, 'warning')
    return redirect(url_for(on_fail))


def _handle_user_calendar_dashboard_post(user_obj, permission_key, redirect_endpoint):
    permission_error = ensure_permission(permission_key, redirect_endpoint)
    if permission_error:
        return permission_error

    action = _normalize_form_text(request.form.get('action'), max_length=40).lower()
    if action not in {'add_calendar_event', 'delete_calendar_event'}:
        flash(_lang_text('Geçersiz panel işlemi.', 'Invalid dashboard action.'), 'warning')
        return redirect(url_for(redirect_endpoint))

    if action == 'add_calendar_event':
        title = (request.form.get('title') or '').strip()
        event_type = (request.form.get('event_type') or 'activity').strip().lower()
        event_date_raw = (request.form.get('event_date') or '').strip()
        note = (request.form.get('note') or '').strip()

        if len(title) > 140:
            flash(_lang_text('Etkinlik başlığı çok uzun.', 'Event title is too long.'), 'warning')
            return redirect(url_for(redirect_endpoint))

        if not title or not event_date_raw:
            flash(_lang_text('Etkinlik başlığı ve tarihi zorunludur.', 'Event title and date are required.'), 'warning')
            return redirect(url_for(redirect_endpoint))

        if event_type not in {'exam', 'activity'}:
            event_type = 'activity'

        try:
            event_date = datetime.datetime.strptime(event_date_raw, '%Y-%m-%d').date()
        except ValueError:
            flash(_lang_text('Geçersiz etkinlik tarihi formatı.', 'Invalid event date format.'), 'warning')
            return redirect(url_for(redirect_endpoint))

        event = UserCalendarEvent(
            user_id=user_obj.id,
            title=title,
            event_type=event_type,
            event_date=event_date,
            note=note[:240] if note else None,
        )
        db.session.add(event)
        db.session.commit()
        flash(_lang_text('Takvim etkinliği eklendi.', 'Calendar event added.'), 'success')
        return redirect(url_for(redirect_endpoint))

    event_id_raw = _normalize_form_text(request.form.get('event_id'), max_length=20)
    if not event_id_raw.isdigit():
        flash(_lang_text('Geçersiz etkinlik kimliği.', 'Invalid event id.'), 'warning')
        return redirect(url_for(redirect_endpoint))

    event = db.session.get(UserCalendarEvent, int(event_id_raw))
    denied = ensure_user_calendar_event_ownership(
        user_obj,
        event,
        on_fail=redirect_endpoint,
        fail_message=_lang_text('Etkinlik bulunamadı.', 'Event not found.'),
    )
    if denied:
        return denied

    db.session.delete(event)
    db.session.commit()
    flash(_lang_text('Takvim etkinliği silindi.', 'Calendar event deleted.'), 'success')
    return redirect(url_for(redirect_endpoint))


def _serialize_user_calendar_events(user_id):
    today = datetime.date.today()
    all_events = UserCalendarEvent.query.filter_by(user_id=user_id).order_by(UserCalendarEvent.event_date.asc()).all()
    upcoming_events = [event for event in all_events if event.event_date >= today][:12]
    serialized_events = [
        {
            'id': event.id,
            'title': event.title,
            'event_type': event.event_type,
            'event_date': event.event_date.isoformat(),
            'note': event.note or '',
        }
        for event in all_events
    ]
    return all_events, upcoming_events, serialized_events


def permission_required(permission_key=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Lütfen önce giriş yapın!', 'danger')
                return redirect(url_for('login', next=request.url))

            role = session.get('role')
            resolved_permission = permission_key or PERMISSION_MAP.get(request.endpoint)
            if has_permission(role, resolved_permission):
                return f(*args, **kwargs)

            _log_permission_denied(resolved_permission)
            if request.endpoint == 'session_stats':
                return jsonify({'error': 'forbidden'}), 403

            flash('Bu işlemi gerçekleştirme yetkiniz yok.', 'danger')
            return redirect(url_for('login'))
        return decorated_function
    return decorator


def validate_admin_role_update(actor_user_id, actor_role, target_user_id, target_user_role, new_role, admin_count):
    allowed_roles = {'student', 'teacher', 'admin'}
    if actor_role != 'admin':
        return 'Only admin can update roles.'
    if new_role not in allowed_roles:
        return 'Invalid target role.'
    if actor_user_id == target_user_id:
        return 'You cannot change your own role.'
    if target_user_role == 'admin' and new_role != 'admin' and admin_count <= 1:
        return 'At least one admin account must remain in the system.'
    return None


def validate_admin_lock_update(actor_user_id, actor_role, target_user_id, target_user_role, target_user_locked, lock_state, unlocked_admin_count):
    if actor_role != 'admin':
        return 'Only admin can update lock status.'
    if actor_user_id == target_user_id and lock_state:
        return 'You cannot lock your own account.'
    if target_user_role == 'admin' and lock_state and not target_user_locked and unlocked_admin_count <= 1:
        return 'At least one unlocked admin account must remain in the system.'
    return None


def validate_admin_teacher_assignment(actor_role, class_obj, teacher_user, current_teacher_id, target_teacher_id):
    if actor_role != 'admin':
        return 'Only admin can assign class teacher.'
    if not class_obj:
        return 'Sınıf bulunamadı.'
    if not teacher_user or teacher_user.role != 'teacher':
        return 'Target teacher user is invalid.'
    if teacher_user.is_locked:
        return 'Locked teacher accounts cannot be assigned.'
    if current_teacher_id == target_teacher_id:
        return 'Class is already assigned to selected teacher.'
    return None


def validate_password_policy(password: str, user_name: str | None = None, user_email: str | None = None):
    if password is None:
        return 'Şifre zorunludur.'

    minimum_length = int(app.config.get('PASSWORD_MIN_LENGTH', 10) or 10)
    if len(password) < minimum_length:
        return f'Password must be at least {minimum_length} characters long.'

    has_upper = any(ch.isupper() for ch in password)
    has_lower = any(ch.islower() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    has_special = any(not ch.isalnum() for ch in password)
    if not (has_upper and has_lower and has_digit and has_special):
        return 'Password must include uppercase, lowercase, digit, and special character.'

    lowered_password = password.lower()
    if user_name and user_name.strip():
        compact_name = ''.join(ch for ch in user_name.strip().lower() if ch.isalnum())
        if compact_name and compact_name in ''.join(ch for ch in lowered_password if ch.isalnum()):
            return 'Password cannot contain your name.'

    if user_email and '@' in user_email:
        local_part = user_email.split('@', 1)[0].strip().lower()
        if local_part and local_part in lowered_password:
            return 'Password cannot contain your email username.'

    return None


def _normalize_form_text(value, max_length: int | None = None) -> str:
    text = (value or '').strip()
    if max_length is not None and len(text) > max_length:
        return text[:max_length]
    return text


def _parse_filter_datetime(raw_value: str | None):
    raw = (raw_value or '').strip()
    if not raw:
        return None
    for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _parse_optional_int(raw_value: str | None):
    raw = (raw_value or '').strip()
    if raw.isdigit():
        return int(raw)
    return None


def _is_valid_email(email: str) -> bool:
    if not email or len(email) > 254:
        return False
    return re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', email) is not None


def _send_email_notification(to_email: str, subject: str, body: str) -> tuple[bool, str | None]:
    email_value = _normalize_form_text(to_email, max_length=254).lower()
    if not _is_valid_email(email_value):
        return False, 'invalid_email'

    if app.config.get('EMAIL_DRY_RUN', True):
        app.logger.info('EMAIL_DRY_RUN to=%s subject=%s', email_value, subject)
        return True, 'dry_run'

    smtp_host = (app.config.get('EMAIL_SMTP_HOST') or '').strip()
    smtp_port = int(app.config.get('EMAIL_SMTP_PORT') or 587)
    smtp_user = (app.config.get('EMAIL_SMTP_USER') or '').strip()
    smtp_password = app.config.get('EMAIL_SMTP_PASSWORD') or ''
    use_tls = bool(app.config.get('EMAIL_USE_TLS', True))
    email_from = (app.config.get('EMAIL_FROM') or '').strip()
    timeout_seconds = int(app.config.get('EMAIL_TIMEOUT_SECONDS') or 10)

    if not smtp_host:
        return False, 'smtp_host_missing'
    if not _is_valid_email(email_from):
        return False, 'invalid_sender_email'

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = email_from
    msg['To'] = email_value
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout_seconds) as smtp:
            if use_tls:
                smtp.starttls()
            if smtp_user:
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)
        return True, None
    except Exception as exc:
        app.logger.exception('Email send failed: to=%s subject=%s', email_value, subject)
        return False, str(exc)


def _log_admin_operation(action, target_user_id, old_value, new_value, status='ok', detail=None):
    try:
        db.session.add(
            AdminOperationLog(
                actor_user_id=session.get('user_id'),
                target_user_id=target_user_id,
                action=action,
                old_value=old_value,
                new_value=new_value,
                status=status,
                detail=detail,
                ip=request.remote_addr,
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to persist admin operation log: action=%s target=%s', action, target_user_id)


@app.route('/set-language', methods=['POST'])
def set_language():
    selected = (request.form.get('lang') or '').strip().lower()
    if selected in LANGUAGES:
        session['lang'] = selected
        flash(_t('language_updated'), 'success')

    next_url = request.form.get('next') or request.referrer or url_for('login')
    if not _is_safe_next_url(next_url):
        next_url = url_for('login')
    return redirect(next_url)

# ------------------ REGISTER ------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    # If already logged in, redirect to the dashboard.
    if 'user_id' in session:
        if session.get('role') == 'student':
            return redirect(url_for('student_dashboard'))
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
        name = _normalize_form_text(request.form.get('name'), max_length=120)
        email = _normalize_form_text(request.form.get('email'), max_length=254).lower()
        password = request.form.get('password') or ''
        role = _normalize_form_text(request.form.get('role'), max_length=20).lower()
        student_number = _normalize_form_text(request.form.get('student_number'), max_length=32)

        if not name:
            flash('Ad alanı zorunludur!', 'danger')
            return redirect(url_for('register'))

        if not _is_valid_email(email):
            flash('Lütfen geçerli bir e-posta adresi girin.', 'danger')
            return redirect(url_for('register'))

        if role not in {'student', 'teacher'}:
            flash('Geçersiz rol seçimi.', 'danger')
            return redirect(url_for('register'))

        password_error = validate_password_policy(password, user_name=name, user_email=email)
        if password_error:
            flash(password_error, 'danger')
            return redirect(url_for('register'))

        if role == 'student' and not student_number:
            flash('Öğrenci numarası zorunludur!', 'danger')
            return redirect(url_for('register'))

        if student_number and not re.match(r'^[A-Za-z0-9_-]+$', student_number):
            flash('Öğrenci numarası geçersiz karakterler içeriyor.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Bu e-posta adresi zaten kayıtlı!', 'danger')
            return redirect(url_for('register'))

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Create student profile for student role.
        if role == 'student':
            name_parts = [part for part in name.strip().split(' ') if part]
            first_name = name_parts[0] if name_parts else None
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else None
            student = Student(
                id=user.id,
                student_number=student_number,
                first_name=first_name,
                last_name=last_name,
            )
            db.session.add(student)
            db.session.commit()

        # Auto-login after registration.
        session['user_id'] = user.id
        session['role'] = user.role

        flash('Kayıt başarılı! Hoş geldiniz.', 'success')
        if user.role == 'student':
            return redirect(url_for('student_dashboard'))
        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('teacher_dashboard'))

    return render_template('register.html')

# ------------------ LOGIN ------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next') or request.form.get('next')

    # If already logged in, redirect to the dashboard.
    if 'user_id' in session:
        if _is_safe_next_url(next_url):
            return redirect(next_url)
        if session.get('role') == 'student':
            return redirect(url_for('student_dashboard'))
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('teacher_dashboard'))

    if request.method == 'POST':
        email = _normalize_form_text(request.form.get('email'), max_length=254).lower()
        password = request.form.get('password') or ''
        remember_me = request.form.get('remember_me') == 'on'

        if not email or not password:
            flash('E-posta veya şifre hatalı!', 'danger')
            return redirect(url_for('login', next=next_url) if next_url else url_for('login'))

        if not _is_valid_email(email):
            flash('E-posta veya şifre hatalı!', 'danger')
            return redirect(url_for('login', next=next_url) if next_url else url_for('login'))

        rate_key = f"{(request.remote_addr or 'unknown').strip()}:{email.strip().lower()}"
        if _is_rate_limited(
            'login',
            rate_key,
            app.config['LOGIN_RATE_LIMIT_MAX_ATTEMPTS'],
            app.config['LOGIN_RATE_LIMIT_WINDOW_SECONDS'],
        ):
            flash('Çok fazla giriş denemesi. Lütfen bekleyip tekrar deneyin.', 'danger')
            return redirect(url_for('login', next=next_url) if next_url else url_for('login'))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if user.is_locked:
                flash('Hesabınız kilitlenmiş. Lütfen bir yönetici ile iletişime geçin.', 'danger')
                return redirect(url_for('login', next=next_url) if next_url else url_for('login'))

            # Reset previous session data before establishing a new login session.
            lang = _get_language()
            session.clear()
            session['lang'] = lang
            session['user_id'] = user.id
            session['role'] = user.role
            session.permanent = remember_me
            RATE_LIMIT_EVENTS.pop(f"login:{rate_key}", None)
            _clear_login_failure_history(email)
            flash('Giriş başarılı!', 'success')
            if _is_safe_next_url(next_url):
                return redirect(next_url)
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:  # teacher
                return redirect(url_for('teacher_dashboard'))

        if _record_login_failure_and_lock(user, email):
            flash('Hesabınız kilitlenmiş. Lütfen bir yönetici ile iletişime geçin.', 'danger')
            return redirect(url_for('login', next=next_url) if next_url else url_for('login'))

        flash('E-posta veya şifre hatalı!', 'danger')
        return redirect(url_for('login', next=next_url) if next_url else url_for('login'))

    return render_template('login.html', next_url=next_url)

# ------------------ LOGOUT ------------------
@app.route('/logout')
def logout():
    lang = _get_language()
    session.clear()
    session['lang'] = lang
    flash('Çıkış yapıldı.', 'success')
    return redirect(url_for('login'))


@app.route('/admin/dashboard', methods=['GET', 'POST'])
@role_required('admin')
@permission_required()
def admin_dashboard():
    admin_user = db.session.get(User, session['user_id'])
    if request.method == 'POST':
        return _handle_user_calendar_dashboard_post(admin_user, PERMISSIONS['ADMIN_DASHBOARD_CALENDAR_UPDATE'], 'admin_dashboard')

    teacher_count = User.query.filter_by(role='teacher').count()
    student_count = User.query.filter_by(role='student').count()
    class_count = Class.query.count()
    active_session_count = AttendanceSession.query.filter_by(active=True).count()

    try:
        persisted_audit_count = PermissionAuditLog.query.count()
    except Exception:
        db.session.rollback()
        persisted_audit_count = 0

    # Weather
    weather_city = (request.args.get('city') or session.get('weather_city') or 'Lefkosa').strip()
    lat_arg = (request.args.get('lat') or '').strip()
    lon_arg = (request.args.get('lon') or '').strip()
    weather_lat = session.get('weather_lat')
    weather_lon = session.get('weather_lon')

    if lat_arg and lon_arg:
        try:
            parsed_lat = float(lat_arg)
            parsed_lon = float(lon_arg)
            if -90 <= parsed_lat <= 90 and -180 <= parsed_lon <= 180:
                weather_lat = parsed_lat
                weather_lon = parsed_lon
                session['weather_lat'] = parsed_lat
                session['weather_lon'] = parsed_lon
        except ValueError:
            pass

    if request.args.get('city'):
        session['weather_city'] = weather_city
        weather_lat = None
        weather_lon = None

    if weather_lat is not None and weather_lon is not None:
        weather = _fetch_weather(lat=float(weather_lat), lon=float(weather_lon))
    else:
        weather = _fetch_weather(city=weather_city)

    _, admin_upcoming_events, admin_calendar_events = _serialize_user_calendar_events(admin_user.id) if admin_user else ([], [], [])
    stats = {
        'teacher_count': teacher_count,
        'student_count': student_count,
        'class_count': class_count,
        'active_session_count': active_session_count,
        'permission_denied_total': persisted_audit_count + len(PERMISSION_AUDIT_EVENTS),
        'calendar_total_count': len(admin_calendar_events),
        'upcoming_events_count': len(admin_upcoming_events),
    }
    return render_template(
        'admin_dashboard.html',
        stats=stats,
        weather=weather,
        weather_using_location=bool(weather and weather.get('source') == 'location'),
        admin_name=admin_user.name if admin_user else 'Admin',
        calendar_events=admin_calendar_events,
        upcoming_event_count=len(admin_upcoming_events),
    )


@app.route('/admin/class-assignments')
@role_required('admin')
@permission_required()
def admin_class_assignments():
    q = (request.args.get('q') or '').strip()
    limit_raw = (request.args.get('limit') or '200').strip()
    limit = int(limit_raw) if limit_raw.isdigit() else 200
    limit = max(1, min(limit, 1000))

    class_query = Class.query
    if q:
        class_query = class_query.filter(Class.name.ilike(f"%{q}%"))

    classes = class_query.order_by(Class.id.asc()).limit(limit).all()
    teachers = User.query.filter_by(role='teacher').order_by(User.name.asc(), User.id.asc()).all()

    class_rows = []
    for class_obj in classes:
        teacher_user = db.session.get(User, class_obj.teacher_id)
        class_rows.append(
            {
                'id': class_obj.id,
                'name': class_obj.name,
                'teacher_id': class_obj.teacher_id,
                'teacher_name': teacher_user.name if teacher_user else 'Unknown',
                'teacher_email': teacher_user.email if teacher_user else '-',
            }
        )

    teacher_options = [
        {
            'id': teacher.id,
            'name': teacher.name,
            'email': teacher.email,
            'is_locked': bool(teacher.is_locked),
        }
        for teacher in teachers
    ]

    summary = {
        'total_loaded_classes': len(class_rows),
        'total_teachers': len(teachers),
        'active_teachers': sum(1 for teacher in teachers if not teacher.is_locked),
        'locked_teachers': sum(1 for teacher in teachers if teacher.is_locked),
    }

    return render_template(
        'admin_class_assignments.html',
        classes=class_rows,
        teachers=teacher_options,
        summary=summary,
        filters={'q': q, 'limit': limit},
    )


@app.route('/admin/users')
@role_required('admin')
@permission_required()
def admin_user_inventory():
    role_filter = (request.args.get('role') or '').strip().lower()
    query_text = (request.args.get('q') or '').strip()
    limit_raw = (request.args.get('limit') or '200').strip()
    limit = int(limit_raw) if limit_raw.isdigit() else 200
    limit = max(1, min(limit, 1000))

    query = User.query
    if role_filter in ('student', 'teacher', 'admin'):
        query = query.filter(User.role == role_filter)
    if query_text:
        query = query.filter(
            (User.name.ilike(f"%{query_text}%")) |
            (User.email.ilike(f"%{query_text}%"))
        )

    users = query.order_by(User.id.asc()).limit(limit).all()
    user_rows = []
    for user in users:
        teacher_class_count = len(user.teacher_classes) if user.role == 'teacher' else 0
        student_profile_exists = bool(user.students) if user.role == 'student' else False
        user_rows.append({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'is_locked': bool(user.is_locked),
            'teacher_class_count': teacher_class_count,
            'student_profile_exists': student_profile_exists,
        })

    summary = {
        'total_loaded': len(user_rows),
        'teacher_count': sum(1 for u in user_rows if u['role'] == 'teacher'),
        'student_count': sum(1 for u in user_rows if u['role'] == 'student'),
        'admin_count': sum(1 for u in user_rows if u['role'] == 'admin'),
    }

    filters = {
        'role': role_filter,
        'q': query_text,
        'limit': limit,
    }
    return render_template(
        'admin_user_inventory.html',
        users=user_rows,
        filters=filters,
        summary=summary,
        role_options=('student', 'teacher', 'admin'),
        current_admin_user_id=session.get('user_id'),
    )


@app.route('/admin/users/<int:user_id>/role', methods=['POST'])
@role_required('admin')
@permission_required()
@csrf_protect
@rate_limit_protect('admin_mutation', 'ADMIN_MUTATION_RATE_LIMIT_MAX', 'ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS', _admin_mutation_rate_key)
def admin_update_user_role(user_id):
    target_user = db.session.get(User, user_id)
    if not target_user:
        flash('Hedef kullanıcı bulunamadı.', 'warning')
        return redirect(url_for('admin_user_inventory'))

    new_role = (request.form.get('role') or '').strip().lower()
    actor_user_id = session.get('user_id')
    actor_role = session.get('role')
    old_role = (target_user.role or '').strip().lower()
    admin_count = User.query.filter_by(role='admin').count()

    validation_error = validate_admin_role_update(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        target_user_id=target_user.id,
        target_user_role=old_role,
        new_role=new_role,
        admin_count=admin_count,
    )
    if validation_error:
        _log_admin_operation(
            action='role_update',
            target_user_id=target_user.id,
            old_value=old_role,
            new_value=new_role,
            status='rejected',
            detail=validation_error,
        )
        flash(validation_error, 'danger')
        return redirect(url_for('admin_user_inventory'))

    if old_role == new_role:
        _log_admin_operation(
            action='role_update',
            target_user_id=target_user.id,
            old_value=old_role,
            new_value=new_role,
            status='noop',
            detail='Role is already set to requested value.',
        )
        flash('Rol zaten bu değere ayarlı.', 'info')
        return redirect(url_for('admin_user_inventory'))

    target_user.role = new_role
    if new_role == 'student' and not target_user.students:
        auto_number = f'AUTO-{target_user.id:05d}'
        name_parts = [part for part in (target_user.name or '').strip().split(' ') if part]
        first_name = name_parts[0] if name_parts else None
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else None
        db.session.add(
            Student(
                id=target_user.id,
                student_number=auto_number,
                first_name=first_name,
                last_name=last_name,
            )
        )

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        _log_admin_operation(
            action='role_update',
            target_user_id=target_user.id,
            old_value=old_role,
            new_value=new_role,
            status='error',
            detail='Database commit failed.',
        )
        flash('Rol güncelleme başarısız (veritabanı hatası).', 'danger')
        return redirect(url_for('admin_user_inventory'))

    _log_admin_operation(
        action='role_update',
        target_user_id=target_user.id,
        old_value=old_role,
        new_value=new_role,
        status='updated',
        detail='Role updated successfully.',
    )
    flash(f'Role updated: {old_role} -> {new_role}', 'success')
    return redirect(url_for('admin_user_inventory'))


@app.route('/admin/users/<int:user_id>/lock', methods=['POST'])
@role_required('admin')
@permission_required()
@csrf_protect
@rate_limit_protect('admin_mutation', 'ADMIN_MUTATION_RATE_LIMIT_MAX', 'ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS', _admin_mutation_rate_key)
def admin_toggle_user_lock(user_id):
    target_user = db.session.get(User, user_id)
    if not target_user:
        flash('Hedef kullanıcı bulunamadı.', 'warning')
        return redirect(url_for('admin_user_inventory'))

    action = (request.form.get('action') or '').strip().lower()
    if action not in {'lock', 'unlock'}:
        flash('Geçersiz kilit işlemi.', 'danger')
        return redirect(url_for('admin_user_inventory'))

    lock_state = action == 'lock'
    actor_user_id = session.get('user_id')
    actor_role = session.get('role')
    target_locked = bool(target_user.is_locked)
    unlocked_admin_count = User.query.filter_by(role='admin', is_locked=False).count()

    validation_error = validate_admin_lock_update(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        target_user_id=target_user.id,
        target_user_role=(target_user.role or '').strip().lower(),
        target_user_locked=target_locked,
        lock_state=lock_state,
        unlocked_admin_count=unlocked_admin_count,
    )
    if validation_error:
        _log_admin_operation(
            action='account_lock_toggle',
            target_user_id=target_user.id,
            old_value='locked' if target_locked else 'active',
            new_value='locked' if lock_state else 'active',
            status='rejected',
            detail=validation_error,
        )
        flash(validation_error, 'danger')
        return redirect(url_for('admin_user_inventory'))

    if target_locked == lock_state:
        _log_admin_operation(
            action='account_lock_toggle',
            target_user_id=target_user.id,
            old_value='locked' if target_locked else 'active',
            new_value='locked' if lock_state else 'active',
            status='noop',
            detail='Lock status is already set to requested value.',
        )
        flash('Kilit durumu zaten bu değere ayarlı.', 'info')
        return redirect(url_for('admin_user_inventory'))

    target_user.is_locked = lock_state
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        _log_admin_operation(
            action='account_lock_toggle',
            target_user_id=target_user.id,
            old_value='locked' if target_locked else 'active',
            new_value='locked' if lock_state else 'active',
            status='error',
            detail='Database commit failed.',
        )
        flash('Kilit güncelleme başarısız (veritabanı hatası).', 'danger')
        return redirect(url_for('admin_user_inventory'))

    _log_admin_operation(
        action='account_lock_toggle',
        target_user_id=target_user.id,
        old_value='locked' if target_locked else 'active',
        new_value='locked' if lock_state else 'active',
        status='updated',
        detail='Account lock status updated successfully.',
    )
    flash('Hesap kilit durumu güncellendi.', 'success')
    return redirect(url_for('admin_user_inventory'))


@app.route('/admin/users/<int:user_id>/password', methods=['POST'])
@role_required('admin')
@permission_required()
@csrf_protect
@rate_limit_protect('admin_mutation', 'ADMIN_MUTATION_RATE_LIMIT_MAX', 'ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS', _admin_mutation_rate_key)
def admin_reset_user_password(user_id):
    target_user = db.session.get(User, user_id)
    if not target_user:
        flash('Hedef kullanıcı bulunamadı.', 'warning')
        return redirect(url_for('admin_user_inventory'))

    actor_user_id = session.get('user_id')
    if actor_user_id == target_user.id:
        flash('Kendi şifrenizi bu panelden sıfırlayamazsınız.', 'danger')
        return redirect(url_for('admin_user_inventory'))

    new_password = request.form.get('new_password') or ''
    confirm_password = request.form.get('confirm_password') or ''
    if not new_password or not confirm_password:
        flash('Her iki şifre alanı da zorunludur.', 'warning')
        return redirect(url_for('admin_user_inventory'))
    if new_password != confirm_password:
        flash('Şifre onayı eşleşmiyor.', 'warning')
        return redirect(url_for('admin_user_inventory'))

    policy_error = validate_password_policy(new_password, user_name=target_user.name, user_email=target_user.email)
    if policy_error:
        _log_admin_operation(
            action='password_reset',
            target_user_id=target_user.id,
            old_value='set',
            new_value='set',
            status='rejected',
            detail=policy_error,
        )
        flash(policy_error, 'danger')
        return redirect(url_for('admin_user_inventory'))

    target_user.set_password(new_password)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        _log_admin_operation(
            action='password_reset',
            target_user_id=target_user.id,
            old_value='set',
            new_value='set',
            status='error',
            detail='Database commit failed.',
        )
        flash('Şifre sıfırlama başarısız (veritabanı hatası).', 'danger')
        return redirect(url_for('admin_user_inventory'))

    _log_admin_operation(
        action='password_reset',
        target_user_id=target_user.id,
        old_value='set',
        new_value='set',
        status='updated',
        detail='Password reset by admin.',
    )
    flash(f'Kullanıcı #{target_user.id} için şifre sıfırlandı.', 'success')
    return redirect(url_for('admin_user_inventory'))


@app.route('/admin/classes/<int:class_id>/assign-teacher', methods=['POST'])
@role_required('admin')
@permission_required()
@csrf_protect
@rate_limit_protect('admin_mutation', 'ADMIN_MUTATION_RATE_LIMIT_MAX', 'ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS', _admin_mutation_rate_key)
def admin_assign_class_teacher(class_id):
    class_obj = db.session.get(Class, class_id)
    teacher_id_raw = (request.form.get('teacher_id') or '').strip()
    if not teacher_id_raw.isdigit():
        flash('Geçersiz öğretmen kimliği.', 'danger')
        return redirect(url_for('admin_class_assignments'))

    target_teacher_id = int(teacher_id_raw)
    teacher_user = db.session.get(User, target_teacher_id)
    current_teacher_id = class_obj.teacher_id if class_obj else None

    validation_error = validate_admin_teacher_assignment(
        actor_role=session.get('role'),
        class_obj=class_obj,
        teacher_user=teacher_user,
        current_teacher_id=current_teacher_id,
        target_teacher_id=target_teacher_id,
    )
    if validation_error:
        _log_admin_operation(
            action='class_teacher_assign',
            target_user_id=target_teacher_id if teacher_user else session.get('user_id'),
            old_value=str(current_teacher_id) if current_teacher_id is not None else None,
            new_value=str(target_teacher_id),
            status='rejected',
            detail=validation_error,
        )
        flash(validation_error, 'danger')
        return redirect(url_for('admin_class_assignments'))

    class_obj.teacher_id = target_teacher_id
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        _log_admin_operation(
            action='class_teacher_assign',
            target_user_id=target_teacher_id,
            old_value=str(current_teacher_id),
            new_value=str(target_teacher_id),
            status='error',
            detail=f'Database commit failed for class_id={class_obj.id}.',
        )
        flash('Öğretmen ataması başarısız (veritabanı hatası).', 'danger')
        return redirect(url_for('admin_class_assignments'))

    _log_admin_operation(
        action='class_teacher_assign',
        target_user_id=target_teacher_id,
        old_value=str(current_teacher_id),
        new_value=str(target_teacher_id),
        status='updated',
        detail=f'Class teacher updated for class_id={class_obj.id}.',
    )
    flash('Sınıf öğretmeni güncellendi.', 'success')
    return redirect(url_for('admin_class_assignments'))


@app.route('/admin/security/permission-audit')
@role_required('admin')
@permission_required()
def admin_permission_audit_report():
    limit_raw = (request.args.get('limit') or '100').strip()
    limit = int(limit_raw) if limit_raw.isdigit() else 100
    limit = max(1, min(limit, MAX_PERMISSION_AUDIT_EVENTS))

    role_filter = (request.args.get('role') or '').strip().lower()
    endpoint_filter = (request.args.get('endpoint') or '').strip().lower()
    permission_filter = (request.args.get('permission') or '').strip().lower()
    from_raw = (request.args.get('from') or '').strip()
    to_raw = (request.args.get('to') or '').strip()

    from_dt = _parse_filter_datetime(from_raw)
    to_dt = _parse_filter_datetime(to_raw)

    events = []
    source = 'database'
    try:
        query = PermissionAuditLog.query
        if role_filter:
            query = query.filter(PermissionAuditLog.role.ilike(f"%{role_filter}%"))
        if endpoint_filter:
            query = query.filter(PermissionAuditLog.endpoint.ilike(f"%{endpoint_filter}%"))
        if permission_filter:
            query = query.filter(PermissionAuditLog.permission.ilike(f"%{permission_filter}%"))
        if from_dt:
            query = query.filter(PermissionAuditLog.created_at >= from_dt)
        if to_dt:
            query = query.filter(PermissionAuditLog.created_at <= to_dt)

        rows = query.order_by(PermissionAuditLog.created_at.desc()).limit(limit).all()
        events = [
            {
                'timestamp': f"{row.created_at.isoformat()}Z" if row.created_at else '-',
                'user_id': row.user_id,
                'role': row.role,
                'endpoint': row.endpoint,
                'permission': row.permission,
                'method': row.method,
                'path': row.path,
                'ip': row.ip,
            }
            for row in rows
        ]
    except Exception:
        db.session.rollback()
        source = 'buffer'
        buffer_events = list(PERMISSION_AUDIT_EVENTS)

        def _buffer_matches(event):
            event_role = (event.get('role') or '').lower()
            event_endpoint = (event.get('endpoint') or '').lower()
            event_permission = (event.get('permission') or '').lower()

            if role_filter and role_filter not in event_role:
                return False
            if endpoint_filter and endpoint_filter not in event_endpoint:
                return False
            if permission_filter and permission_filter not in event_permission:
                return False

            timestamp_raw = (event.get('timestamp') or '').replace('Z', '')
            event_time = None
            try:
                event_time = datetime.datetime.fromisoformat(timestamp_raw)
            except ValueError:
                event_time = None

            if from_dt and event_time and event_time < from_dt:
                return False
            if to_dt and event_time and event_time > to_dt:
                return False
            return True

        events = [event for event in buffer_events if _buffer_matches(event)][:limit]

    filters = {
        'role': role_filter,
        'endpoint': endpoint_filter,
        'permission': permission_filter,
        'from': from_raw,
        'to': to_raw,
    }
    return render_template('admin_permission_audit.html', events=events, limit=limit, source=source, filters=filters)


@app.route('/admin/security/admin-operations')
@role_required('admin')
@permission_required()
def admin_operation_audit_report():
    limit_raw = (request.args.get('limit') or '100').strip()
    limit = int(limit_raw) if limit_raw.isdigit() else 100
    limit = max(1, min(limit, 500))

    action_filter = (request.args.get('action') or '').strip().lower()
    status_filter = (request.args.get('status') or '').strip().lower()
    actor_filter_raw = (request.args.get('actor_user_id') or '').strip()
    target_filter_raw = (request.args.get('target_user_id') or '').strip()
    from_raw = (request.args.get('from') or '').strip()
    to_raw = (request.args.get('to') or '').strip()

    actor_user_id = _parse_optional_int(actor_filter_raw)
    target_user_id = _parse_optional_int(target_filter_raw)
    from_dt = _parse_filter_datetime(from_raw)
    to_dt = _parse_filter_datetime(to_raw)

    query = AdminOperationLog.query
    if action_filter:
        query = query.filter(AdminOperationLog.action.ilike(f"%{action_filter}%"))
    if status_filter:
        query = query.filter(AdminOperationLog.status.ilike(f"%{status_filter}%"))
    if actor_user_id is not None:
        query = query.filter(AdminOperationLog.actor_user_id == actor_user_id)
    if target_user_id is not None:
        query = query.filter(AdminOperationLog.target_user_id == target_user_id)
    if from_dt:
        query = query.filter(AdminOperationLog.created_at >= from_dt)
    if to_dt:
        query = query.filter(AdminOperationLog.created_at <= to_dt)

    rows = query.order_by(AdminOperationLog.created_at.desc()).limit(limit).all()
    events = []
    for row in rows:
        actor_user = db.session.get(User, row.actor_user_id)
        target_user = db.session.get(User, row.target_user_id)
        events.append(
            {
                'timestamp': f"{row.created_at.isoformat()}Z" if row.created_at else '-',
                'action': row.action,
                'status': row.status,
                'actor_user_id': row.actor_user_id,
                'actor_user_email': actor_user.email if actor_user else '-',
                'target_user_id': row.target_user_id,
                'target_user_email': target_user.email if target_user else '-',
                'old_value': row.old_value,
                'new_value': row.new_value,
                'detail': row.detail,
                'ip': row.ip,
            }
        )

    filters = {
        'action': action_filter,
        'status': status_filter,
        'actor_user_id': actor_filter_raw,
        'target_user_id': target_filter_raw,
        'from': from_raw,
        'to': to_raw,
    }
    summary = {
        'loaded_events': len(events),
        'updated_count': sum(1 for event in events if event['status'] == 'updated'),
        'rejected_count': sum(1 for event in events if event['status'] == 'rejected'),
        'error_count': sum(1 for event in events if event['status'] == 'error'),
    }
    return render_template('admin_operation_audit.html', events=events, limit=limit, filters=filters, summary=summary)


@app.route('/health')
def health_check():
    snapshot = _build_health_snapshot()
    status_code = 200 if snapshot['status'] in {'healthy', 'degraded'} else 503
    return jsonify(snapshot), status_code


@app.route('/admin/security/health-status')
@role_required('admin')
@permission_required(PERMISSIONS['ADMIN_METRICS_READ'])
def admin_health_status_report():
    snapshot = _build_health_snapshot()
    return render_template('admin_health_status.html', health=snapshot)


@app.route('/admin/security/permission-matrix')
@role_required('admin')
@permission_required()
def admin_permission_matrix():
    all_permissions = sorted(set(PERMISSIONS.values()))
    matrix_rows = []
    for role in sorted(ROLE_PERMISSIONS.keys()):
        assigned = set(ROLE_PERMISSIONS.get(role, set()))
        matrix_rows.append(
            {
                'role': role,
                'permission_count': len(assigned),
                'permissions': [
                    {
                        'name': perm,
                        'enabled': perm in assigned,
                    }
                    for perm in all_permissions
                ],
            }
        )

    return render_template(
        'admin_permission_matrix.html',
        rows=matrix_rows,
        permissions=all_permissions,
        endpoint_map=sorted(PERMISSION_MAP.items()),
    )


@app.route('/admin/notifications', methods=['GET', 'POST'])
@role_required('admin')
@permission_required()
@csrf_protect
@rate_limit_protect('admin_mutation', 'ADMIN_MUTATION_RATE_LIMIT_MAX', 'ADMIN_MUTATION_RATE_LIMIT_WINDOW_SECONDS', _admin_mutation_rate_key)
def admin_notifications():
    admin_user = db.session.get(User, session.get('user_id'))
    target_role = _normalize_form_text(
        request.form.get('target_role') if request.method == 'POST' else request.args.get('target_role'),
        max_length=20,
    ).lower()
    if target_role not in {'all', 'student', 'teacher', 'admin'}:
        target_role = 'all'

    users_query = User.query
    if target_role != 'all':
        users_query = users_query.filter_by(role=target_role)
    users = users_query.order_by(User.id.asc()).all()
    invalid_emails = [u.email for u in users if not _is_valid_email((u.email or '').strip().lower())]

    stats = {
        'selected_role': target_role,
        'selected_user_count': len(users),
        'invalid_email_count': len(invalid_emails),
        'sample_invalid_emails': invalid_emails[:10],
        'dry_run': bool(app.config.get('EMAIL_DRY_RUN', True)),
    }
    courses = Course.query.order_by(Course.code.asc()).limit(500).all()
    recent_announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(8).all()

    if request.method == 'POST':
        action = _normalize_form_text(request.form.get('action'), max_length=30).lower()
        subject = _normalize_form_text(request.form.get('subject'), max_length=150)
        body = _normalize_form_text(request.form.get('body'), max_length=2000)
        test_email = _normalize_form_text(request.form.get('test_email'), max_length=254).lower()
        limit_raw = _normalize_form_text(request.form.get('max_recipients'), max_length=10)
        max_recipients = int(limit_raw) if limit_raw.isdigit() else 200
        max_recipients = max(1, min(max_recipients, 2000))

        def _render_admin_notifications():
            return render_template(
                'admin_notifications.html',
                stats=stats,
                recent_announcements=recent_announcements,
                courses=courses,
            )

        def _parse_dt_local(raw_value: str):
            raw_value = (raw_value or '').strip()
            if not raw_value:
                return None
            try:
                return datetime.datetime.fromisoformat(raw_value)
            except ValueError:
                return None

        def _normalize_announcement_payload():
            announcement_title = _normalize_form_text(request.form.get('announcement_title'), max_length=150)
            announcement_body = _normalize_form_text(request.form.get('announcement_body'), max_length=2000)
            announcement_target_role = _normalize_form_text(request.form.get('announcement_target_role'), max_length=20).lower()
            announcement_course_id_raw = _normalize_form_text(request.form.get('announcement_course_id'), max_length=20)
            announcement_starts_at = _parse_dt_local(request.form.get('announcement_starts_at') or '')
            announcement_ends_at = _parse_dt_local(request.form.get('announcement_ends_at') or '')
            announcement_course = None
            if announcement_target_role not in {'all', 'student', 'teacher', 'admin'}:
                announcement_target_role = 'all'
            if announcement_course_id_raw and announcement_course_id_raw.isdigit():
                announcement_course = db.session.get(Course, int(announcement_course_id_raw))
            return {
                'title': announcement_title,
                'body': announcement_body,
                'target_role': announcement_target_role,
                'course': announcement_course,
                'starts_at': announcement_starts_at,
                'ends_at': announcement_ends_at,
            }

        if action == 'publish_announcement':
            payload = _normalize_announcement_payload()

            if not payload['title'] or not payload['body']:
                flash(_lang_text('Duyuru başlığı ve içeriği zorunludur.', 'Announcement title and body are required.'), 'warning')
                return _render_admin_notifications()
            if payload['ends_at'] and payload['starts_at'] and payload['ends_at'] < payload['starts_at']:
                flash(_lang_text('Bitiş zamanı başlangıç zamanından önce olamaz.', 'End time cannot be earlier than start time.'), 'warning')
                return _render_admin_notifications()

            try:
                db.session.add(Announcement(
                    title=payload['title'],
                    body=payload['body'],
                    author_id=admin_user.id if admin_user else session.get('user_id'),
                    target_role=payload['target_role'],
                    course_id=payload['course'].id if payload['course'] else None,
                    starts_at=payload['starts_at'],
                    ends_at=payload['ends_at'],
                ))
                db.session.commit()
                flash(_lang_text('Duyuru başarıyla yayınlandı.', 'Announcement published successfully.'), 'success')
            except Exception:
                db.session.rollback()
                flash(_lang_text('Duyuru yayınlanırken hata oluştu.', 'Failed to publish announcement.'), 'danger')

            recent_announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(8).all()
            return _render_admin_notifications()

        if action == 'update_announcement':
            announcement_id_raw = _normalize_form_text(request.form.get('announcement_id'), max_length=20)
            if not announcement_id_raw.isdigit():
                flash(_lang_text('Geçersiz duyuru kaydı.', 'Invalid announcement record.'), 'warning')
                return _render_admin_notifications()

            announcement = db.session.get(Announcement, int(announcement_id_raw))
            if not announcement:
                flash(_lang_text('Duyuru bulunamadı.', 'Announcement not found.'), 'warning')
                return _render_admin_notifications()

            payload = _normalize_announcement_payload()
            if not payload['title'] or not payload['body']:
                flash(_lang_text('Duyuru başlığı ve içeriği zorunludur.', 'Announcement title and body are required.'), 'warning')
                return _render_admin_notifications()
            if payload['ends_at'] and payload['starts_at'] and payload['ends_at'] < payload['starts_at']:
                flash(_lang_text('Bitiş zamanı başlangıç zamanından önce olamaz.', 'End time cannot be earlier than start time.'), 'warning')
                return _render_admin_notifications()

            try:
                announcement.title = payload['title']
                announcement.body = payload['body']
                announcement.target_role = payload['target_role']
                announcement.course_id = payload['course'].id if payload['course'] else None
                announcement.starts_at = payload['starts_at']
                announcement.ends_at = payload['ends_at']
                db.session.commit()
                flash(_lang_text('Duyuru güncellendi.', 'Announcement updated.'), 'success')
            except Exception:
                db.session.rollback()
                flash(_lang_text('Duyuru güncellenirken hata oluştu.', 'Failed to update announcement.'), 'danger')

            recent_announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(8).all()
            return _render_admin_notifications()

        if action == 'delete_announcement':
            announcement_id_raw = _normalize_form_text(request.form.get('announcement_id'), max_length=20)
            if not announcement_id_raw.isdigit():
                flash(_lang_text('Geçersiz duyuru kaydı.', 'Invalid announcement record.'), 'warning')
                return _render_admin_notifications()

            announcement = db.session.get(Announcement, int(announcement_id_raw))
            if not announcement:
                flash(_lang_text('Duyuru bulunamadı.', 'Announcement not found.'), 'warning')
                return _render_admin_notifications()

            try:
                db.session.delete(announcement)
                db.session.commit()
                flash(_lang_text('Duyuru silindi.', 'Announcement deleted.'), 'success')
            except Exception:
                db.session.rollback()
                flash(_lang_text('Duyuru silinirken hata oluştu.', 'Failed to delete announcement.'), 'danger')

            recent_announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(8).all()
            return _render_admin_notifications()

        if action == 'send_test':
            if not _is_valid_email(test_email):
                flash('Lütfen geçerli bir test e-posta adresi girin.', 'danger')
                return _render_admin_notifications()
            if not subject or not body:
                flash('Test e-postası için konu ve içerik zorunludur.', 'warning')
                return _render_admin_notifications()

            ok, reason = _send_email_notification(test_email, subject, body)
            if ok:
                flash('Test e-postası başarıyla gönderildi.' if reason != 'dry_run' else 'Test e-postası kuru çalıştırma modunda doğrulandı.', 'success')
            else:
                flash(f'Test email failed: {reason}', 'danger')
            return _render_admin_notifications()

        if action != 'send_broadcast':
            flash('Geçersiz bildirim işlemi.', 'warning')
            return _render_admin_notifications()

        if not subject or not body:
            flash('Toplu gönderim için konu ve içerik zorunludur.', 'warning')
            return _render_admin_notifications()

        recipients = users[:max_recipients]
        sent_count = 0
        failed_count = 0
        invalid_count = 0

        for user in recipients:
            recipient = (user.email or '').strip().lower()
            if not _is_valid_email(recipient):
                invalid_count += 1
                continue
            ok, _ = _send_email_notification(recipient, subject, body)
            if ok:
                sent_count += 1
            else:
                failed_count += 1

        flash(
            f'Notification completed. Sent={sent_count}, Failed={failed_count}, Invalid Emails={invalid_count}, Targeted={len(recipients)}.',
            'success' if failed_count == 0 else 'warning',
        )

    return render_template('admin_notifications.html', stats=stats, recent_announcements=recent_announcements, courses=courses)

# ------------------ TEACHER DASHBOARD ------------------
def _build_teacher_dashboard_context(user: User):
    _auto_finalize_expired_sessions()

    teacher_classes = Class.query.filter_by(teacher_id=user.id).all()

    class_ids = [cls.id for cls in teacher_classes]
    active_session_by_class = {}
    confirmed_sessions_by_class = defaultdict(list)
    student_counts = {}
    records_by_session = defaultdict(list)
    live_present_counts = {}

    if class_ids:
        active_sessions = (
            AttendanceSession.query
            .filter(AttendanceSession.class_id.in_(class_ids), AttendanceSession.active.is_(True))
            .order_by(AttendanceSession.class_id.asc(), AttendanceSession.date.desc())
            .all()
        )
        for sess in active_sessions:
            active_session_by_class.setdefault(sess.class_id, sess)

        confirmed_sessions = (
            AttendanceSession.query
            .filter(AttendanceSession.class_id.in_(class_ids), AttendanceSession.confirmed.is_(True))
            .order_by(AttendanceSession.class_id.asc(), AttendanceSession.date.desc())
            .all()
        )
        for sess in confirmed_sessions:
            confirmed_sessions_by_class[sess.class_id].append(sess)

        student_count_rows = (
            db.session.query(Class.id, func.count(Student.id))
            .outerjoin(Class.students)
            .filter(Class.id.in_(class_ids))
            .group_by(Class.id)
            .all()
        )
        student_counts = {class_id: count for class_id, count in student_count_rows}

        active_session_ids = [sess.id for sess in active_session_by_class.values()]
        if active_session_ids:
            present_rows = (
                db.session.query(AttendanceRecord.session_id, func.count(AttendanceRecord.id))
                .filter(AttendanceRecord.session_id.in_(active_session_ids), AttendanceRecord.present.is_(True))
                .group_by(AttendanceRecord.session_id)
                .all()
            )
            live_present_counts = {session_id: count for session_id, count in present_rows}

            session_records = AttendanceRecord.query.filter(AttendanceRecord.session_id.in_(active_session_ids)).all()
            for record in session_records:
                records_by_session[record.session_id].append(record)

    for cls in teacher_classes:
        active_session = active_session_by_class.get(cls.id)
        cls.active_session = active_session
        cls.live_total_count = student_counts.get(cls.id, 0)
        if active_session:
            cls.attendance_by_student = {r.student_id: r for r in records_by_session.get(active_session.id, [])}
            cls.live_present_count = live_present_counts.get(active_session.id, 0)
            cls.deadline = _session_deadline(active_session)
        else:
            cls.attendance_by_student = {}
            cls.live_present_count = 0
            cls.deadline = None

        cls.confirmed_sessions = confirmed_sessions_by_class.get(cls.id, [])
        cls.last_confirmed = cls.confirmed_sessions[0] if cls.confirmed_sessions else None

    dashboard_summary = {
        'class_count': len(teacher_classes),
        'active_session_count': sum(1 for cls in teacher_classes if cls.active_session),
        'student_total': sum(len(cls.students) for cls in teacher_classes),
        'confirmed_session_total': sum(len(cls.confirmed_sessions) for cls in teacher_classes),
    }
    return teacher_classes, dashboard_summary


@app.route('/teacher_dashboard', methods=['GET', 'POST'])
@role_required('teacher')
@permission_required()
def teacher_dashboard():
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        return _handle_user_calendar_dashboard_post(user, PERMISSIONS['TEACHER_DASHBOARD_CALENDAR_UPDATE'], 'teacher_dashboard')

    teacher_classes, dashboard_summary = _build_teacher_dashboard_context(user)

    weather_city = (request.args.get('city') or session.get('teacher_weather_city') or 'Lefkosa').strip()
    lat_arg = (request.args.get('lat') or '').strip()
    lon_arg = (request.args.get('lon') or '').strip()
    weather_lat = session.get('teacher_weather_lat')
    weather_lon = session.get('teacher_weather_lon')

    if lat_arg and lon_arg:
        try:
            parsed_lat = float(lat_arg)
            parsed_lon = float(lon_arg)
            if -90 <= parsed_lat <= 90 and -180 <= parsed_lon <= 180:
                weather_lat = parsed_lat
                weather_lon = parsed_lon
                session['teacher_weather_lat'] = parsed_lat
                session['teacher_weather_lon'] = parsed_lon
        except ValueError:
            pass

    if request.args.get('city'):
        session['teacher_weather_city'] = weather_city
        weather_lat = None
        weather_lon = None

    if weather_lat is not None and weather_lon is not None:
        weather = _fetch_weather(lat=float(weather_lat), lon=float(weather_lon))
    else:
        weather = _fetch_weather(city=weather_city)

    teacher_announcements = []
    try:
        now = datetime.datetime.now()
        teacher_course_ids = [course.id for course in user.courses_taught]
        teacher_announcements_query = Announcement.query.filter(
            ((Announcement.target_role.is_(None)) | (Announcement.target_role == 'all') | (Announcement.target_role == 'teacher')),
            ((Announcement.starts_at.is_(None)) | (Announcement.starts_at <= now)),
            ((Announcement.ends_at.is_(None)) | (Announcement.ends_at >= now)),
        )
        if teacher_course_ids:
            teacher_announcements_query = teacher_announcements_query.filter(
                (Announcement.course_id.is_(None)) | (Announcement.course_id.in_(teacher_course_ids))
            )
        else:
            teacher_announcements_query = teacher_announcements_query.filter(Announcement.course_id.is_(None))
        teacher_announcements = teacher_announcements_query.order_by(Announcement.created_at.desc()).limit(6).all()
    except Exception:
        db.session.rollback()
        teacher_announcements = []

    lookup_student_number = _normalize_form_text(request.args.get('student_number'), max_length=20)
    student_lookup_error = None
    student_dashboard_preview = None
    if lookup_student_number:
        teacher_student_ids = {student.id for cls in teacher_classes for student in cls.students}
        taught_course_ids = [course.id for course in user.courses_taught]
        if taught_course_ids:
            enrolled_student_rows = db.session.query(CourseEnrollment.student_id).filter(
                CourseEnrollment.course_id.in_(taught_course_ids)
            ).all()
            teacher_student_ids.update(student_id for student_id, in enrolled_student_rows)
        looked_up_student = None
        if teacher_student_ids:
            looked_up_student = Student.query.filter(
                Student.id.in_(teacher_student_ids),
                Student.student_number == lookup_student_number,
            ).first()

        if looked_up_student:
            try:
                now = datetime.datetime.now()
                looked_up_user = db.session.get(User, looked_up_student.id)
                taught_course_ids = [course.id for course in user.courses_taught]
                student_course_ids = [enrollment.course_id for enrollment in looked_up_student.course_enrollments]
                student_announcements_query = Announcement.query.filter(
                    ((Announcement.target_role.is_(None)) | (Announcement.target_role == 'all') | (Announcement.target_role == 'student')),
                    ((Announcement.starts_at.is_(None)) | (Announcement.starts_at <= now)),
                    ((Announcement.ends_at.is_(None)) | (Announcement.ends_at >= now)),
                )
                if student_course_ids:
                    student_announcements_query = student_announcements_query.filter(
                        (Announcement.course_id.is_(None)) | (Announcement.course_id.in_(student_course_ids))
                    )
                else:
                    student_announcements_query = student_announcements_query.filter(Announcement.course_id.is_(None))
                student_announcements = student_announcements_query.order_by(Announcement.created_at.desc()).limit(6).all()

                today = datetime.date.today()
                student_calendar_events = StudentCalendarEvent.query.filter_by(
                    student_id=looked_up_student.id
                ).order_by(StudentCalendarEvent.event_date.asc()).all()
                student_upcoming_events = [event for event in student_calendar_events if event.event_date >= today][:12]

                teacher_enrollments = (
                    CourseEnrollment.query
                    .join(Course, CourseEnrollment.course_id == Course.id)
                    .filter(
                        CourseEnrollment.student_id == looked_up_student.id,
                        Course.teacher_id == user.id,
                    )
                    .order_by(Course.code.asc())
                    .all()
                )

                enrollment_attendance_items = []
                for enrollment in teacher_enrollments:
                    course = enrollment.course
                    if not course:
                        continue

                    confirmed_session_total = 0
                    present_count = 0
                    absence_count = 0
                    attendance_pct = 0.0
                    attendance_status = 'no_data'

                    linked_class_id = None
                    code_value = (course.code or '').strip().upper()
                    if code_value.startswith('CLS') and code_value[3:].isdigit():
                        linked_class_id = int(code_value[3:])

                    if linked_class_id is not None:
                        linked_class = db.session.get(Class, linked_class_id)
                        if linked_class and linked_class.teacher_id == user.id:
                            confirmed_session_total = AttendanceSession.query.filter_by(
                                class_id=linked_class.id,
                                confirmed=True,
                            ).count()
                            if confirmed_session_total > 0:
                                present_count = (
                                    AttendanceRecord.query
                                    .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
                                    .filter(
                                        AttendanceSession.class_id == linked_class.id,
                                        AttendanceSession.confirmed.is_(True),
                                        AttendanceRecord.student_id == looked_up_student.id,
                                        AttendanceRecord.present.is_(True),
                                    )
                                    .count()
                                )
                                absence_count = max(confirmed_session_total - present_count, 0)
                                attendance_pct = round((present_count / confirmed_session_total) * 100.0, 2)
                                attendance_status = 'pass' if (present_count / confirmed_session_total) >= 0.7 else 'fail'

                    grade_status = 'pending'
                    if enrollment.grades:
                        avg_grade_point = sum(grade.grade_point for grade in enrollment.grades) / len(enrollment.grades)
                        grade_status = 'pass' if avg_grade_point >= 1.0 else 'fail'

                    enrollment_attendance_items.append(
                        {
                            'course_code': course.code,
                            'course_title': course.title,
                            'confirmed_session_total': confirmed_session_total,
                            'present_count': present_count,
                            'absence_count': absence_count,
                            'attendance_pct': attendance_pct,
                            'attendance_status': attendance_status,
                            'grade_status': grade_status,
                        }
                    )

                student_dashboard_preview = {
                    'student_id': looked_up_student.id,
                    'student_number': looked_up_student.student_number,
                    'name': looked_up_user.name if looked_up_user else f'{looked_up_student.first_name or ""} {looked_up_student.last_name or ""}'.strip() or '-',
                    'department': (looked_up_student.university_department or '').strip() or _lang_text('Henuz tanimli degil', 'Not set yet'),
                    'class_level': (looked_up_student.university_term or '').strip() or _lang_text('Henuz tanimli degil', 'Not set yet'),
                    'contact': {
                        'email': looked_up_user.email if looked_up_user else '-',
                        'phone': None,
                        'address': None,
                        'contact_preference': 'email',
                    },
                    'courses': enrollment_attendance_items,
                }
            except Exception:
                db.session.rollback()
                student_lookup_error = _lang_text('Ogrenci bilgileri yuklenemedi.', 'Student data could not be loaded.')
        else:
            student_lookup_error = _lang_text(
                'Bu ogrenci numarasi sizin derslerinizde bulunamadi.',
                'This student number was not found in your classes.',
            )

    _, teacher_upcoming_events, teacher_calendar_events = _serialize_user_calendar_events(user.id)

    return render_template(
        'teacher_dashboard.html',
        teacher_classes=teacher_classes,
        user_name=user.name,
        dashboard_summary=dashboard_summary,
        weather=weather,
        weather_using_location=bool(weather and weather.get('source') == 'location'),
        teacher_announcements=teacher_announcements,
        calendar_events=teacher_calendar_events,
        upcoming_event_count=len(teacher_upcoming_events),
        lookup_student_number=lookup_student_number,
        student_dashboard_preview=student_dashboard_preview,
        student_lookup_error=student_lookup_error,
    )


@app.route('/teacher/attendance-hub', methods=['GET'])
@role_required('teacher')
@permission_required()
def teacher_attendance_hub():
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    teacher_classes, dashboard_summary = _build_teacher_dashboard_context(user)

    return render_template(
        'teacher_attendance_hub.html',
        teacher_classes=teacher_classes,
        user_name=user.name,
        dashboard_summary=dashboard_summary,
    )


@app.route('/teacher/grade-entry', methods=['GET', 'POST'])
@role_required('teacher')
@permission_required()
def teacher_grade_entry():
    def _letter_from_ratio(ratio_percent: float) -> str:
        if ratio_percent >= 90:
            return 'AA'
        if ratio_percent >= 85:
            return 'BA'
        if ratio_percent >= 80:
            return 'BB'
        if ratio_percent >= 75:
            return 'CB'
        if ratio_percent >= 70:
            return 'CC'
        if ratio_percent >= 65:
            return 'DC'
        if ratio_percent >= 60:
            return 'DD'
        if ratio_percent >= 50:
            return 'FD'
        return 'FF'

    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    teacher_classes = Class.query.filter_by(teacher_id=user.id).all()
    class_lookup = {cls.id: cls for cls in teacher_classes}

    if request.method == 'POST':
        class_id_raw = _normalize_form_text(request.form.get('class_id'), max_length=20)
        student_id_raw = _normalize_form_text(request.form.get('student_id'), max_length=20)
        assessment_name = _normalize_form_text(request.form.get('assessment_name'), max_length=120)
        max_points_raw = _normalize_form_text(request.form.get('max_points'), max_length=20)
        score_raw = _normalize_form_text(request.form.get('score'), max_length=20)

        if not class_id_raw.isdigit() or not student_id_raw.isdigit():
            flash('Geçersiz ders veya öğrenci seçimi.', 'danger')
            return redirect(url_for('teacher_grade_entry'))

        class_id = int(class_id_raw)
        student_id = int(student_id_raw)
        cls = class_lookup.get(class_id)
        if not cls:
            flash('Bu derse not girme yetkiniz yok.', 'danger')
            return redirect(url_for('teacher_grade_entry'))

        allowed_student_ids = {s.id for s in cls.students}
        if student_id not in allowed_student_ids:
            flash('Seçilen öğrenci bu derse kayıtlı değil.', 'danger')
            return redirect(url_for('teacher_grade_entry'))

        if not assessment_name:
            flash('Değerlendirme adı zorunludur.', 'warning')
            return redirect(url_for('teacher_grade_entry'))

        try:
            max_points = float(max_points_raw)
            score = float(score_raw)
        except (TypeError, ValueError):
            flash('Sınav puan alanları sayısal olmalıdır.', 'warning')
            return redirect(url_for('teacher_grade_entry'))

        if max_points <= 0:
            flash("Sınav kaç üzerinden bilgisi 0'dan büyük olmalıdır.", 'warning')
            return redirect(url_for('teacher_grade_entry'))

        if score < 0 or score > max_points:
            flash('Sınav notu 0 ile toplam puan arasında olmalıdır.', 'warning')
            return redirect(url_for('teacher_grade_entry'))

        ratio_percent = (score / max_points) * 100.0
        letter_grade = _letter_from_ratio(ratio_percent)

        try:
            course_code = f'CLS{cls.id:04d}'
            course = Course.query.filter_by(code=course_code).first()
            if not course:
                course = Course(
                    code=course_code,
                    title=cls.name[:120],
                    credit=3,
                    teacher_id=user.id,
                    term_id=None,
                )
                db.session.add(course)
                db.session.flush()

            enrollment = CourseEnrollment.query.filter_by(
                student_id=student_id,
                course_id=course.id,
            ).first()
            if not enrollment:
                enrollment = CourseEnrollment(student_id=student_id, course_id=course.id)
                db.session.add(enrollment)
                db.session.flush()

            grade = GradeRecord(
                enrollment_id=enrollment.id,
                assessment_name=f"{assessment_name} ({score:g}/{max_points:g})",
                letter_grade=letter_grade,
                grade_point=GradeRecord.point_from_letter(letter_grade),
            )
            db.session.add(grade)
            db.session.commit()
            flash(f'Not basariyla kaydedildi. Otomatik harf notu: {letter_grade}', 'success')
        except Exception:
            db.session.rollback()
            flash('Not kaydı sırasında hata oluştu.', 'danger')

        return redirect(url_for('teacher_grade_entry', class_id=class_id))

    selected_class_id_raw = (request.args.get('class_id') or '').strip()
    selected_class = None
    if selected_class_id_raw.isdigit():
        selected_class = class_lookup.get(int(selected_class_id_raw))
    if not selected_class and teacher_classes:
        selected_class = teacher_classes[0]

    students_for_class = []
    recent_grades = []
    if selected_class:
        students_for_class = sorted(
            selected_class.students,
            key=lambda s: ((s.user.name if s.user else '').lower(), s.student_number or ''),
        )
        student_ids = [s.id for s in students_for_class]
        if student_ids:
            recent_grades = (
                GradeRecord.query
                .join(CourseEnrollment, GradeRecord.enrollment_id == CourseEnrollment.id)
                .join(Course, CourseEnrollment.course_id == Course.id)
                .filter(Course.teacher_id == user.id, CourseEnrollment.student_id.in_(student_ids))
                .order_by(GradeRecord.created_at.desc())
                .limit(50)
                .all()
            )

    return render_template(
        'teacher_grade_entry.html',
        user_name=user.name,
        teacher_classes=teacher_classes,
        selected_class=selected_class,
        students_for_class=students_for_class,
        recent_grades=recent_grades,
    )


@app.route('/teacher/course-roster', methods=['GET'])
@role_required('teacher')
@permission_required()
def teacher_course_roster():
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    teacher_courses = Course.query.filter_by(teacher_id=user.id).order_by(Course.code.asc()).all()
    selected_course = None
    selected_course_id_raw = (request.args.get('course_id') or '').strip()
    if selected_course_id_raw.isdigit():
        selected_course = next((c for c in teacher_courses if c.id == int(selected_course_id_raw)), None)
    if not selected_course and teacher_courses:
        selected_course = teacher_courses[0]

    search_q = (request.args.get('q') or '').strip()
    export_csv = request.args.get('export') == 'csv'

    enrolled_rows = []
    if selected_course:
        query = (
            CourseEnrollment.query
            .join(Student, CourseEnrollment.student_id == Student.id)
            .join(User, Student.id == User.id)
            .filter(CourseEnrollment.course_id == selected_course.id)
        )
        if search_q:
            like = f'%{search_q}%'
            query = query.filter(
                db.or_(User.name.ilike(like), Student.student_number.ilike(like))
            )
        enrolled_rows = query.order_by(User.name.asc()).all()

    if export_csv and selected_course:
        import io
        si = io.StringIO()
        writer = csv.writer(si)
        writer.writerow(['Öğrenci No', 'Ad Soyad', 'E-posta', 'Kayıt Tarihi'])
        for en in enrolled_rows:
            sn = en.student.student_number if en.student else ''
            name = en.student.user.name if en.student and en.student.user else ''
            email = en.student.user.email if en.student and en.student.user else ''
            date = en.created_at.strftime('%d-%m-%Y %H:%M') if en.created_at else ''
            writer.writerow([sn, name, email, date])
        output = si.getvalue()
        from flask import Response
        filename = f'roster_{selected_course.code}.csv'
        return Response(
            output,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
        )

    return render_template(
        'teacher_course_roster.html',
        user_name=user.name,
        teacher_courses=teacher_courses,
        selected_course=selected_course,
        enrolled_rows=enrolled_rows,
        search_q=search_q,
    )


# ------------------ TEACHER CLASS HISTORY ------------------
@app.route('/teacher/history/<int:class_id>')
@role_required('teacher')
@permission_required()
def teacher_class_history(class_id):
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    cls = Class.query.filter_by(id=class_id, teacher_id=user.id).first_or_404()

    week_filter = request.args.get('week', '').strip()
    start_date = request.args.get('start', '').strip()
    end_date = request.args.get('end', '').strip()

    query = AttendanceSession.query.filter_by(class_id=cls.id, confirmed=True)
    if week_filter:
        query = query.filter(AttendanceSession.week.ilike(f"%{week_filter}%"))
    if start_date:
        try:
            start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(AttendanceSession.date >= start_dt)
        except ValueError:
            flash('Geçersiz başlangıç tarihi formatı.', 'warning')
    if end_date:
        try:
            end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
            query = query.filter(AttendanceSession.date < end_dt)
        except ValueError:
            flash('Geçersiz bitiş tarihi formatı.', 'warning')

    sessions = query.order_by(AttendanceSession.date.desc()).all()
    session_ids = [sess.id for sess in sessions]
    present_counts = {}
    if session_ids:
        present_rows = (
            db.session.query(AttendanceRecord.session_id, func.count(AttendanceRecord.id))
            .filter(AttendanceRecord.session_id.in_(session_ids), AttendanceRecord.present.is_(True))
            .group_by(AttendanceRecord.session_id)
            .all()
        )
        present_counts = {session_id: count for session_id, count in present_rows}

    total_students = len(cls.students)
    sessions_data = []
    for sess in sessions:
        present_count = present_counts.get(sess.id, 0)
        sessions_data.append({
            'id': sess.id,
            'date': sess.date,
            'week': sess.week,
            'present_count': present_count,
            'total_students': total_students,
        })

    return render_template('teacher_history.html', cls=cls, sessions=sessions_data, week_filter=week_filter, start_date=start_date, end_date=end_date)


@app.route('/teacher/history/<int:class_id>/export')
@role_required('teacher')
@permission_required()
def export_teacher_class_history(class_id):
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    cls = Class.query.filter_by(id=class_id, teacher_id=user.id).first_or_404()

    week_filter = request.args.get('week', '').strip()
    start_date = request.args.get('start', '').strip()
    end_date = request.args.get('end', '').strip()

    query = AttendanceSession.query.filter_by(class_id=cls.id, confirmed=True)
    if week_filter:
        query = query.filter(AttendanceSession.week.ilike(f"%{week_filter}%"))
    if start_date:
        try:
            start_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(AttendanceSession.date >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
            query = query.filter(AttendanceSession.date < end_dt)
        except ValueError:
            pass

    sessions = query.order_by(AttendanceSession.date.desc()).all()
    output = StringIO()
    writer = csv.writer(output)

    def padded(value):
        """Add visual breathing room inside cells without extra CSV separators."""
        return f" {value} "

    writer.writerow(['Session Date', 'Week', 'Student Number', 'Student Name', 'Student Email', 'Attendance'])

    sorted_students = sorted(cls.students, key=lambda s: (s.student_number or '', s.id))
    for idx, sess in enumerate(sessions):
        present_ids = {record.student_id for record in sess.records if record.present}

        if not sorted_students:
            writer.writerow([
                padded(sess.date.strftime('%d-%m-%Y %H:%M')),
                padded(sess.week or '-'),
                padded('-'),
                padded('-'),
                padded('-'),
                padded('No students in class'),
            ])
            continue

        for student in sorted_students:
            student_name = student.user.name if student.user else f"Student {student.id}"
            student_email = student.user.email if student.user else '-'
            status = 'Present' if student.id in present_ids else 'Absent'
            writer.writerow([
                padded(sess.date.strftime('%d-%m-%Y %H:%M')),
                padded(sess.week or '-'),
                padded(student.student_number),
                padded(student_name),
                padded(student_email),
                padded(status),
            ])

        # Add visual separation between session/week blocks for Excel readability.
        if idx < len(sessions) - 1:
            writer.writerow([])
            writer.writerow([])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={cls.name}_attendance_history.csv'}
    )


@app.route('/teacher/session/<int:session_id>/stats')
@role_required('teacher')
@permission_required()
def session_stats(session_id):
    session_obj = AttendanceSession.query.get_or_404(session_id)
    denied = ensure_teacher_session_ownership(session_obj, on_fail='json')
    if denied:
        return denied
    cls = session_obj.class_obj

    present_count = AttendanceRecord.query.filter_by(session_id=session_obj.id, present=True).count()
    return jsonify({
        'present_count': present_count,
        'total_count': len(cls.students),
        'active': session_obj.active,
    })


# Keep legacy history route for backward compatibility
@app.route('/teacher/history')
@role_required('teacher')
@permission_required()
def teacher_history_redirect():
    return redirect(url_for('teacher_dashboard'))


# ------------------ SESSION DETAIL ------------------
@app.route('/teacher/session/<int:session_id>')
@role_required('teacher')
@permission_required()
def session_detail(session_id):
    session_obj = AttendanceSession.query.get_or_404(session_id)
    denied = ensure_teacher_session_ownership(session_obj, on_fail='login')
    if denied:
        return denied
    cls = session_obj.class_obj

    attendance_ids = {r.student_id for r in session_obj.records if r.present}
    confirmed_sessions = AttendanceSession.query.filter_by(class_id=cls.id, confirmed=True).all()
    confirmed_session_ids = [s.id for s in confirmed_sessions]
    total_confirmed_sessions = len(confirmed_session_ids)
    attended_counts = {}

    if confirmed_session_ids:
        attended_rows = (
            db.session.query(AttendanceRecord.student_id, func.count(AttendanceRecord.id))
            .filter(
                AttendanceRecord.session_id.in_(confirmed_session_ids),
                AttendanceRecord.present == True,
            )
            .group_by(AttendanceRecord.student_id)
            .all()
        )
        attended_counts = {student_id: count for student_id, count in attended_rows}

    absence_stats = {}
    for student in cls.students:
        if total_confirmed_sessions == 0:
            absence_stats[student.id] = {
                'absent_count': 0,
                'total_sessions': 0,
                'absence_pct': 0.0,
            }
            continue

        attended_count = int(attended_counts.get(student.id, 0))
        absent_count = total_confirmed_sessions - attended_count
        absence_stats[student.id] = {
            'absent_count': absent_count,
            'total_sessions': total_confirmed_sessions,
            'absence_pct': (absent_count / total_confirmed_sessions) * 100,
        }

    return render_template(
        'teacher_session_detail.html',
        cls=cls,
        session=session_obj,
        attendance_ids=attendance_ids,
        absence_stats=absence_stats,
    )


# ------------------ DELETE SESSION ------------------
@app.route('/teacher/session/<int:session_id>/delete', methods=['POST'])
@role_required('teacher')
@permission_required()
def delete_session(session_id):
    session_obj = AttendanceSession.query.get_or_404(session_id)
    denied = ensure_teacher_session_ownership(session_obj, on_fail='login')
    if denied:
        return denied
    cls = session_obj.class_obj

    # Only confirmed sessions can be deleted.
    if not session_obj.confirmed:
        flash('Bu oturumun silinmeden önce tamamlanması gerekiyor.', 'warning')
        return redirect(url_for('teacher_class_history', class_id=cls.id))

    AttendanceRecord.query.filter_by(session_id=session_id).delete()
    db.session.delete(session_obj)
    db.session.commit()

    flash('Yoklama kaydı silindi.', 'success')
    return redirect(url_for('teacher_class_history', class_id=cls.id))


# ------------------ TEACHER ACCOUNT ------------------
@app.route('/teacher/account', methods=['GET', 'POST'])
@role_required('teacher')
@permission_required()
def teacher_account():
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        permission_error = ensure_permission(PERMISSIONS['TEACHER_ACCOUNT_UPDATE'], 'teacher_account')
        if permission_error:
            return permission_error

        action = _normalize_form_text(request.form.get('action'), max_length=40).lower()
        if action not in {'change_password', 'delete_account'}:
            flash('Geçersiz işlem.', 'warning')
            return redirect(url_for('teacher_account'))

        if action == 'change_password':
            current_password = request.form.get('current_password') or ''
            new_password = request.form.get('new_password') or ''
            new_password_confirm = request.form.get('new_password_confirm') or ''

            if not current_password or not new_password or not new_password_confirm:
                flash('Tüm şifre alanları zorunludur.', 'warning')
                return redirect(url_for('teacher_account'))

            if not user.check_password(current_password):
                flash('Mevcut şifre hatalı.', 'danger')
                return redirect(url_for('teacher_account'))

            if new_password != new_password_confirm:
                flash('Yeni şifre ve onay eşleşmiyor.', 'warning')
                return redirect(url_for('teacher_account'))

            password_error = validate_password_policy(new_password, user_name=user.name, user_email=user.email)
            if password_error:
                flash(password_error, 'danger')
                return redirect(url_for('teacher_account'))

            user.set_password(new_password)
            db.session.commit()
            flash('Şifreniz başarıyla değiştirildi.', 'success')
            return redirect(url_for('teacher_account'))

        if action == 'delete_account':
            password = request.form.get('password') or ''
            if not password:
                flash('Şifre zorunludur.', 'warning')
                return redirect(url_for('teacher_account'))
            if not user.check_password(password):
                flash('Şifre hatalı.', 'danger')
                return redirect(url_for('teacher_account'))

            # Delete all related user data.
            for cls in user.teacher_classes:
                # Delete class sessions and records.
                for sess in cls.sessions:
                    AttendanceRecord.query.filter_by(session_id=sess.id).delete()
                AttendanceSession.query.filter_by(class_id=cls.id).delete()
                # Remove class-student links.
                cls.students = []
                db.session.delete(cls)
            # Delete student profile if present.
            for student in user.students:
                db.session.delete(student)

            db.session.delete(user)
            db.session.commit()

            session.clear()
            flash('Hesabınız silindi.', 'success')
            return redirect(url_for('login'))

    return render_template('teacher_account.html')


# ------------------ STUDENT ACCOUNT ------------------
@app.route('/student/account', methods=['GET', 'POST'])
@role_required('student')
@permission_required()
def student_account():
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        permission_error = ensure_permission(PERMISSIONS['STUDENT_ACCOUNT_UPDATE'], 'student_account')
        if permission_error:
            return permission_error

        action = _normalize_form_text(request.form.get('action'), max_length=40).lower()
        if action not in {'change_password', 'delete_account'}:
            flash('Geçersiz işlem.', 'warning')
            return redirect(url_for('student_account'))

        if action == 'change_password':
            current_password = request.form.get('current_password') or ''
            new_password = request.form.get('new_password') or ''
            new_password_confirm = request.form.get('new_password_confirm') or ''

            if not current_password or not new_password or not new_password_confirm:
                flash('Tüm şifre alanları zorunludur.', 'warning')
                return redirect(url_for('student_account'))

            if not user.check_password(current_password):
                flash('Mevcut şifre hatalı.', 'danger')
                return redirect(url_for('student_account'))

            if new_password != new_password_confirm:
                flash('Yeni şifre ve onay eşleşmiyor.', 'warning')
                return redirect(url_for('student_account'))

            password_error = validate_password_policy(new_password, user_name=user.name, user_email=user.email)
            if password_error:
                flash(password_error, 'danger')
                return redirect(url_for('student_account'))

            user.set_password(new_password)
            db.session.commit()
            flash('Şifreniz başarıyla değiştirildi.', 'success')
            return redirect(url_for('student_account'))

        if action == 'delete_account':
            flash('Hesap silme devre dışı. Lütfen sistem yöneticisiyle iletişime geçin.', 'warning')
            return redirect(url_for('student_account'))

    return render_template('student_account.html')


# ------------------ STUDENT DASHBOARD ------------------
@app.route('/student_dashboard', methods=['GET', 'POST'])
@role_required('student')
@permission_required()
def student_dashboard():
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    if not user.students:
        flash('Öğrenci profili bulunamadı. Lütfen destek ekibiyle iletişime geçin.', 'danger')
        return redirect(url_for('logout'))
    student = user.students[0]

    if request.method == 'POST':
        permission_error = ensure_permission(PERMISSIONS['STUDENT_DASHBOARD_CALENDAR_UPDATE'], 'student_dashboard')
        if permission_error:
            return permission_error

        action = _normalize_form_text(request.form.get('action'), max_length=40).lower()
        if action not in {'add_calendar_event', 'delete_calendar_event'}:
            flash('Geçersiz panel işlemi.', 'warning')
            return redirect(url_for('student_dashboard'))

        if action == 'add_calendar_event':
            title = (request.form.get('title') or '').strip()
            event_type = (request.form.get('event_type') or 'activity').strip().lower()
            event_date_raw = (request.form.get('event_date') or '').strip()
            note = (request.form.get('note') or '').strip()

            if len(title) > 120:
                flash('Etkinlik başlığı çok uzun.', 'warning')
                return redirect(url_for('student_dashboard'))

            if not title or not event_date_raw:
                flash('Etkinlik başlığı ve tarihi zorunludur.', 'warning')
                return redirect(url_for('student_dashboard'))

            if event_type not in ('exam', 'activity'):
                event_type = 'activity'

            try:
                event_date = datetime.datetime.strptime(event_date_raw, '%Y-%m-%d').date()
            except ValueError:
                flash('Geçersiz etkinlik tarihi formatı.', 'warning')
                return redirect(url_for('student_dashboard'))

            event = StudentCalendarEvent(
                student_id=student.id,
                title=title,
                event_type=event_type,
                event_date=event_date,
                note=note[:240] if note else None,
            )
            db.session.add(event)
            db.session.commit()
            flash('Takvim etkinliği eklendi.', 'success')
            return redirect(url_for('student_dashboard'))

        if action == 'delete_calendar_event':
            event_id_raw = _normalize_form_text(request.form.get('event_id'), max_length=20)
            if not event_id_raw.isdigit():
                flash('Geçersiz etkinlik kimliği.', 'warning')
                return redirect(url_for('student_dashboard'))
            event_id = int(event_id_raw) if event_id_raw and event_id_raw.isdigit() else None
            event = db.session.get(StudentCalendarEvent, event_id) if event_id is not None else None
            denied = ensure_student_event_ownership(
                student,
                event,
                on_fail='student_dashboard',
                fail_message='Event not found.',
            )
            if denied:
                return denied

            db.session.delete(event)
            db.session.commit()
            flash('Takvim etkinliği silindi.', 'success')
            return redirect(url_for('student_dashboard'))

    city_arg = (request.args.get('city') or '').strip()
    lat_arg = (request.args.get('lat') or '').strip()
    lon_arg = (request.args.get('lon') or '').strip()

    weather_lat = session.get('weather_lat')
    weather_lon = session.get('weather_lon')
    weather_city = (session.get('weather_city') or 'Istanbul').strip()

    # Manual city search takes precedence and clears auto-location cache.
    if city_arg:
        weather_city = city_arg[:50]
        session['weather_city'] = weather_city
        session.pop('weather_lat', None)
        session.pop('weather_lon', None)
        weather_lat = None
        weather_lon = None

    # Geolocation coordinates update weather source when provided.
    if lat_arg and lon_arg:
        try:
            parsed_lat = float(lat_arg)
            parsed_lon = float(lon_arg)
            if -90 <= parsed_lat <= 90 and -180 <= parsed_lon <= 180:
                weather_lat = parsed_lat
                weather_lon = parsed_lon
                session['weather_lat'] = parsed_lat
                session['weather_lon'] = parsed_lon
        except ValueError:
            pass

    if weather_lat is not None and weather_lon is not None:
        weather = _fetch_weather(lat=float(weather_lat), lon=float(weather_lon))
    else:
        weather = _fetch_weather(city=weather_city)

    announcements = []
    try:
        now = datetime.datetime.now()
        student_course_ids = [en.course_id for en in student.course_enrollments]
        announcements_query = Announcement.query.filter(
            ((Announcement.target_role.is_(None)) | (Announcement.target_role == 'all') | (Announcement.target_role == 'student')),
            ((Announcement.starts_at.is_(None)) | (Announcement.starts_at <= now)),
            ((Announcement.ends_at.is_(None)) | (Announcement.ends_at >= now)),
        )
        if student_course_ids:
            announcements_query = announcements_query.filter(
                (Announcement.course_id.is_(None)) | (Announcement.course_id.in_(student_course_ids))
            )
        else:
            announcements_query = announcements_query.filter(Announcement.course_id.is_(None))
        announcements = announcements_query.order_by(Announcement.created_at.desc()).limit(6).all()
    except Exception:
        db.session.rollback()
        announcements = []

    today = datetime.date.today()
    all_events = StudentCalendarEvent.query.filter_by(student_id=student.id).order_by(StudentCalendarEvent.event_date.asc()).all()
    upcoming_events = [e for e in all_events if e.event_date >= today][:12]
    upcoming_exam_count = sum(1 for e in upcoming_events if e.event_type == 'exam')
    upcoming_activity_count = sum(1 for e in upcoming_events if e.event_type == 'activity')
    calendar_events = [
        {
            'id': e.id,
            'title': e.title,
            'event_type': e.event_type,
            'event_date': e.event_date.isoformat(),
            'note': e.note or '',
        }
        for e in all_events
    ]

    cards = [
        {'title': _t('identity_information'), 'desc': _t('identity_information_desc'), 'endpoint': 'student_identity_info'},
        {'title': _t('education_information'), 'desc': _t('education_information_desc'), 'endpoint': 'student_education_info'},
        {'title': _t('family_information'), 'desc': _t('family_information_desc'), 'endpoint': 'student_family_info'},
        {'title': _t('documents'), 'desc': _t('documents_desc'), 'endpoint': 'student_documents_info'},
        {'title': _t('contact'), 'desc': _t('contact_desc'), 'endpoint': 'student_contact_info'},
        {'title': _t('current_account'), 'desc': _t('current_account_desc'), 'endpoint': 'student_current_account'},
        {'title': _t('payments'), 'desc': _t('payments_desc'), 'endpoint': 'student_payment_info'},
        {'title': _t('absence'), 'desc': _t('absence_desc'), 'endpoint': 'student_absence'},
        {'title': _t('term_courses'), 'desc': _t('term_courses_desc'), 'endpoint': 'student_term_courses'},
        {'title': _t('transcript'), 'desc': _t('transcript_desc'), 'endpoint': 'student_transcript'},
        {'title': _t('academic_calendar'), 'desc': _t('academic_calendar_desc'), 'endpoint': 'student_academic_calendar'},
        {'title': _t('exams'), 'desc': _t('exams_desc'), 'endpoint': 'student_exams'},
    ]

    dashboard_summary = {
        'joined_class_count': len(student.classes),
        'upcoming_events_count': len(upcoming_events),
        'announcement_count': len(announcements),
        'calendar_total_count': len(all_events),
    }

    return render_template(
        'student_dashboard.html',
        user_name=user.name,
        cards=cards,
        announcements=announcements,
        upcoming_events=upcoming_events,
        calendar_events=calendar_events,
        upcoming_exam_count=upcoming_exam_count,
        upcoming_activity_count=upcoming_activity_count,
        weather=weather,
        weather_using_location=bool(weather and weather.get('source') == 'location'),
        dashboard_summary=dashboard_summary,
    )


@app.route('/reports')
@login_required_session
def reports():
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    role = session.get('role')
    if role == 'teacher':
        permission_error = ensure_permission(PERMISSIONS['TEACHER_REPORT_READ'], 'teacher_dashboard')
        if permission_error:
            return permission_error

        classes = Class.query.filter_by(teacher_id=user.id).order_by(Class.name.asc()).all()
        rows = []
        for cls in classes:
            confirmed_sessions = AttendanceSession.query.filter_by(class_id=cls.id, confirmed=True).all()
            session_ids = [sess.id for sess in confirmed_sessions]
            total_sessions = len(session_ids)
            total_students = len(cls.students)
            present_total = 0
            if session_ids:
                present_total = AttendanceRecord.query.filter(
                    AttendanceRecord.session_id.in_(session_ids),
                    AttendanceRecord.present.is_(True),
                ).count()

            expected_total = total_sessions * total_students
            attendance_rate = (present_total / expected_total * 100.0) if expected_total else 0.0
            rows.append(
                {
                    'class_name': cls.name,
                    'student_count': total_students,
                    'confirmed_session_count': total_sessions,
                    'present_total': present_total,
                    'expected_total': expected_total,
                    'attendance_rate': round(attendance_rate, 2),
                }
            )

        totals = {
            'class_count': len(rows),
            'student_total': sum(row['student_count'] for row in rows),
            'session_total': sum(row['confirmed_session_count'] for row in rows),
            'present_total': sum(row['present_total'] for row in rows),
            'expected_total': sum(row['expected_total'] for row in rows),
        }
        totals['attendance_rate'] = round((totals['present_total'] / totals['expected_total'] * 100.0), 2) if totals['expected_total'] else 0.0

        return render_template('reports.html', report_role='teacher', user=user, rows=rows, totals=totals)

    if role == 'student':
        permission_error = ensure_permission(PERMISSIONS['STUDENT_REPORT_READ'], 'student_dashboard')
        if permission_error:
            return permission_error

        if not user.students:
            flash('Öğrenci profili bulunamadı. Lütfen destek ekibiyle iletişime geçin.', 'danger')
            return redirect(url_for('logout'))

        student = user.students[0]
        rows = []
        for cls in sorted(student.classes, key=lambda c: (c.name or '').lower()):
            confirmed_sessions = AttendanceSession.query.filter_by(class_id=cls.id, confirmed=True).all()
            session_ids = [sess.id for sess in confirmed_sessions]
            total_sessions = len(session_ids)
            present_count = 0
            if session_ids:
                present_count = AttendanceRecord.query.filter(
                    AttendanceRecord.student_id == student.id,
                    AttendanceRecord.session_id.in_(session_ids),
                    AttendanceRecord.present.is_(True),
                ).count()
            absence_count = total_sessions - present_count
            attendance_rate = (present_count / total_sessions * 100.0) if total_sessions else 0.0
            rows.append(
                {
                    'class_name': cls.name,
                    'total_sessions': total_sessions,
                    'present_count': present_count,
                    'absence_count': absence_count,
                    'attendance_rate': round(attendance_rate, 2),
                }
            )

        totals = {
            'class_count': len(rows),
            'total_sessions': sum(row['total_sessions'] for row in rows),
            'present_total': sum(row['present_count'] for row in rows),
            'absence_total': sum(row['absence_count'] for row in rows),
        }
        totals['attendance_rate'] = round((totals['present_total'] / totals['total_sessions'] * 100.0), 2) if totals['total_sessions'] else 0.0

        return render_template('reports.html', report_role='student', user=user, rows=rows, totals=totals)

    flash('Raporlar ekranı yalnızca öğretmen ve öğrenci hesapları içindir.', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/student/absence', methods=['GET', 'POST'])
@role_required('student')
@permission_required()
def student_absence():
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    _auto_finalize_expired_sessions()

    if not user.students:
        flash('Öğrenci profili bulunamadı. Lütfen destek ekibiyle iletişime geçin.', 'danger')
        return redirect(url_for('logout'))
    student = user.students[0]

    if request.method == 'POST':
        permission_error = ensure_permission(PERMISSIONS['STUDENT_ABSENCE_UPDATE'], 'student_absence')
        if permission_error:
            return permission_error

        class_id = _normalize_form_text(request.form.get('class_id'), max_length=20)
        if not class_id.isdigit():
            flash('Geçersiz sınıf kimliği.', 'warning')
            return redirect(url_for('student_absence'))

        cls = db.session.get(Class, int(class_id))
        if not cls:
            flash('Sınıf bulunamadı.', 'warning')
            return redirect(url_for('student_absence'))

        if cls not in student.classes:
            student.classes.append(cls)
            db.session.commit()
            flash(f"Derse başarıyla katıldınız: {cls.name}", "success")
        else:
            flash("Derse katılım başarısız veya zaten kayıtlısınız.", "warning")
        return redirect(url_for('student_absence'))

    search_query = request.args.get('search')
    search_message = None
    filtered_classes = student.classes
    if search_query:
        normalized_query = search_query.strip().lower()
        if normalized_query:
            already_joined = any(normalized_query in cls.name.lower() for cls in student.classes)
            if already_joined:
                search_message = _t('already_enrolled_named', name=search_query)
            else:
                search_message = _t('no_class_found_named', name=search_query)

    classes = list(student.classes)
    class_ids = [cls.id for cls in classes]

    active_session_map = {}
    if class_ids:
        active_sessions = (
            AttendanceSession.query
            .filter(AttendanceSession.class_id.in_(class_ids), AttendanceSession.active == True)
            .order_by(AttendanceSession.class_id.asc(), AttendanceSession.date.desc())
            .all()
        )
        for active_session in active_sessions:
            if active_session.class_id not in active_session_map:
                active_session_map[active_session.class_id] = active_session

    confirmed_totals_by_class = {}
    if class_ids:
        confirmed_total_rows = (
            db.session.query(AttendanceSession.class_id, func.count(AttendanceSession.id))
            .filter(AttendanceSession.class_id.in_(class_ids), AttendanceSession.confirmed == True)
            .group_by(AttendanceSession.class_id)
            .all()
        )
        confirmed_totals_by_class = {class_id: total for class_id, total in confirmed_total_rows}

    attended_by_class = {}
    if class_ids:
        attended_rows = (
            db.session.query(AttendanceSession.class_id, func.count(AttendanceRecord.id))
            .join(AttendanceRecord, AttendanceRecord.session_id == AttendanceSession.id)
            .filter(
                AttendanceSession.class_id.in_(class_ids),
                AttendanceSession.confirmed == True,
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.present == True,
            )
            .group_by(AttendanceSession.class_id)
            .all()
        )
        attended_by_class = {class_id: total for class_id, total in attended_rows}

    marked_in_active_session_ids = set()
    active_session_ids = [sess.id for sess in active_session_map.values()]
    if active_session_ids:
        marked_rows = (
            db.session.query(AttendanceRecord.session_id)
            .filter(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.session_id.in_(active_session_ids),
            )
            .all()
        )
        marked_in_active_session_ids = {session_id for session_id, in marked_rows}

    active_announcements = []
    for cls in classes:
        active_session = active_session_map.get(cls.id)
        if active_session:
            deadline = _session_deadline(active_session)
            active_announcements.append({
                'class_name': cls.name,
                'week': active_session.week,
                'deadline': deadline,
                'token': cls.qr_token,
            })

    class_data = []
    for cls in filtered_classes:
        total = int(confirmed_totals_by_class.get(cls.id, 0))
        attended = int(attended_by_class.get(cls.id, 0))

        active_session = active_session_map.get(cls.id)
        active_week = active_session.week if active_session else None
        already_marked = False
        if active_session:
            already_marked = active_session.id in marked_in_active_session_ids

        class_data.append({
            'class_id': cls.id,
            'class_name': cls.name,
            'total': total,
            'attended': attended,
            'percentage': (attended / total * 100) if total else 0,
            'status': _t('pass') if (total > 0 and (attended / total) >= 0.7) else _t('fail'),
            'risk': (total > 0 and (attended / total) < 0.7),
            'active': bool(active_session),
            'active_week': active_week,
            'already_marked': already_marked,
            'qr_token': cls.qr_token,
        })

    # Hide integration-test fixtures from join list (example.com test users, Integration Class names).
    all_classes = (
        Class.query
        .join(User, Class.teacher_id == User.id)
        .filter(~Class.name.ilike('Integration Class %'))
        .filter(~User.email.ilike('%@example.com'))
        .all()
    )
    joined_class_ids = {cls.id for cls in classes}
    available_classes = [cls for cls in all_classes if cls.id not in joined_class_ids]

    absence_summary = {
        'joined_class_count': len(student.classes),
        'active_session_count': len(active_announcements),
        'total_confirmed_sessions': sum(item['total'] for item in class_data),
        'average_absence_pct': (sum(item['percentage'] for item in class_data) / len(class_data)) if class_data else 0,
    }

    return render_template(
        'student_absence.html',
        user_name=user.name,
        class_data=class_data,
        available_classes=available_classes,
        search_message=search_message,
        active_announcements=active_announcements,
        absence_summary=absence_summary,
    )


@app.route('/student/identity')
@role_required('student')
@permission_required()
def student_identity_info():
    user = db.session.get(User, session.get('user_id'))
    if not user or not user.students:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))
    student = user.students[0]

    first_name = (student.first_name or '').strip() if hasattr(student, 'first_name') else ''
    last_name = (student.last_name or '').strip() if hasattr(student, 'last_name') else ''
    if not first_name and not last_name:
        name_parts = [part for part in (user.name or '').strip().split(' ') if part]
        first_name = name_parts[0] if name_parts else _t('not_set_yet')
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else _t('not_set_yet')

    gender = (student.gender or '').strip() if hasattr(student, 'gender') else ''
    birth_place = (student.birth_place or '').strip() if hasattr(student, 'birth_place') else ''
    birth_date_text = _t('not_set_yet')
    if getattr(student, 'birth_date', None):
        birth_date_text = student.birth_date.strftime('%d-%m-%Y')

    identity_details = [
        (_t('first_name'), first_name or _t('not_set_yet')),
        (_t('last_name'), last_name or _t('not_set_yet')),
        (_t('gender'), gender or _t('not_set_yet')),
        (_t('birth_date'), birth_date_text),
        (_t('birth_place'), birth_place or _t('not_set_yet')),
    ]

    identity_number = (student.identity_number or '').strip() if hasattr(student, 'identity_number') else ''
    nationality = (student.nationality or '').strip() if hasattr(student, 'nationality') else ''
    registered_city = (student.registered_city or '').strip() if hasattr(student, 'registered_city') else ''
    registered_district = (student.registered_district or '').strip() if hasattr(student, 'registered_district') else ''
    passport_number = (student.passport_number or '').strip() if hasattr(student, 'passport_number') else ''
    passport_active = bool(getattr(student, 'passport_active', False))
    passport_issue_place = (student.passport_issue_place or '').strip() if hasattr(student, 'passport_issue_place') else ''

    passport_issue_date_text = _t('not_set_yet')
    if getattr(student, 'passport_issue_date', None):
        passport_issue_date_text = student.passport_issue_date.strftime('%d-%m-%Y')

    passport_expiry_date_text = _t('not_set_yet')
    if getattr(student, 'passport_expiry_date', None):
        passport_expiry_date_text = student.passport_expiry_date.strftime('%d-%m-%Y')

    marital_status = (student.marital_status or '').strip() if hasattr(student, 'marital_status') else ''
    blood_type = (student.blood_type or '').strip() if hasattr(student, 'blood_type') else ''
    is_veteran_martyr_relative = bool(getattr(student, 'is_veteran_martyr_relative', False))
    is_disabled = bool(getattr(student, 'is_disabled', False))
    disability_type = (student.disability_type or '').strip() if hasattr(student, 'disability_type') else ''
    disability_rate = (student.disability_rate or '').strip() if hasattr(student, 'disability_rate') else ''
    is_employed = bool(getattr(student, 'is_employed', False))
    is_group_company = bool(getattr(student, 'is_group_company', False))
    company_name = (student.company_name or '').strip() if hasattr(student, 'company_name') else ''
    work_type = (student.work_type or '').strip() if hasattr(student, 'work_type') else ''

    employment_start_date_text = _t('not_set_yet')
    if getattr(student, 'employment_start_date', None):
        employment_start_date_text = student.employment_start_date.strftime('%d-%m-%Y')

    citizenship_details = [
        (_t('identity_number'), identity_number or _t('not_set_yet')),
        (_t('nationality'), nationality or _t('not_set_yet')),
        (_t('registered_city'), registered_city or _t('not_set_yet')),
        (_t('registered_district'), registered_district or _t('not_set_yet')),
    ]

    passport_summary = passport_number or _t('not_set_yet')
    passport_details = [
        (_t('active_status_box'), passport_active),
        (_t('issued_date'), passport_issue_date_text),
        (_t('issued_place'), passport_issue_place or _t('not_set_yet')),
        (_t('valid_until'), passport_expiry_date_text),
    ]

    other_details = [
        (_t('marital_status'), marital_status or _t('not_set_yet')),
        (_t('blood_type'), blood_type or _t('not_set_yet')),
        (_t('veteran_martyr_relative_q'), _t('yes') if is_veteran_martyr_relative else _t('no')),
        (_t('disabled_q'), _t('yes') if is_disabled else _t('no')),
        (_t('disability_type'), disability_type or _t('not_set_yet')),
        (_t('disability_rate'), disability_rate or _t('not_set_yet')),
    ]

    working_details = [
        (_t('is_employed_q'), _t('yes') if is_employed else _t('no')),
        (_t('is_group_company_q'), _t('yes') if is_group_company else _t('no')),
        (_t('company_name'), company_name or _t('not_set_yet')),
        (_t('work_type'), work_type or _t('not_set_yet')),
        (_t('employment_start_date'), employment_start_date_text),
    ]

    return render_template(
        'student_identity.html',
        title=_t('identity_information'),
        identity_details=identity_details,
        citizenship_title=_t('citizenship'),
        citizenship_details=citizenship_details,
        passport_title=_t('passport_number'),
        passport_summary=passport_summary,
        passport_details=passport_details,
        other_title=_t('other_information'),
        other_details=other_details,
        working_title=_t('working_information'),
        working_details=working_details,
    )


@app.route('/student/education')
@role_required('student')
@permission_required()
def student_education_info():
    user = db.session.get(User, session.get('user_id'))
    if not user or not user.students:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))
    student = user.students[0]

    details = [
        (_t('entry_place'), (student.university_entry_place or '').strip() or _t('not_set_yet')),
        (_t('entry_type'), (student.university_entry_type or '').strip() or _t('not_set_yet')),
        (_t('academic_year'), (student.university_academic_year or '').strip() or _t('not_set_yet')),
        (_t('term'), (student.university_term or '').strip() or _t('not_set_yet')),
        (_t('faculty'), (student.university_faculty or '').strip() or _t('not_set_yet')),
        (_t('department'), (student.university_department or '').strip() or _t('not_set_yet')),
        (_t('scholarship_type'), (student.university_scholarship_type or '').strip() or _t('not_set_yet')),
        (_t('placement_type'), (student.university_placement_type or '').strip() or _t('not_set_yet')),
        (_t('score_type'), (student.university_score_type or '').strip() or _t('not_set_yet')),
        (_t('achievement_score'), (student.university_achievement_score or '').strip() or _t('not_set_yet')),
        (_t('placement_score'), (student.university_placement_score or '').strip() or _t('not_set_yet')),
        (_t('preference_order'), (student.university_preference_order or '').strip() or _t('not_set_yet')),
    ]

    highschool_graduation_date = (
        student.highschool_graduation_date.strftime('%Y-%m-%d')
        if student.highschool_graduation_date
        else _t('not_set_yet')
    )
    highschool_details = [
        (_t('highschool_name'), (student.highschool_name or '').strip() or _t('not_set_yet')),
        (_t('highschool_info'), (student.highschool_info or '').strip() or _t('not_set_yet')),
        (_t('highschool_graduation_date'), highschool_graduation_date),
    ]

    return render_template(
        'student_education.html',
        title=_t('education_information'),
        section_title=_t('university_information'),
        highschool_title=_t('highschool_information'),
        details=details,
        highschool_details=highschool_details,
    )


@app.route('/student/family')
@role_required('student')
@permission_required()
def student_family_info():
    details = [
        (_t('guardian_full_name'), _t('not_set_yet')),
        (_t('relationship'), _t('not_set_yet')),
        (_t('emergency_phone'), _t('not_set_yet')),
        (_t('note'), _t('family_note')),
    ]
    return render_template('student_module_page.html', title=_t('family_information'), details=details)


@app.route('/student/documents')
@role_required('student')
@permission_required()
def student_documents_info():
    details = [
        (_t('document_status'), _t('no_uploaded_document')),
        (_t('registration_document'), _t('pending')),
        (_t('student_certificate'), _t('can_be_requested')),
        (_t('note'), _t('documents_note')),
    ]
    return render_template('student_module_page.html', title=_t('documents'), details=details)


@app.route('/student/contact')
@role_required('student')
@permission_required()
def student_contact_info():
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))
    details = [
        (_t('email'), user.email),
        (_t('phone'), _t('not_set_yet')),
        (_t('address'), _t('not_set_yet')),
        (_t('contact_preference'), _t('email')),
    ]
    return render_template('student_module_page.html', title=_t('contact'), details=details)


@app.route('/student/current-account')
@role_required('student')
@permission_required()
def student_current_account():
    details = [
        (_t('total_debt'), '0.00'),
        (_t('total_paid'), '0.00'),
        (_t('current_balance'), '0.00'),
        (_t('note'), _t('current_account_note')),
    ]
    return render_template('student_module_page.html', title=_t('current_account'), details=details)


@app.route('/student/payment')
@role_required('student')
@permission_required()
def student_payment_info():
    details = [
        (_t('last_payment'), _t('no_record_found')),
        (_t('payment_method'), _t('undefined')),
        (_t('scheduled_payment'), _t('none')),
        (_t('note'), _t('payment_note')),
    ]
    return render_template('student_module_page.html', title=_t('payments'), details=details)


@app.route('/student/term-courses')
@role_required('student')
@permission_required()
def student_term_courses():
    user = db.session.get(User, session.get('user_id'))
    if not user or not user.students:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    def _get_or_create_registration_policy():
        policy = CourseRegistrationPolicy.query.first()
        if policy:
            return policy
        policy = CourseRegistrationPolicy(
            add_drop_start=None,
            add_drop_end=None,
            min_credits=0,
            max_credits=30,
            is_locked=False,
        )
        db.session.add(policy)
        db.session.commit()
        return policy

    def _is_add_drop_open(policy):
        if not policy or policy.is_locked:
            return False
        now = datetime.datetime.now()
        if policy.add_drop_start and now < policy.add_drop_start:
            return False
        if policy.add_drop_end and now > policy.add_drop_end:
            return False
        return True

    def _ensure_course_catalog_from_classes():
        created = False
        for cls in Class.query.all():
            code = f'CLS{cls.id:04d}'
            existing = Course.query.filter_by(code=code).first()
            if existing:
                continue
            db.session.add(Course(
                code=code,
                title=(cls.name or 'Course')[:120],
                credit=3,
                capacity=60,
                schedule_slot=None,
                teacher_id=cls.teacher_id,
                term_id=None,
            ))
            created = True
        if created:
            db.session.commit()

    student = user.students[0]
    _ensure_course_catalog_from_classes()
    policy = _get_or_create_registration_policy()
    is_open = _is_add_drop_open(policy)

    enrollments = (
        CourseEnrollment.query
        .join(Course, CourseEnrollment.course_id == Course.id)
        .filter(CourseEnrollment.student_id == student.id)
        .order_by(Course.code.asc())
        .all()
    )
    enrolled_course_ids = {en.course_id for en in enrollments}
    enrolled_credits = sum((en.course.credit or 0) for en in enrollments if en.course)

    available_courses = (
        Course.query
        .order_by(Course.code.asc())
        .all()
    )

    course_student_counts = {
        course_id: cnt
        for course_id, cnt in (
            db.session.query(CourseEnrollment.course_id, func.count(CourseEnrollment.id))
            .group_by(CourseEnrollment.course_id)
            .all()
        )
    }

    return render_template(
        'student_term_courses.html',
        student=student,
        policy=policy,
        is_open=is_open,
        enrollments=enrollments,
        enrolled_course_ids=enrolled_course_ids,
        enrolled_credits=enrolled_credits,
        available_courses=available_courses,
        course_student_counts=course_student_counts,
    )


@app.route('/student/term-courses/update', methods=['POST'])
@role_required('student')
@permission_required()
def student_term_courses_update():
    user = db.session.get(User, session.get('user_id'))
    if not user or not user.students:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    student = user.students[0]
    action = _normalize_form_text(request.form.get('action'), max_length=20)
    course_id_raw = _normalize_form_text(request.form.get('course_id'), max_length=20)

    if action not in {'add', 'drop'} or not course_id_raw.isdigit():
        flash('Geçersiz ders güncelleme isteği.', 'danger')
        return redirect(url_for('student_term_courses'))

    course = db.session.get(Course, int(course_id_raw))
    if not course:
        flash('Ders bulunamadı.', 'danger')
        return redirect(url_for('student_term_courses'))

    policy = CourseRegistrationPolicy.query.first()
    if not policy:
        policy = CourseRegistrationPolicy(min_credits=0, max_credits=30, is_locked=False)
        db.session.add(policy)
        db.session.commit()

    now = datetime.datetime.now()
    window_open = (
        not policy.is_locked
        and (policy.add_drop_start is None or now >= policy.add_drop_start)
        and (policy.add_drop_end is None or now <= policy.add_drop_end)
    )
    if not window_open:
        flash('Ders ekleme-bırakma penceresi şu an kapalı.', 'warning')
        return redirect(url_for('student_term_courses'))

    enrollment = CourseEnrollment.query.filter_by(student_id=student.id, course_id=course.id).first()

    if action == 'add':
        if enrollment:
            flash('Bu derse zaten kayıtlısınız.', 'warning')
            return redirect(url_for('student_term_courses'))

        current_credits = (
            db.session.query(func.coalesce(func.sum(Course.credit), 0))
            .join(CourseEnrollment, Course.id == CourseEnrollment.course_id)
            .filter(CourseEnrollment.student_id == student.id)
            .scalar() or 0
        )
        if current_credits + (course.credit or 0) > (policy.max_credits or 30):
            flash(f'Maksimum kredi limitini ({policy.max_credits or 30} kredi) aştınız.', 'warning')
            return redirect(url_for('student_term_courses'))

        if course.schedule_slot:
            clash_exists = (
                db.session.query(Course.id)
                .join(CourseEnrollment, Course.id == CourseEnrollment.course_id)
                .filter(
                    CourseEnrollment.student_id == student.id,
                    Course.schedule_slot == course.schedule_slot,
                )
                .first()
            )
            if clash_exists:
                flash(f'Ders programı çakışması: {course.schedule_slot} saatinde başka bir dersiniz var.', 'warning')
                return redirect(url_for('student_term_courses'))

        if course.capacity and course.capacity > 0:
            enrolled_count = CourseEnrollment.query.filter_by(course_id=course.id).count()
            if enrolled_count >= course.capacity:
                flash(f'{course.code} dersinin kontenjanı doldu ({course.capacity} kişi).', 'warning')
                return redirect(url_for('student_term_courses'))

        try:
            db.session.add(CourseEnrollment(student_id=student.id, course_id=course.id))
            db.session.flush()
            db.session.add(CourseEnrollmentAudit(
                actor_user_id=user.id,
                student_id=student.id,
                course_id=course.id,
                action='add',
                detail=f'student-self add {course.code}',
            ))
            db.session.commit()
            flash(f'{course.code} dersi başarıyla eklendi.', 'success')
        except Exception:
            db.session.rollback()
            flash('Ders eklenirken bir hata oluştu. Lütfen tekrar deneyin.', 'danger')
        return redirect(url_for('student_term_courses'))

    if not enrollment:
        flash('Bu derse kayıtlı değilsiniz.', 'warning')
        return redirect(url_for('student_term_courses'))

    current_credits = (
        db.session.query(func.coalesce(func.sum(Course.credit), 0))
        .join(CourseEnrollment, Course.id == CourseEnrollment.course_id)
        .filter(CourseEnrollment.student_id == student.id)
        .scalar() or 0
    )
    remaining_credits = current_credits - (course.credit or 0)
    if remaining_credits < (policy.min_credits or 0):
        flash(f'Bu dersi bırakırsanız minimum kredi limitinin ({policy.min_credits or 0} kredi) altına düşersiniz.', 'warning')
        return redirect(url_for('student_term_courses'))

    try:
        db.session.delete(enrollment)
        db.session.flush()
        db.session.add(CourseEnrollmentAudit(
            actor_user_id=user.id,
            student_id=student.id,
            course_id=course.id,
            action='drop',
            detail=f'student-self drop {course.code}',
        ))
        db.session.commit()
        flash(f'{course.code} dersi başarıyla bırakıldı.', 'success')
    except Exception:
        db.session.rollback()
        flash('Ders bırakılırken bir hata oluştu. Lütfen tekrar deneyin.', 'danger')
    return redirect(url_for('student_term_courses'))


@app.route('/admin/course-registration-window', methods=['GET', 'POST'])
@role_required('admin')
@permission_required()
def admin_course_registration_window():
    created = False
    for cls in Class.query.all():
        code = f'CLS{cls.id:04d}'
        if Course.query.filter_by(code=code).first():
            continue
        db.session.add(Course(
            code=code,
            title=(cls.name or 'Course')[:120],
            credit=3,
            capacity=60,
            schedule_slot=None,
            teacher_id=cls.teacher_id,
            term_id=None,
        ))
        created = True
    if created:
        db.session.commit()

    policy = CourseRegistrationPolicy.query.first()
    if not policy:
        policy = CourseRegistrationPolicy(min_credits=0, max_credits=30, is_locked=False)
        db.session.add(policy)
        db.session.commit()

    if request.method == 'POST':
        action = _normalize_form_text(request.form.get('action'), max_length=30)
        if action == 'save_policy':
            start_raw = _normalize_form_text(request.form.get('add_drop_start'), max_length=25)
            end_raw = _normalize_form_text(request.form.get('add_drop_end'), max_length=25)
            min_credits_raw = _normalize_form_text(request.form.get('min_credits'), max_length=10)
            max_credits_raw = _normalize_form_text(request.form.get('max_credits'), max_length=10)
            is_locked = request.form.get('is_locked') == 'on'

            try:
                policy.add_drop_start = datetime.datetime.fromisoformat(start_raw) if start_raw else None
                policy.add_drop_end = datetime.datetime.fromisoformat(end_raw) if end_raw else None
                policy.min_credits = int(min_credits_raw or 0)
                policy.max_credits = int(max_credits_raw or 30)
                policy.is_locked = is_locked
                if policy.max_credits < policy.min_credits:
                    flash('Maksimum kredi, minimum krediden az olamaz.', 'warning')
                else:
                    db.session.commit()
                    flash('Ders kayıt penceresi politikası güncellendi.', 'success')
            except Exception:
                db.session.rollback()
                flash('Politika güncellenirken hata oluştu.', 'danger')

    students = User.query.filter_by(role='student').order_by(User.name.asc()).limit(500).all()
    courses = Course.query.order_by(Course.code.asc()).limit(500).all()
    recent_audits = CourseEnrollmentAudit.query.order_by(CourseEnrollmentAudit.created_at.desc()).limit(80).all()

    return render_template(
        'admin_course_registration_window.html',
        policy=policy,
        students=students,
        courses=courses,
        recent_audits=recent_audits,
    )


@app.route('/admin/course-registration-window/override', methods=['POST'])
@role_required('admin')
@permission_required()
def admin_course_registration_override():
    admin_user = db.session.get(User, session.get('user_id'))
    student_id_raw = _normalize_form_text(request.form.get('student_id'), max_length=20)
    course_id_raw = _normalize_form_text(request.form.get('course_id'), max_length=20)
    action = _normalize_form_text(request.form.get('action'), max_length=20)

    if action not in {'add', 'drop'} or not student_id_raw.isdigit() or not course_id_raw.isdigit():
        flash('Geçersiz override isteği.', 'danger')
        return redirect(url_for('admin_course_registration_window'))

    student = db.session.get(Student, int(student_id_raw))
    course = db.session.get(Course, int(course_id_raw))
    if not student or not course:
        flash('Öğrenci veya ders bulunamadı.', 'danger')
        return redirect(url_for('admin_course_registration_window'))

    enrollment = CourseEnrollment.query.filter_by(student_id=student.id, course_id=course.id).first()

    try:
        if action == 'add':
            if not enrollment:
                db.session.add(CourseEnrollment(student_id=student.id, course_id=course.id))
                db.session.flush()
            db.session.add(CourseEnrollmentAudit(
                actor_user_id=admin_user.id,
                student_id=student.id,
                course_id=course.id,
                action='add_override',
                detail=f'admin override add {course.code}',
            ))
            db.session.commit()
            flash(f'Admin ekleme tamamlandı: {course.code}.', 'success')
            return redirect(url_for('admin_course_registration_window'))

        if enrollment:
            db.session.delete(enrollment)
            db.session.flush()
        db.session.add(CourseEnrollmentAudit(
            actor_user_id=admin_user.id,
            student_id=student.id,
            course_id=course.id,
            action='drop_override',
            detail=f'admin override drop {course.code}',
        ))
        db.session.commit()
        flash(f'Admin bırakma tamamlandı: {course.code}.', 'success')
    except Exception:
        db.session.rollback()
        flash('Override işlemi başarısız. Lütfen tekrar deneyin.', 'danger')
    return redirect(url_for('admin_course_registration_window'))


@app.route('/student/transcript')
@role_required('student')
@permission_required()
def student_transcript():
    user = db.session.get(User, session.get('user_id'))
    if not user or not user.students:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    student = user.students[0]
    gpa_4_scale = 0.0
    weighted_credits = 0
    transcript_note = _t('no_graded_data')

    try:
        enrollments = CourseEnrollment.query.filter_by(student_id=student.id).all()
        total_weighted_points = 0.0
        graded_course_count = 0

        for enrollment in enrollments:
            if not enrollment.grades:
                continue
            course_credit = enrollment.course.credit if enrollment.course and enrollment.course.credit else 0
            if course_credit <= 0:
                continue
            avg_grade_point = sum(g.grade_point for g in enrollment.grades) / len(enrollment.grades)
            total_weighted_points += avg_grade_point * course_credit
            weighted_credits += course_credit
            graded_course_count += 1

        if weighted_credits > 0:
            gpa_4_scale = total_weighted_points / weighted_credits
            transcript_note = _t('calculated_from_courses', count=graded_course_count)
    except Exception:
        db.session.rollback()
        transcript_note = _t('transcript_table_not_initialized')

    details = [
        (_t('student_label'), user.name),
        (_t('gpa_4'), f'{gpa_4_scale:.2f}'),
        (_t('weighted_credits'), str(weighted_credits)),
        (_t('note'), transcript_note),
    ]
    return render_template('student_module_page.html', title=_t('transcript'), details=details)


@app.route('/student/academic-calendar')
@role_required('student')
@permission_required()
def student_academic_calendar():
    user = db.session.get(User, session.get('user_id'))
    if not user or not user.students:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    student = user.students[0]
    now = datetime.datetime.now()
    class_ids = [cls.id for cls in student.classes]

    upcoming_count = 0
    if class_ids:
        upcoming_count = AttendanceSession.query.filter(
            AttendanceSession.class_id.in_(class_ids),
            AttendanceSession.date >= now,
        ).count()

    details = [
        (_t('today'), now.strftime('%d-%m-%Y')),
        (_t('upcoming_academic_events'), str(upcoming_count)),
        (_t('term_window'), _t('configured_by_admin')),
        (_t('note'), _t('academic_calendar_note')),
    ]
    return render_template('student_module_page.html', title=_t('academic_calendar'), details=details)


@app.route('/student/exams')
@role_required('student')
@permission_required()
def student_exams():
    user = db.session.get(User, session.get('user_id'))
    if not user or not user.students:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))

    details = [
        (_t('upcoming_exams'), '0'),
        (_t('completed_exams'), '0'),
        (_t('next_exam_date'), _t('not_scheduled')),
        (_t('note'), _t('exam_module_note')),
    ]
    return render_template('student_module_page.html', title=_t('exams'), details=details)


@app.route('/student/history/<int:class_id>')
@role_required('student')
@permission_required()
def student_class_history(class_id):
    user = db.session.get(User, session.get('user_id'))
    if not user:
        session.clear()
        flash('Oturum süresi doldu. Lütfen tekrar giriş yapın.', 'warning')
        return redirect(url_for('login'))
    if not user.students:
        flash('Öğrenci profili bulunamadı. Lütfen destek ekibiyle iletişime geçin.', 'danger')
        return redirect(url_for('logout'))
    student = user.students[0]
    cls = Class.query.get_or_404(class_id)
    denied = ensure_student_class_membership(
        student,
        cls,
        on_fail='student_absence',
        fail_message='You are not authorized to view this class history.',
    )
    if denied:
        return denied

    sessions = AttendanceSession.query.filter_by(class_id=cls.id, confirmed=True).order_by(AttendanceSession.date.desc()).all()
    history_rows = []
    for sess in sessions:
        present = AttendanceRecord.query.filter_by(session_id=sess.id, student_id=student.id, present=True).first() is not None
        history_rows.append({
            'date': sess.date,
            'week': sess.week,
            'present': present,
        })

    return render_template('student_class_history.html', cls=cls, history_rows=history_rows)

# ------------------ CREATE CLASS ------------------
@app.route('/teacher/create_class', methods=['GET', 'POST'])
@role_required('teacher')
@permission_required()
def create_class():
    if request.method == 'POST':
        permission_error = ensure_permission(PERMISSIONS['TEACHER_CLASS_CREATE'], 'create_class')
        if permission_error:
            return permission_error

        class_name = (request.form.get('class_name') or '').strip()
        if not class_name:
            flash("Class name cannot be empty.", "danger")
            return redirect(url_for('create_class'))

        if len(class_name) > 120:
            flash("Class name is too long.", "danger")
            return redirect(url_for('create_class'))

        existing = Class.query.filter_by(name=class_name).first()
        if existing:
            flash("A class with this name already exists.", "warning")
            return redirect(url_for('create_class'))

        # There is no separate teacher model, so we use user.id.
        # Create one fixed QR code per class.
        qr_token = secrets.token_hex(4)
        qr_filename = f"{class_name}_qr_{qr_token}.png"

        qr_folder = os.path.join(app.root_path, "static", "qrcodes")
        if not os.path.exists(qr_folder):
            os.makedirs(qr_folder)

        qr_path = os.path.join(qr_folder, qr_filename)
        img = qrcode.make(_attendance_url(qr_token))
        img.save(qr_path)

        new_class = Class(name=class_name, teacher_id=session['user_id'], qr_token=qr_token, qr_filename=qr_filename)
        db.session.add(new_class)
        db.session.commit()
        flash("Class created.", "success")
        return redirect(url_for('teacher_dashboard'))

    return render_template('create_class.html')

# ------------------ START ATTENDANCE SESSION ------------------
@app.route('/create_session', methods=['POST'])
@role_required('teacher')
@permission_required()
def create_session():
    class_id_raw = _normalize_form_text(request.form.get('class_id'), max_length=20)
    week = _normalize_form_text(request.form.get('week'), max_length=20)
    action = _normalize_form_text(request.form.get('action', 'start'), max_length=30)

    if not class_id_raw.isdigit():
        flash("Geçersiz sınıf kimliği.", "danger")
        return redirect(url_for('teacher_dashboard'))

    if not week:
        # For QR-open flow, allow quick launch by assigning today's label.
        if action == 'start_and_show_qr':
            week = datetime.datetime.now().strftime('%Y-%m-%d')
        else:
            flash("Week is required.", "danger")
            return redirect(url_for('teacher_dashboard'))

    if not re.match(r'^[A-Za-z0-9._ -]+$', week):
        flash("Week contains invalid characters.", "danger")
        return redirect(url_for('teacher_dashboard'))

    if action not in {'start', 'start_and_show_qr'}:
        action = 'start'

    class_id = int(class_id_raw) if class_id_raw and class_id_raw.isdigit() else None
    cls = db.session.get(Class, class_id) if class_id is not None else None
    if not cls:
        flash("Sınıf bulunamadı.", "danger")
        return redirect(url_for('teacher_dashboard'))
    denied = ensure_teacher_class_ownership(
        cls,
        on_fail='teacher_dashboard',
        fail_message='You are not allowed to start attendance for this class.',
    )
    if denied:
        return denied

    # Deactivate previous active sessions for this class.
    AttendanceSession.query.filter_by(class_id=class_id, active=True).update({'active': False})

    new_session = AttendanceSession(
        class_id=class_id,
        date=datetime.datetime.now(),
        qr_token=secrets.token_hex(4),
        qr_filename='',
        name=None,
        week=week,
        active=True
    )
    db.session.add(new_session)
    db.session.commit()

    flash("Attendance session started.", "success")
    if action == 'start_and_show_qr':
        return redirect(url_for('view_qr', token=cls.qr_token))
    return redirect(url_for('teacher_dashboard'))

# ------------------ VIEW QR ------------------
@app.route('/view_qr/<token>')
@role_required('teacher')
@permission_required()
def view_qr(token):
    # Token is the class-level fixed QR token.
    cls = Class.query.filter_by(qr_token=token).first()
    if not cls:
        flash("QR not found.", "danger")
        return redirect(url_for('teacher_dashboard'))
    denied = ensure_teacher_class_ownership(
        cls,
        on_fail='teacher_dashboard',
        fail_message='You are not allowed to view this QR.',
    )
    if denied:
        return denied

    return render_template("view_qr.html", qr_filename=cls.qr_filename, token=token, attendance_url=_attendance_url(token))

# ------------------ CLASS DETAIL ------------------
@app.route('/teacher/class/<int:class_id>')
@role_required('teacher')
@permission_required()
def class_detail(class_id):
    cls = Class.query.get_or_404(class_id)
    denied = ensure_teacher_class_ownership(
        cls,
        on_fail='teacher_dashboard',
        fail_message='You are not allowed to view this class.',
    )
    if denied:
        return denied

    students_data = []
    session_ids = [session.id for session in cls.sessions]
    total_sessions = len(session_ids)
    attended_by_student = {}

    if session_ids:
        attended_rows = (
            db.session.query(AttendanceRecord.student_id, func.count(AttendanceRecord.id))
            .filter(
                AttendanceRecord.session_id.in_(session_ids),
                AttendanceRecord.present == True,
            )
            .group_by(AttendanceRecord.student_id)
            .all()
        )
        attended_by_student = {student_id: count for student_id, count in attended_rows}

    for student in cls.students:
        attended = int(attended_by_student.get(student.id, 0))

        absence = total_sessions - attended
        passed = (attended / total_sessions) >= 0.7 if total_sessions > 0 else False

        students_data.append({
            'name': student.user.name,
            'attended': attended,
            'absence': absence,
            'passed': passed
        })

    return render_template('class_detail.html', class_obj=cls, students_data=students_data)

# ------------------ ATTENDANCE ------------------
@app.route('/attendance/<token>')
@role_required('student')
@permission_required()
def mark_attendance(token):
    user_id = session['user_id']
    student = Student.query.get_or_404(user_id)

    # Token is the class-level fixed QR token.
    cls = Class.query.filter_by(qr_token=token).first()
    if not cls:
        flash('Geçersiz QR kodu!', 'danger')
        return redirect(url_for('student_absence'))
    denied = ensure_student_class_membership(
        student,
        cls,
        on_fail='student_absence',
        fail_message='You are not enrolled in this class.',
    )
    if denied:
        return denied

    active_session = AttendanceSession.query.filter_by(class_id=cls.id, active=True).order_by(AttendanceSession.date.desc()).first()
    if not active_session:
        flash('Bu sınıf için aktif yoklama oturumu yok. Öğretmeninizden başlatmasını isteyin.', 'warning')
        return redirect(url_for('student_absence'))

    # Reject scans outside the allowed time window (QR security layer).
    if datetime.datetime.now() > _session_deadline(active_session):
        active_session.active = False
        active_session.confirmed = True
        db.session.commit()
        flash('Yoklama süresi doldu. Oturum kapatıldı.', 'warning')
        return redirect(url_for('student_absence'))

    existing_record = AttendanceRecord.query.filter_by(
        student_id=student.id,
        session_id=active_session.id
    ).first()

    if existing_record:
        flash('Yoklamanız zaten işaretlendi!', 'info')
    else:
        new_record = AttendanceRecord(
            student_id=student.id,
            session_id=active_session.id,
            present=True
        )
        db.session.add(new_record)
        db.session.commit()
        return render_template('attendance_success.html', cls=cls, active_session=active_session)

    return redirect(url_for('student_absence'))

# ------------------ UPDATE ATTENDANCE ------------------
@app.route('/teacher/session/<int:session_id>/update_attendance', methods=['POST'])
@role_required('teacher')
@permission_required()
def update_attendance(session_id):
    session_obj = AttendanceSession.query.get_or_404(session_id)
    denied = ensure_teacher_session_ownership(session_obj, on_fail='login')
    if denied:
        return denied
    cls = session_obj.class_obj

    raw_present_ids = request.form.getlist('present')
    present_ids = set()
    for raw_id in raw_present_ids:
        raw_id = (raw_id or '').strip()
        if raw_id.isdigit():
            present_ids.add(int(raw_id))

    valid_student_ids = {student.id for student in cls.students}
    present_ids = {student_id for student_id in present_ids if student_id in valid_student_ids}

    for student in cls.students:
        record = AttendanceRecord.query.filter_by(student_id=student.id, session_id=session_obj.id).first()
        if student.id in present_ids:
            if not record:
                db.session.add(AttendanceRecord(student_id=student.id, session_id=session_obj.id, present=True))
            else:
                record.present = True
        else:
            if record:
                db.session.delete(record)

    # If stop is requested, close and confirm the session.
    stop = request.form.get('stop')
    if stop == '1':
        session_obj.active = False
        session_obj.confirmed = True
        flash('Yoklama tamamlandı ve kaydedildi.', 'success')
    else:
        flash('Yoklama güncellendi.', 'success')

    db.session.commit()
    return redirect(url_for('teacher_dashboard'))


# ------------------ STOP ATTENDANCE SESSION ------------------
@app.route('/teacher/session/<int:session_id>/stop')
@role_required('teacher')
@permission_required()
def stop_session(session_id):
    session_obj = AttendanceSession.query.get_or_404(session_id)
    denied = ensure_teacher_session_ownership(session_obj, on_fail='login')
    if denied:
        return denied
    cls = session_obj.class_obj

    session_obj.active = False
    session_obj.confirmed = True
    db.session.commit()
    flash('Yoklama oturumu tamamlandı ve kaydedildi.', 'success')
    return redirect(url_for('teacher_dashboard'))


# ------------------ ERROR HANDLERS ------------------
@app.errorhandler(404)
def handle_not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def handle_internal_error(error):
    # Roll back pending transactions so the app can continue serving requests.
    db.session.rollback()
    app.logger.exception('Unhandled server error: %s', error)
    return render_template('500.html'), 500


# ------------------ RUN ------------------
if __name__ == "__main__":
    debug_mode = os.getenv('FLASK_DEBUG', '1') == '1'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)




