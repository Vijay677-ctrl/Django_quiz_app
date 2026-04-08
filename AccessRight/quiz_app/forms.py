from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Quiz, Question
from django.utils import timezone

class TeacherSignUpForm(UserCreationForm):
    subject = forms.CharField(max_length=50, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'subject')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.IS_TEACHER
        if commit:
            user.save()
        return user

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'subject', 'topic', 'quiz_time', 'last_date']
        widgets = {
            'last_date': forms.DateInput(attrs={'type': 'date'}),
        }
    def clean_quiz_time(self):
        quiz_time = self.cleaned_data.get('quiz_time')
        if quiz_time is not None and quiz_time <= 0:
            raise forms.ValidationError("Quiz time must be a positive number.")
        return quiz_time

    def clean_last_date(self):
        last_date = self.cleaned_data.get('last_date')
        # Check if date is in the past (comparing only the date part)
        if last_date and last_date < timezone.now().date():
            raise forms.ValidationError("The last date to submit cannot be in the past.")
        return last_date


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'option_1', 'option_2', 'option_3', 'option_4', 'correct_option']