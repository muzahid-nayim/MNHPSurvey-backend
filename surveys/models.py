# surveys/models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class Survey(models.Model):
    """
    Main Survey Model
    - Stores survey title, description, settings
    """
    
    # Access Control Types
    ACCESS_TYPES = [
        ('public_anonymous', 'Public - Anonymous'),      # Anyone can join, responses are anonymous
        ('public_authenticated', 'Public - Login Required'),  # Must login, can see who responded
        ('private_invited', 'Private - Invited Only'),   # Only specific emails can join
    ]
    
    # Display Modes (how questions appear)
    DISPLAY_MODES = [
        ('one_by_one', 'One Question at a Time'),  # Like Google Forms
        ('show_all', 'Show All Questions'),         # All questions on one page
        ('paginated', 'Custom Pages'),              # Show X questions per page
    ]
    
    # Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),      # Still creating
        ('active', 'Active'),    # Published and accepting responses
        ('closed', 'Closed'),    # No longer accepting responses
    ]
    
    # Basic Info
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='surveys')
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Access Control
    access_type = models.CharField(max_length=30, choices=ACCESS_TYPES, default='public_anonymous')
    
    # Display Settings
    display_mode = models.CharField(max_length=20, choices=DISPLAY_MODES, default='show_all')
    questions_per_page = models.IntegerField(default=5)  # Used when display_mode='paginated'
    
    # Settings
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    allow_multiple_responses = models.BooleanField(default=False)  # Can same user submit multiple times?
    show_progress_bar = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'surveys'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class Question(models.Model):
    """
    Question Model
    - Each question belongs to a survey
    - Can be single choice or multiple choice
    """
    
    # Question Types
    QUESTION_TYPES = [
        ('single_choice', 'Single Choice'),      # Radio buttons (select one)
        ('multiple_choice', 'Multiple Choice'),  # Checkboxes (select many)
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    
    question_text = models.TextField()  # The actual question
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='single_choice')
    
    # Ordering (which question comes first)
    order = models.IntegerField(default=0)
    
    # Validation
    is_required = models.BooleanField(default=False)  # Must answer or can skip?
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'questions'
        ordering = ['order']  # Questions ordered by 'order' field
    
    def __str__(self):
        return f"{self.survey.title} - Q{self.order}: {self.question_text[:50]}"


class QuestionOption(models.Model):
    """
    Question Option Model
    - The choices for a question
    - Example: For "What's your favorite color?"
      Options: Red, Blue, Green, Yellow
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    
    option_text = models.CharField(max_length=500)  # The choice text
    order = models.IntegerField(default=0)  # Order of options
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'question_options'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.question.question_text[:30]} - Option: {self.option_text}"	



class SurveyInvitation(models.Model):
    """
    Survey Invitation Model
    - For 'private_invited' surveys
    - Only invited emails can access the survey
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),      # Email sent, not opened yet
        ('opened', 'Opened'),        # User opened the survey
        ('completed', 'Completed'),  # User submitted response
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='invitations')
    
    email = models.EmailField()
    token = models.UUIDField(unique=True, default=uuid.uuid4)  # Unique access token
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Tracking
    sent_at = models.DateTimeField(auto_now_add=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'survey_invitations'
        unique_together = ['survey', 'email']  # Can't invite same email twice
    
    def __str__(self):
        return f"{self.survey.title} - Invited: {self.email}"



class SurveyResponse(models.Model):
    """
    Survey Response Model
    - One record for each survey submission
    - Tracks who submitted and when
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='responses')
    
    # Identity Tracking (depends on access_type)
    respondent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # If logged in
    invitation = models.ForeignKey(SurveyInvitation, on_delete=models.SET_NULL, null=True, blank=True)  # If invited
    
    # Anonymous Tracking (for public_anonymous)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    is_complete = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'survey_responses'
        ordering = ['-started_at']
    
    def __str__(self):
        respondent_info = self.respondent.email if self.respondent else 'Anonymous'
        return f"{self.survey.title} - Response by {respondent_info}"




class Answer(models.Model):
    """
    Answer Model
    - Stores answers to questions
    - For single choice: one Answer with one selected_option
    - For multiple choice: one Answer with multiple selected_options (through AnswerSelection)
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    response = models.ForeignKey(SurveyResponse, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'answers'
        unique_together = ['response', 'question']  # One answer per question per response
    
    def __str__(self):
        return f"Answer to: {self.question.question_text[:30]}"


class AnswerSelection(models.Model):
    """
    Answer Selection Model
    - Links Answer to QuestionOption(s)
    - For single choice: one AnswerSelection
    - For multiple choice: multiple AnswerSelections
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name='selections')
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'answer_selections'
        unique_together = ['answer', 'selected_option']  # Can't select same option twice
    
    def __str__(self):
        return f"Selection: {self.selected_option.option_text}"


