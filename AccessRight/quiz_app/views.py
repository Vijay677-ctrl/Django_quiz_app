from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, F, Max
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta

# Ensure these models and forms exist in your project
from .models import User, Quiz, Question, Result, StudentAnswer
from .forms import TeacherSignUpForm, QuizForm, QuestionForm


# --- AUTHENTICATION & DISPATCH VIEWS ---

def login_selection(request):
    return render(request, 'login_selection.html')


def teacher_register(request):
    if request.method == 'POST':
        form = TeacherSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('teacher_dashboard')
    else:
        form = TeacherSignUpForm()
    return render(request, 'teacher_register.html', {'form': form})


@login_required
def dispatch_dashboard(request):
    user = request.user
    if user.role == User.IS_TEACHER:
        return redirect('teacher_dashboard')
    elif user.role == User.IS_STUDENT:
        return redirect('student_dashboard')
    elif user.role == User.IS_PARENT:
        return redirect('parent_dashboard')
    elif user.role == User.IS_PRINCIPAL or user.is_superuser:
        return redirect('admin_dashboard')
    return redirect('login_selection')


# --- PRINCIPAL/ADMIN VIEWS ---

from django.db.models import Avg
from django.db.models.functions import Round  # Import the Database Round function

# --- Updated Student Views in views.py ---

@login_required
def attempt_quiz_one_by_one(request, quiz_id, question_id=None):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    student = request.user

    # MODIFIED: Check if a result already exists and handle re-attempts
    existing_result = Result.objects.filter(student=student, quiz=quiz).first()
    if existing_result:
        # Check if the existing score is a Pass (more than 50%)
        if existing_result.score > (existing_result.total_questions / 2):
            return redirect('student_dashboard')
        else:
            # If they failed, clear old answers ONLY when starting from the beginning
            if question_id is None:
                StudentAnswer.objects.filter(student=student, quiz=quiz).delete()
                # Reset the session start time for a fresh countdown
                session_key = f'quiz_start_time_{quiz_id}'
                if session_key in request.session:
                    del request.session[session_key]

    session_key = f'quiz_start_time_{quiz_id}'
    if session_key not in request.session:
        request.session[session_key] = timezone.now().isoformat()

    start_time = timezone.datetime.fromisoformat(request.session[session_key])
    time_remaining = (start_time + timedelta(minutes=quiz.quiz_time)) - timezone.now()

    if time_remaining.total_seconds() <= 0:
        return redirect('take_quiz', quiz_id=quiz.id)

    if request.method == 'POST' and question_id:
        current_question = get_object_or_404(Question, id=question_id)
        selected_option = request.POST.get(str(current_question.id))

        if selected_option:
            StudentAnswer.objects.update_or_create(
                student=student, quiz=quiz, question=current_question,
                defaults={'selected_option': int(selected_option)}
            )

        answered_ids = StudentAnswer.objects.filter(student=student, quiz=quiz).values_list('question__id', flat=True)
        next_q = quiz.questions.exclude(id__in=answered_ids).order_by('id').first()

        if next_q:
            return redirect('attempt_next_question', quiz_id=quiz.id, question_id=next_q.id)
        return redirect('take_quiz', quiz_id=quiz.id)

    if question_id is None:
        first_q = quiz.questions.order_by('id').first()
        return redirect('attempt_next_question', quiz_id=quiz.id, question_id=first_q.id)

    question = get_object_or_404(Question, id=question_id, quiz=quiz)
    return render(request, 'quiz_app/attempt_assignment.html', {
        'quiz': quiz,
        'question': question,
        'question_number': quiz.questions.filter(id__lte=question.id).count(),
        'total_questions': quiz.questions.count(),
        'time_remaining_seconds': time_remaining.total_seconds(),
    })

# --- Analytics Logic Update for admin_dashboard ---
@login_required
def admin_dashboard(request):
    if request.user.role != User.IS_PRINCIPAL and not request.user.is_superuser:
        return redirect('dispatch_dashboard')

    students_count = User.objects.filter(role=User.IS_STUDENT).count()
    teachers_count = User.objects.filter(role=User.IS_TEACHER).count()
    total_quizzes = Quiz.objects.count()

    # Annotation remains clean because take_quiz deletes the old record per student
    performance = Result.objects.values('quiz__subject').annotate(
        avg_score=Round(Avg('score'), 2)
    )

    context = {
        'students_count': students_count,
        'teachers_count': teachers_count,
        'total_quizzes': total_quizzes,
        'performance': performance,
        'students': User.objects.filter(role=User.IS_STUDENT),
        'teachers': User.objects.filter(role=User.IS_TEACHER),
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def student_detail_admin(request, user_id):
    student = get_object_or_404(User, id=user_id)
    results = Result.objects.filter(student=student).order_by('-date_taken')
    return render(request, 'student_detail_admin.html', {'student': student, 'results': results})


@login_required
def teacher_detail_admin(request, user_id):
    teacher = get_object_or_404(User, id=user_id)
    quizzes = Quiz.objects.filter(teacher=teacher).order_by('-created_at')
    return render(request, 'teacher_detail_admin.html', {'teacher': teacher, 'quizzes': quizzes})


# --- TEACHER VIEWS ---

@login_required
def teacher_dashboard(request):
    if request.user.role != User.IS_TEACHER:
        return redirect('dispatch_dashboard')
    quizzes = Quiz.objects.filter(teacher=request.user)
    students = User.objects.filter(role=User.IS_STUDENT)
    pending_reviews_count = Result.objects.filter(quiz__teacher=request.user, is_reviewed=False).count()
    return render(request, 'teacher_dashboard.html', {
        'quizzes': quizzes,
        'students': students,
        'pending_reviews': pending_reviews_count
    })


@login_required
def create_quiz(request):
    if request.user.role != User.IS_TEACHER:
        return redirect('dispatch_dashboard')

    # Get the teacher's assigned subject from their profile
    teacher_subject = getattr(request.user, 'subject', 'General')

    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.teacher = request.user
            # Force the subject to be the teacher's subject
            quiz.subject = teacher_subject
            quiz.save()
            return redirect('add_question', quiz_id=quiz.id)
    else:
        # Pass the teacher's subject as the initial value
        form = QuizForm(initial={'subject': teacher_subject})

    return render(request, 'create_quiz.html', {'form': form, 'teacher_subject': teacher_subject})


@login_required
def add_question(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, teacher=request.user)
    next_question_number = quiz.questions.count() + 1
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            question.save()
            if 'add_another' in request.POST:
                return redirect('add_question', quiz_id=quiz.id)
            return redirect('teacher_dashboard')
    else:
        form = QuestionForm()
    return render(request, 'add_question.html', {'form': form, 'quiz': quiz, 'next_number': next_question_number})


import json  # Add this at the top with other imports

@login_required
def quiz_results_teacher(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    all_results = Result.objects.filter(quiz=quiz)
    all_results.update(is_reviewed=True)

    student_performance = []
    for result in all_results:
        student_performance.append({
            'student_name': result.student.get_full_name() or result.student.username,
            'score': result.score,
            'total_questions': result.total_questions,
            'percentage': round((result.score / result.total_questions) * 100, 1) if result.total_questions > 0 else 0,
            'date_taken': result.date_taken,
        })

    chart_labels = []
    chart_data = []

    # Improved loop to generate Q1, Q2 labels
    for i, q in enumerate(quiz.questions.all(), 1):
        total_attempts = StudentAnswer.objects.filter(quiz=quiz, question=q).count()
        correct_count = StudentAnswer.objects.filter(quiz=quiz, question=q, selected_option=q.correct_option).count()

        mistake_perc = 0
        if total_attempts > 0:
            mistake_perc = round(((total_attempts - correct_count) / total_attempts) * 100, 1)

        chart_labels.append(f"Q{i}")
        chart_data.append(mistake_perc)

    context = {
        'quiz': quiz,
        'results': all_results,
        'student_performance': student_performance,
        'sorted_students': sorted(student_performance, key=lambda x: x['score'], reverse=True),
        # FIX: Convert lists to JSON strings so the template handles them easily
        'chart_labels_json': json.dumps(chart_labels),
        'chart_data_json': json.dumps(chart_data),
    }
    return render(request, 'quiz_results_teacher.html', context)
# --- STUDENT VIEWS ---

@login_required
def student_dashboard(request):
    if request.user.role != User.IS_STUDENT:
        return redirect('dispatch_dashboard')

    now = timezone.now().date()

    # Get successful attempts (Pass)
    passed_quiz_ids = Result.objects.filter(
        student=request.user,
        score__gt=F('total_questions') / 2
    ).values_list('quiz_id', flat=True)

    # Quizzes are available if they haven't been passed AND deadline hasn't passed
    available_quizzes = Quiz.objects.filter(last_date__gte=now).exclude(id__in=passed_quiz_ids)

    completed_results = Result.objects.filter(student=request.user).order_by('-date_taken')

    new_assignments_data = []
    for assignment in available_quizzes:
        new_assignments_data.append({
            'id': assignment.id,
            'name': assignment.title,
            'topic': assignment.topic,
            'quiz_time': assignment.quiz_time,
            'last_date': assignment.last_date,
            'teacher_username': assignment.teacher.username,
            'questions_count': assignment.questions.count(),
        })

    return render(request, 'student_dashboard.html', {
        'new_assignments': new_assignments_data,
        'completed': completed_results
    })


@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    student = request.user

    # Handle Time Calculation BEFORE clearing session
    session_key = f'quiz_start_time_{quiz_id}'
    time_taken_display = "N/A"
    if session_key in request.session:
        start_time = timezone.datetime.fromisoformat(request.session[session_key])
        elapsed = timezone.now() - start_time
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        time_taken_display = f"{minutes}m {seconds}s"
        del request.session[session_key]

    # Scoring logic
    score = 0
    total = quiz.questions.count()
    student_answers = StudentAnswer.objects.filter(student=student, quiz=quiz)
    for ans in student_answers:
        if ans.question.correct_option == ans.selected_option:
            score += 1

    percentage = round((score / total) * 100, 1) if total > 0 else 0

    # Logic for Retakes: Delete previous failed results
    existing_result = Result.objects.filter(student=student, quiz=quiz).first()
    if existing_result:
        existing_result.delete()

    new_result = Result.objects.create(
        student=student,
        quiz=quiz,
        score=score,
        total_questions=total
    )

    # Pass the time taken to the next view via session
    request.session['last_quiz_time_taken'] = time_taken_display
    return redirect('quiz_score_card', result_id=new_result.id)


@login_required
def quiz_score_card(request, result_id):
    result = get_object_or_404(Result, id=result_id, student=request.user)
    percentage = round((result.score / result.total_questions) * 100, 1) if result.total_questions else 0

    # Retrieve time taken from session
    time_taken = request.session.pop('last_quiz_time_taken', 'N/A')

    return render(request, 'quiz_app/score_card.html', {
        'result': result,
        'percentage': percentage,
        'time_taken': time_taken
    })


@login_required
def student_quiz_review(request, result_id):
    result = get_object_or_404(Result, id=result_id, student=request.user)
    quiz = result.quiz
    review_data = []

    for q in quiz.questions.all():
        student_ans = StudentAnswer.objects.filter(
            student=request.user,
            quiz=quiz,
            question=q
        ).first()

        # We pass these as strings to avoid template comparison issues
        selected = str(student_ans.selected_option) if student_ans else None
        correct = str(q.correct_option)

        review_data.append({
            'question': q,
            'selected_option': selected,
            'correct_option': correct,
            'is_correct': selected == correct
        })

    # Calculate percentage for the Pass/Fail header logic
    percentage = (result.score / result.total_questions) * 100 if result.total_questions > 0 else 0

    return render(request, 'quiz_review.html', {
        'quiz': quiz,
        'result': result,
        'review_data': review_data,
        'percentage': percentage
    })
# --- PARENT VIEWS ---

@login_required
def parent_dashboard(request):
    if request.user.role != User.IS_PARENT:
        return redirect('dispatch_dashboard')
    child = getattr(request.user, 'child', None)
    if not child:
        return render(request, 'parent_dashboard.html', {'error': 'No student linked.'})

    # FIXED: Coalesce and F-expression logic for safe division
    student_stats = Result.objects.filter(student=child).values('quiz__subject').annotate(
        avg_score=Coalesce(Avg(F('score') * 100.0 / F('total_questions')), 0.0)
    )
    class_stats = Result.objects.values('quiz__subject').annotate(
        avg_score=Coalesce(Avg(F('score') * 100.0 / F('total_questions')), 0.0)
    )

    subjects = [item['quiz__subject'] for item in student_stats]
    student_averages = [round((item['avg_score'] or 0), 1) for item in student_stats]
    class_map = {item['quiz__subject']: item['avg_score'] for item in class_stats}
    class_averages = [round((class_map.get(sub, 0) or 0), 1) for sub in subjects]

    return render(request, 'parent_dashboard.html', {
        'child': child, 'results': Result.objects.filter(student=child).order_by('-date_taken'),
        'subjects': subjects, 'student_averages': student_averages, 'class_averages': class_averages,
    })


@login_required
def teacher_quiz_questions_review(request, quiz_id):
    # Ensure only teachers or admins can access this
    if request.user.role not in [User.IS_TEACHER, User.IS_PRINCIPAL] and not request.user.is_superuser:
        return redirect('dispatch_dashboard')

    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()

    return render(request, 'teacher_questions_review.html', {
        'quiz': quiz,
        'questions': questions
    })


@login_required
def edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    quiz = question.quiz

    # Security: Ensure only the teacher who owns the quiz can edit it
    if request.user != quiz.teacher and not request.user.is_superuser:
        return redirect('dispatch_dashboard')

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            # Redirect back to the review page after saving
            return redirect('teacher_questions_review', quiz_id=quiz.id)
    else:
        form = QuestionForm(instance=question)

    return render(request, 'edit_question.html', {
        'form': form,
        'quiz': quiz,
        'question': question
    })


@login_required
def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    quiz = question.quiz

    # Security: Only the quiz owner or admin can delete
    if request.user != quiz.teacher and not request.user.is_superuser:
        return redirect('dispatch_dashboard')

    if request.method == 'POST':
        question.delete()
        # Return to the review page after deletion
        return redirect('teacher_questions_review', quiz_id=quiz.id)

    return redirect('teacher_questions_review', quiz_id=quiz.id)


@login_required
def add_question(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, teacher=request.user)
    next_question_number = quiz.questions.count() + 1

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            question.save()

            # If they click 'Add Another', keep them on the form
            if 'add_another' in request.POST:
                return redirect('add_question', quiz_id=quiz.id)

            # UPDATED: Redirect back to the Question Review list
            return redirect('teacher_questions_review', quiz_id=quiz.id)
    else:
        form = QuestionForm()

    return render(request, 'add_question.html', {
        'form': form,
        'quiz': quiz,
        'next_number': next_question_number
    })