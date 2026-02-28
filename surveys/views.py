# surveys/views.py
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .utils.ip_utils import get_client_ip
from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from django.db import transaction
from rest_framework import serializers
from django.db.models import Count, Q
from .models import (
	Survey,
	Question,
	QuestionOption,
	AllowedEmail,
	SurveyAllowedEmail,
	SurveyResponse,
	Answer,
	AnswerSelection,
)
from .serializers import (
	SurveyListSerializer,
	SurveyDetailSerializer,
	SurveyCreateSerializer,
	QuestionSerializer,
	QuestionCreateSerializer,
	QuestionOptionSerializer,
	AllowedEmailSerializer,
	SurveyResponseSerializer,
	SubmitSurveyResponseSerializer,
	AggregatedSurveyResponseSerializer,
)

User = get_user_model()


# ============================================
# VIEW 1: Survey List & Create
# ============================================
class SurveyListCreateView(generics.ListCreateAPIView):
	"""
	GET: List all surveys created by logged-in user
	POST: Create new survey

	Endpoint: /api/surveys/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = SurveyCreateSerializer

	def get_serializer_class(self):
		if self.request.method == "GET":
			return SurveyListSerializer
		return SurveyCreateSerializer

	def get_queryset(self):
		return Survey.objects.filter(owner=self.request.user).order_by(
			"-created_at"
		)

	def perform_create(self, serializer):
		serializer.save(owner=self.request.user)


# ============================================
# VIEW 2: Survey Detail
# ============================================
class SurveyDetailView(generics.RetrieveUpdateDestroyAPIView):
	"""
	GET: Retrieve survey details
	PUT: Update survey (full)
	PATCH: Partial update
	DELETE: Delete survey

	Endpoint: /api/surveys/<survey_id>/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = SurveyDetailSerializer
	lookup_field = "id"

	def get_queryset(self):
		return Survey.objects.filter(owner=self.request.user)


# ============================================
# VIEW 3: Question Create
# ============================================
class QuestionCreateView(generics.CreateAPIView):
	"""
	POST: Add question to survey

	Endpoint: /api/surveys/<survey_id>/questions/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = QuestionCreateSerializer

	def perform_create(self, serializer):
		survey_id = self.kwargs.get("survey_id")
		survey = get_object_or_404(Survey, id=survey_id, owner=self.request.user)
		serializer.save(survey=survey)


# ============================================
# VIEW 4: Question List
# ============================================
class QuestionListView(generics.ListAPIView):
	"""
	GET: List all questions in a survey

	Endpoint: /api/surveys/<survey_id>/questions/list/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = QuestionSerializer

	def get_queryset(self):
		survey_id = self.kwargs.get("survey_id")
		return Question.objects.filter(
			survey__id=survey_id, survey__owner=self.request.user
		).prefetch_related("options")


# ============================================
# VIEW 5: Question Detail
# ============================================
class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
	"""
	GET: Retrieve question
	PUT: Update question (full)
	PATCH: Partial update
	DELETE: Delete question

	Endpoint: /api/surveys/<survey_id>/questions/<question_id>/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = QuestionSerializer
	lookup_field = "id"

	def get_queryset(self):
		survey_id = self.kwargs.get("survey_id")
		return Question.objects.filter(
			survey__id=survey_id, survey__owner=self.request.user
		)


# ============================================
# VIEW 6: Question Option Create
# ============================================
class QuestionOptionCreateView(generics.CreateAPIView):
	"""
	POST: Add option to question

	Endpoint: /api/surveys/<survey_id>/questions/<question_id>/options/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = QuestionOptionSerializer

	def perform_create(self, serializer):
		survey_id = self.kwargs.get("survey_id")
		question_id = self.kwargs.get("question_id")

		survey = get_object_or_404(Survey, id=survey_id, owner=self.request.user)
		question = get_object_or_404(
			Question, id=question_id, survey=survey
		)

		serializer.save(question=question)


# ============================================
# VIEW 7: Question Option Detail
# ============================================
class QuestionOptionDetailView(generics.RetrieveUpdateDestroyAPIView):
	"""
	GET: Retrieve option
	PUT: Update option (full)
	PATCH: Partial update
	DELETE: Delete option

	Endpoint: /api/surveys/<survey_id>/questions/<question_id>/options/<option_id>/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = QuestionOptionSerializer
	lookup_field = "id"

	def get_queryset(self):
		question_id = self.kwargs.get("question_id")
		return QuestionOption.objects.filter(question__id=question_id)


# ============================================
# VIEW 8: Allowed Emails List & Create
# ============================================
class AllowedEmailListCreateView(generics.ListCreateAPIView):
	"""
	GET: List all allowed emails
	POST: Create new allowed email

	Endpoint: /api/surveys/allowed-emails/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = AllowedEmailSerializer

	def get_queryset(self):
		return AllowedEmail.objects.filter(user=self.request.user)

	def perform_create(self, serializer):
		serializer.save(user=self.request.user)


# ============================================
# VIEW 9: Allowed Email Detail
# ============================================
class AllowedEmailDetailView(generics.RetrieveDestroyAPIView):
	"""
	GET: Retrieve allowed email
	DELETE: Delete allowed email

	Endpoint: /api/surveys/allowed-emails/<email_id>/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = AllowedEmailSerializer
	lookup_field = "id"

	def get_queryset(self):
		return AllowedEmail.objects.filter(user=self.request.user)


# ============================================
# VIEW 10: Survey Allowed Emails Management
# ============================================
class SurveyAllowedEmailsView(APIView):
	"""
	GET: Get allowed emails for survey
	POST: Add allowed emails to survey
	DELETE: Remove allowed email from survey

	Endpoint: /api/surveys/<survey_id>/allowed-emails/
	"""

	permission_classes = [IsAuthenticated]

	def get(self, request, survey_id):
		# Get survey (must be owner)
		survey = get_object_or_404(Survey, id=survey_id, owner=request.user)

		# Get related allowed emails
		survey_emails = SurveyAllowedEmail.objects.filter(
			survey=survey
		).select_related("allowed_email")

		data = [
			{
				"id": se.allowed_email.id,
				"email": se.allowed_email.email,
				"created_at": se.allowed_email.created_at,
			}
			for se in survey_emails
		]

		return Response(data)

	def post(self, request, survey_id):
		# Get survey (must be owner)
		survey = get_object_or_404(Survey, id=survey_id, owner=request.user)

		allowed_email_ids = request.data.get("allowed_email_ids", [])

		# Get allowed emails owned by user
		allowed_emails = AllowedEmail.objects.filter(
			id__in=allowed_email_ids,
			user=request.user
		)

		# Create relations
		for allowed_email in allowed_emails:
			SurveyAllowedEmail.objects.get_or_create(
				survey=survey,
				allowed_email=allowed_email
			)

		return Response(
			{
				"message": f"{allowed_emails.count()} emails added to survey",
				"allowed_emails": AllowedEmailSerializer(
					allowed_emails, many=True
				).data,
			}
		)

	def delete(self, request, survey_id):
		# Get survey (must be owner)
		survey = get_object_or_404(Survey, id=survey_id, owner=request.user)

		allowed_email_id = request.data.get("allowed_email_id")

		# Delete relation
		SurveyAllowedEmail.objects.filter(
			survey=survey,
			allowed_email__id=allowed_email_id
		).delete()

		return Response({"message": "Email removed from survey"})


# ============================================
# VIEW 11: Survey Status Update
# ============================================
class SurveyStatusUpdateView(APIView):
	"""
	POST: Update survey status (draft/active/closed)

	Endpoint: /api/surveys/<survey_id>/status/
	"""

	permission_classes = [IsAuthenticated]

	def post(self, request, survey_id):
		survey = get_object_or_404(Survey, id=survey_id, owner=request.user)

		new_status = request.data.get("status")

		if new_status not in ["draft", "active", "closed"]:
			return Response(
				{"error": "Invalid status. Choose: draft, active, or closed."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		# Validate survey has questions before publishing
		if new_status == "active" and survey.questions.count() == 0:
			return Response(
				{"error": "Cannot publish survey without questions."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		survey.status = new_status
		survey.save()

		return Response(
			{
				"message": f"Survey status updated to '{new_status}'.",
				"status": survey.status,
			}
		)


# ============================================
# VIEW 12: Take Survey (Public)
# ============================================
class TakeSurveyView(APIView):
	"""
	GET: Retrieve survey for taking (public endpoint)

	Endpoint: /api/surveys/take/<survey_id>/
	"""

	permission_classes = [AllowAny]

	def get(self, request, survey_id):
		# Get survey and verify it's active
		survey = get_object_or_404(Survey, id=survey_id, status="active")

		# Check access restrictions
		if not self._verify_user_access(survey, request):
			return Response(
				{"error": "You don't have permission to take this survey."},
				status=status.HTTP_403_FORBIDDEN,
			)

		serializer = SurveyDetailSerializer(survey)
		return Response(serializer.data)

	def _verify_user_access(self, survey, request):
		"""
		Helper: Verify user has access based on survey access_type.
		
		Access types:
		- public_anonymous: Anyone can take
		- public_authenticated: Must be authenticated
		- private_invited: Must have valid token or email allowed
		"""
		if survey.access_type == "public_anonymous":
			return True

		if survey.access_type == "public_authenticated":
			return request.user.is_authenticated

		if survey.access_type == "private_invited":
			# Check token or email
			token = request.query_params.get("token")
			if token:
				return self._verify_token(survey, token)

			if request.user.is_authenticated:
				return self._verify_email(survey, request.user.email)

			return False

		return False

	def _verify_token(self, survey, token):
		"""Helper: Verify invitation token is valid"""
		# Implementation depends on token structure
		return True

	def _verify_email(self, survey, email):
		"""Helper: Check if email is allowed for survey"""
		return SurveyAllowedEmail.objects.filter(
			survey=survey,
			allowed_email__email=email
		).exists()


# ============================================
# VIEW 13: Submit Survey Response
# ============================================
class SubmitSurveyResponseView(APIView):
	"""
	POST: Submit survey response (public endpoint)

	Endpoint: /api/surveys/submit/<survey_id>/
	"""

	permission_classes = [AllowAny]

	def post(self, request, survey_id):
		# Get survey
		survey = get_object_or_404(Survey, id=survey_id, status="active")

		# Verify access
		if not self._verify_user_access(survey, request):
			return Response(
				{"error": "You don't have permission to submit this survey."},
				status=status.HTTP_403_FORBIDDEN,
			)

		# Create response record
		with transaction.atomic():
			response_obj = self._create_response_object(survey, request)
			self._create_answers(survey, response_obj, request.data)

		serializer = SurveyResponseSerializer(response_obj)
		return Response(
			{
				"message": "Response submitted successfully",
				"response_id": str(response_obj.id),
			},
			status=status.HTTP_201_CREATED,
		)

	def _verify_user_access(self, survey, request):
		"""Helper: Same logic as TakeSurveyView"""
		if survey.access_type == "public_anonymous":
			return True

		if survey.access_type == "public_authenticated":
			return request.user.is_authenticated

		if survey.access_type == "private_invited":
			token = request.query_params.get("token")
			if token:
				return True

			if request.user.is_authenticated:
				return SurveyAllowedEmail.objects.filter(
					survey=survey,
					allowed_email__email=request.user.email
				).exists()

		return False

	def _create_response_object(self, survey, request):
		"""Helper: Create SurveyResponse record"""
		respondent = request.user if request.user.is_authenticated else None
		respondent_email = (
			request.user.email if request.user.is_authenticated
			else request.data.get("respondent_email", "")
		)

		response_obj = SurveyResponse.objects.create(
			survey=survey,
			respondent=respondent,
			respondent_email=respondent_email,
			started_at=timezone.now(),
			completed_at=timezone.now(),
			is_complete=True,
			ip_address=get_client_ip(request),
		)

		return response_obj

	def _create_answers(self, survey, response_obj, data):
		"""Helper: Create Answer and AnswerSelection records"""
		answers_data = data.get("answers", [])

		for answer_data in answers_data:
			question_id = answer_data.get("question_id")
			selected_option_ids = answer_data.get("selected_options", [])

			# Get question
			try:
				question = Question.objects.get(
					id=question_id, survey=survey
				)
			except Question.DoesNotExist:
				continue

			# Create answer
			answer = Answer.objects.create(
				response=response_obj,
				question=question
			)

			# Create selections
			for option_id in selected_option_ids:
				try:
					option = QuestionOption.objects.get(
						id=option_id, question=question
					)
					AnswerSelection.objects.create(
						answer=answer,
						selected_option=option
					)
				except QuestionOption.DoesNotExist:
					continue


# ============================================
# VIEW 14: Survey Response List (Aggregated)
# ============================================
class SurveyResponseListView(APIView):
	"""
	GET: List survey responses with aggregated statistics

	Endpoint: /api/surveys/<survey_id>/responses/
	"""

	permission_classes = [IsAuthenticated]

	def get(self, request, survey_id):
		# Get survey (must be owner)
		survey = get_object_or_404(Survey, id=survey_id, owner=request.user)

		# Aggregate statistics
		questions_data = []

		for question in survey.questions.all().order_by("order"):
			question_stats = self._get_question_statistics(survey, question)
			questions_data.append(question_stats)

		return Response(
			{
				"survey_id": str(survey.id),
				"survey_title": survey.title,
				"total_responses": SurveyResponse.objects.filter(
					survey=survey, is_complete=True
				).count(),
				"questions": questions_data,
			}
		)

	def _get_question_statistics(self, survey, question):
		"""Helper: Get aggregated statistics for a question"""
		total_answers = Answer.objects.filter(
			response__survey=survey,
			response__is_complete=True,
			question=question,
		).count()

		options_data = self._get_option_statistics(
			survey, question, total_answers
		)

		return {
			"id": str(question.id),
			"question_text": question.question_text,
			"question_type": question.question_type,
			"total_answers": total_answers,
			"options": options_data,
		}

	def _get_option_statistics(self, survey, question, total_answers):
		"""Helper: Calculate count and percentage for each option"""
		options_data = []

		for option in question.options.all():
			count = AnswerSelection.objects.filter(
				answer__response__survey=survey,
				answer__response__is_complete=True,
				answer__question=question,
				selected_option=option,
			).count()

			percentage = (count / total_answers * 100) if total_answers > 0 else 0

			options_data.append({
				"id": str(option.id),
				"option_text": option.option_text,
				"count": count,
				"percentage": round(percentage, 2),
			})

		return options_data


# ============================================
# VIEW 15: Survey Response Detail (with filtering)
# ============================================
class SurveyResponseDetailView(APIView):
	"""
	GET: Get responses with optional question filtering
	- Without question_id: Returns all responses with all answers
	- With question_id: Returns formatted table data for DataTable

	Endpoint: /api/surveys/<survey_id>/responses/detail/
	Query params: ?question_id=<uuid> (optional)
	"""

	permission_classes = [IsAuthenticated]

	def get(self, request, survey_id):
		# Get survey (must be owner)
		survey = get_object_or_404(Survey, id=survey_id, owner=request.user)

		# Check if filtering by question
		question_id = request.query_params.get("question_id")

		if question_id:
			return self._get_question_responses_for_table(
				survey, question_id, request
			)
		else:
			return self._get_all_responses(survey)

	def _get_question_responses_for_table(self, survey, question_id, request):
		"""Helper: Get responses for specific question formatted for DataTable"""
		# Verify question belongs to survey
		try:
			question = Question.objects.get(id=question_id, survey=survey)
		except Question.DoesNotExist:
			return Response(
				{"error": "Question not found in this survey."},
				status=status.HTTP_404_NOT_FOUND,
			)

		# Get only responses that have answered this specific question
		responses = SurveyResponse.objects.filter(
			survey=survey, is_complete=True, answers__question=question
		).select_related("respondent").prefetch_related("answers__selections").distinct()

		# Build table rows
		table_rows = []
		sn = 1

		for response in responses:
			# Get email (respondent > respondent_email > Anonymous)
			if response.respondent:
				email = response.respondent.email
			else:
				email = response.respondent_email or "Anonymous"

			# Get respondent name from User object if available
			respondent_name = None
			if response.respondent:
				name = f"{response.respondent.first_name} {response.respondent.last_name}".strip()
				respondent_name = name if name else None

			# Get selected options for this question
			answer = response.answers.filter(question=question).first()
			selected_options = ""

			if answer:
				options = [sel.selected_option.option_text for sel in answer.selections.all()]
				selected_options = ", ".join(options)

			table_rows.append({
				"id": str(response.id),
				"sn": sn,
				"email": email,
				"respondent_name": respondent_name,
				"selected_options": selected_options,
				"submitted_at": response.completed_at.isoformat() if response.completed_at else None,
			})

			sn += 1

		return Response({
			"question_id": str(question.id),
			"question_text": question.question_text,
			"question_type": question.question_type,
			"total_responses": len(table_rows),
			"responses": table_rows,
		})

	def _get_all_responses(self, survey):
		"""Helper: Get all responses with all answers (original format)"""
		responses = SurveyResponse.objects.filter(
			survey=survey, is_complete=True
		).select_related("respondent").prefetch_related("answers__selections")

		data = []

		for response in responses:
			# Get email
			email = (
				response.respondent.email if response.respondent
				else response.respondent_email or "Anonymous"
			)

			answers_data = []

			for answer in response.answers.all():
				selected_options = [
					{
						"option_id": str(sel.selected_option.id),
						"option_text": sel.selected_option.option_text,
					}
					for sel in answer.selections.all()
				]

				answers_data.append({
					"question_id": str(answer.question.id),
					"question_text": answer.question.question_text,
					"selected_options": selected_options,
				})

			data.append({
				"response_id": str(response.id),
				"email": email,
				"submitted_at": response.completed_at,
				"answers": answers_data,
			})

		return Response(data)
