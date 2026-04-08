from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth & Landing
    path('', views.login_selection, name='login_selection'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/teacher/', views.teacher_register, name='teacher_register'),
    path('dashboard/', views.dispatch_dashboard, name='dispatch_dashboard'),

    # Admin/Principal
    path('admin-portal/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-portal/student/<int:user_id>/', views.student_detail_admin, name='student_detail_admin'),
    path('admin-portal/teacher/<int:user_id>/', views.teacher_detail_admin, name='teacher_detail_admin'),

    # Teacher
    path('teacher-portal/', views.teacher_dashboard, name='teacher_dashboard'),
    path('quiz/create/', views.create_quiz, name='create_quiz'),
    path('quiz/<int:quiz_id>/add-question/', views.add_question, name='add_question'),
    path('quiz/<int:quiz_id>/results/', views.quiz_results_teacher, name='quiz_results_teacher'),
    path('attempt/<int:quiz_id>/', views.attempt_quiz_one_by_one, name='attempt_assignment'),
    path('attempt/<int:quiz_id>/<int:question_id>/', views.attempt_quiz_one_by_one, name='attempt_next_question'),
    path('quiz/<int:quiz_id>/questions-review/', views.teacher_quiz_questions_review, name='teacher_questions_review'),
    path('question/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    path('question/<int:question_id>/delete/', views.delete_question, name='delete_question'),
    # Student
    path('student-portal/', views.student_dashboard, name='student_dashboard'),
    path('quiz/<int:quiz_id>/take/', views.take_quiz, name='take_quiz'),
    # NEW: Review Page
    path('student-portal/review/<int:result_id>/', views.student_quiz_review, name='student_quiz_review'),
    path('submit/<int:quiz_id>/', views.take_quiz, name='submit_assignment'),
    path('result/<int:result_id>/scorecard/', views.quiz_score_card, name='quiz_score_card'),

    # Parent
    path('parent-portal/', views.parent_dashboard, name='parent_dashboard'),
]