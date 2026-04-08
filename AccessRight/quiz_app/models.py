from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    IS_TEACHER = 'teacher'
    IS_STUDENT = 'student'
    IS_PARENT = 'parent'
    IS_PRINCIPAL = 'principal'

    ROLE_CHOICES = [
        (IS_TEACHER, 'Teacher'),
        (IS_STUDENT, 'Student'),
        (IS_PARENT, 'Parent'),
        (IS_PRINCIPAL, 'Principal'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=IS_STUDENT)
    subject = models.CharField(max_length=50, blank=True, null=True)
    child = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='parents',
                              limit_choices_to={'role': IS_STUDENT})


class Quiz(models.Model):
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=50)
    topic = models.CharField(max_length=100)  # already added
    quiz_time = models.IntegerField(help_text="Duration in minutes")  # ← NEW FIELD
    last_date = models.DateField(help_text="Last date to submit")     # ← NEW FIELD
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': User.IS_TEACHER})
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.subject} - {self.topic}"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)
    option_1 = models.CharField(max_length=200)
    option_2 = models.CharField(max_length=200)
    option_3 = models.CharField(max_length=200)
    option_4 = models.CharField(max_length=200)
    correct_option = models.IntegerField(choices=[(1, 'Option 1'), (2, 'Option 2'), (3, 'Option 3'), (4, 'Option 4')])


class Result(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': User.IS_STUDENT})
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField()
    total_questions = models.IntegerField()
    date_taken = models.DateTimeField(auto_now_add=True)
    is_reviewed = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.student.username} - {self.quiz.title}: {self.score}"


# --- NEW MODEL TO STORE ANSWERS ---
class StudentAnswer(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.IntegerField()

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title} - Q{self.question.id}"