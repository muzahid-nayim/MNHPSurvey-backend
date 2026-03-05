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
	# Allowed Email Management endpoints
	AllowedEmailListCreateView,
	AllowedEmailDetailView,
	SurveyAllowedEmailsView,
	# Public survey taking endpoints
	TakeSurveyView,
	SubmitSurveyResponseView,
	# Response viewing endpoints
	SurveyResponseListView,
	SurveyResponseDetailView,
)



urlpatterns = [

	# ==========================================
	# SURVEY MANAGEMENT (Owner only)
	# ==========================================
	# List all surveys and create new survey
	path("", SurveyListCreateView.as_view(), name="survey-list-create"),
	# Get/Update/Delete specific survey
	path("<uuid:id>/", SurveyDetailView.as_view(), name="survey-detail"),
	# Update survey status (draft/active/closed)
	path(
		"<uuid:survey_id>/status/",
		SurveyStatusUpdateView.as_view(),
		name="survey-status",
	),
	# ==========================================
	# QUESTION MANAGEMENT (Owner only)
	# ==========================================
	# Add question to survey and list all questions
	path(
		"<uuid:survey_id>/questions/",
		QuestionCreateView.as_view(),
		name="question-create",
	),
	path(
		"<uuid:survey_id>/questions/list/",
		QuestionListView.as_view(),
		name="question-list",
	),
	# Get/Update/Delete specific question
	path(
		"<uuid:survey_id>/questions/<uuid:id>/",
		QuestionDetailView.as_view(),
		name="question-detail",
	),
	# ==========================================
	# QUESTION OPTION MANAGEMENT (Owner only)
	# ==========================================
	# Add option to question
	path(
		"<uuid:survey_id>/questions/<uuid:question_id>/options/",
		QuestionOptionCreateView.as_view(),
		name="option-create",
	),
	# Get/Update/Delete specific option
	path(
		"<uuid:survey_id>/questions/<uuid:question_id>/options/<uuid:id>/",
		QuestionOptionDetailView.as_view(),
		name="option-detail",
	),
	# ==========================================
	# ALLOWED EMAILS MANAGEMENT (Owner only)
	# ==========================================
	# Manage allowed emails for a survey
	path(
		"<uuid:survey_id>/allowed-emails/",
		SurveyAllowedEmailsView.as_view(),
		name="survey-allowed-emails",
	),
	# ==========================================
	# RESPONSE VIEWING (Owner only)
	# ==========================================
	# List all responses for survey
	path(
		"<uuid:survey_id>/responses/",
		SurveyResponseListView.as_view(),
		name="response-list",
	),
	# View single response detail
	path(
		"<uuid:survey_id>/responses/detail/",
		SurveyResponseDetailView.as_view(),
		name="response-detail",
	),
	# ==========================================
	# PUBLIC ENDPOINTS (Survey takers)
	# ==========================================
	# Get survey for taking (public access)
	path("take/<uuid:survey_id>/", TakeSurveyView.as_view(), name="take-survey"),
	# Submit survey response (public access)
	path(
		"submit/<uuid:survey_id>/",
		SubmitSurveyResponseView.as_view(),
		name="submit-survey",
	),

]

# ==========================================
# ALLOWED EMAILS ENDPOINTS (User's list)
# ==========================================

urlpatterns += [
	# List all allowed emails and create new email
	path(
		"allowed-emails/",
		AllowedEmailListCreateView.as_view(),
		name="allowed-email-list-create",
	),
	# View/Delete specific allowed email
	path(
		"allowed-emails/<uuid:id>/",
		AllowedEmailDetailView.as_view(),
		name="allowed-email-detail",
	),
]
