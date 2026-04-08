from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Quiz, Question, Result, StudentAnswer


# --- 1. Custom User Administration ---
class CustomUserAdmin(UserAdmin):
    model = User
    # Display 'role' and 'subject' in the user list view
    list_display = ['username', 'email', 'role', 'subject', 'is_staff']

    # Organize custom fields into a clear section in the edit form
    fieldsets = UserAdmin.fieldsets + (
        ('AssessRight Permissions', {'fields': ('role', 'subject', 'child')}),
    )

    # Ensure these fields are available when creating a user via admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('AssessRight Permissions', {'fields': ('role', 'subject', 'child')}),
    )


# Register Custom User
admin.site.register(User, CustomUserAdmin)


# --- 2. Quiz and Question Management ---
class QuestionInline(admin.TabularInline):
    """Allows adding questions directly inside the Quiz page."""
    model = Question
    extra = 1


class QuizAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]
    list_display = ('title', 'subject', 'teacher', 'quiz_time', 'created_at')
    list_filter = ('subject', 'teacher')


# --- 3. Register Remaining Models ---
admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question)  # Kept for direct editing if needed
admin.site.register(Result)
admin.site.register(StudentAnswer)  # Added to track individual student responses