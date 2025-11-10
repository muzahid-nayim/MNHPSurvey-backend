# surveys/urls.py
from django.urls import path
from .views import (
    # Survey endpoints
    SurveyListCreateView,
    SurveyDetailView,
    SurveyStatusUpdateView,
    
    # Question endpoints
    QuestionCreateView,
    QuestionListView,
    QuestionDetailView,
    
    # Option endpoints
    QuestionOptionCreateView,
    QuestionOptionDetailView,
    
    # Invitation endpoints
    SendInvitationsView,
    InvitationListView,
    
    # Public survey taking endpoints
    TakeSurveyView,
    SubmitSurveyResponseView,
    
    # Response viewing endpoints
    SurveyResponseListView,
    SurveyResponseDetailView,
)

"""
URL Pattern Explanation:

Structure:
/api/surveys/                           - List/Create surveys
/api/surveys/<id>/                      - Get/Update/Delete survey
/api/surveys/<id>/questions/            - Add/List questions
/api/surveys/<id>/questions/<id>/       - Update/Delete question
/api/surveys/<id>/questions/<id>/options/    - Add option
/api/surveys/<id>/questions/<id>/options/<id>/ - Update/Delete option
/api/surveys/<id>/invite/               - Send invitations
/api/surveys/<id>/invitations/          - List invitations
/api/surveys/<id>/status/               - Update survey status
/api/surveys/<id>/responses/            - View all responses
/api/surveys/<id>/responses/<id>/       - View single response
/api/surveys/take/<id>/                 - Public: Get survey to take
/api/surveys/submit/<id>/               - Public: Submit response
"""

urlpatterns = [
    # ==========================================
    # SURVEY MANAGEMENT (Owner only)
    # ==========================================
    
    # List all surveys and create new survey
    path('', SurveyListCreateView.as_view(), name='survey-list-create'),
    
    # Get/Update/Delete specific survey
    path('<uuid:id>/', SurveyDetailView.as_view(), name='survey-detail'),
    
    # Update survey status (draft/active/closed)
    path('<uuid:survey_id>/status/', SurveyStatusUpdateView.as_view(), name='survey-status'),
    
    
    # ==========================================
    # QUESTION MANAGEMENT (Owner only)
    # ==========================================
    
    # Add question to survey and list all questions
    path('<uuid:survey_id>/questions/', QuestionCreateView.as_view(), name='question-create'),
    path('<uuid:survey_id>/questions/list/', QuestionListView.as_view(), name='question-list'),
    
    # Get/Update/Delete specific question
    path('<uuid:survey_id>/questions/<uuid:id>/', QuestionDetailView.as_view(), name='question-detail'),
    
    
    # ==========================================
    # QUESTION OPTION MANAGEMENT (Owner only)
    # ==========================================
    
    # Add option to question
    path('<uuid:survey_id>/questions/<uuid:question_id>/options/', 
         QuestionOptionCreateView.as_view(), 
         name='option-create'),
    
    # Get/Update/Delete specific option
    path('<uuid:survey_id>/questions/<uuid:question_id>/options/<uuid:id>/', 
         QuestionOptionDetailView.as_view(), 
         name='option-detail'),
    
    
    # ==========================================
    # INVITATION MANAGEMENT (Owner only)
    # ==========================================
    
    # Send invitations to emails
    path('<uuid:survey_id>/invite/', SendInvitationsView.as_view(), name='survey-invite'),
    
    # List all invitations for survey
    path('<uuid:survey_id>/invitations/', InvitationListView.as_view(), name='invitation-list'),
    
    
    # ==========================================
    # RESPONSE VIEWING (Owner only)
    # ==========================================
    
    # List all responses for survey
    path('<uuid:survey_id>/responses/', SurveyResponseListView.as_view(), name='response-list'),
    
    # View single response detail
    path('<uuid:survey_id>/responses/<uuid:id>/', 
         SurveyResponseDetailView.as_view(), 
         name='response-detail'),
    
    
    # ==========================================
    # PUBLIC ENDPOINTS (Survey takers)
    # ==========================================
    
    # Get survey for taking (public access)
    path('take/<uuid:survey_id>/', TakeSurveyView.as_view(), name='take-survey'),
    
    # Submit survey response (public access)
    path('submit/<uuid:survey_id>/', SubmitSurveyResponseView.as_view(), name='submit-survey'),
]