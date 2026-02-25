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

	def get_serializer_class(self):
		"""Use different serializers for list vs create"""
		if self.request.method == "POST":
			return SurveyCreateSerializer
		return SurveyListSerializer

	def get_queryset(self):
		"""Return only surveys created by current user"""
		return Survey.objects.filter(owner=self.request.user)

	def perform_create(self, serializer):
		"""
		Automatically set the owner when creating survey
		- User doesn't need to send 'owner' in request
		- We get it from JWT token
		"""
		serializer.save(owner=self.request.user)


# ============================================
# VIEW 2: Survey Detail, Update, Delete
# ============================================
class SurveyDetailView(generics.RetrieveUpdateDestroyAPIView):
	"""
	GET: Get single survey details
	PATCH/PUT: Update survey
	DELETE: Delete survey

	Endpoint: /api/surveys/<survey_id>/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = SurveyDetailSerializer
	lookup_field = "id"

	def get_queryset(self):
		"""User can only access their own surveys"""
		return Survey.objects.filter(owner=self.request.user)


# ============================================
# VIEW 3: Add Question to Survey
# ============================================
class QuestionCreateView(generics.CreateAPIView):
	"""
	POST: Add question to survey (with options)

	Endpoint: /api/surveys/<survey_id>/questions/

	Request body:
	{
		"question_text": "What's your favorite color?",
		"question_type": "single_choice",
		"order": 0,
		"is_required": true,
		"options": [
			{"option_text": "Red", "order": 0},
			{"option_text": "Blue", "order": 1}
		]
	}
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = QuestionCreateSerializer

	def perform_create(self, serializer):
		"""
		Link question to survey
		- Get survey_id from URL
		- Check user owns the survey
		- Create question
		"""
		survey_id = self.kwargs.get("survey_id")
		survey = get_object_or_404(Survey, id=survey_id, owner=self.request.user)
		serializer.save(survey=survey)


# ============================================
# VIEW 4: List Questions in Survey
# ============================================
class QuestionListView(generics.ListAPIView):
	"""
	GET: List all questions in a survey

	Endpoint: /api/surveys/<survey_id>/questions/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = QuestionSerializer

	def get_queryset(self):
		"""Get all questions for this survey"""
		survey_id = self.kwargs.get("survey_id")
		survey = get_object_or_404(Survey, id=survey_id, owner=self.request.user)
		return Question.objects.filter(survey=survey)


# ============================================
# VIEW 5: Update/Delete Single Question
# ============================================
class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
	"""
	GET: Get single question
	PATCH/PUT: Update question
	DELETE: Delete question

	Endpoint: /api/surveys/<survey_id>/questions/<question_id>/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = QuestionSerializer
	lookup_field = "id"
	# def initial(self, request, *args, **kwargs):
	# 	super().initial(request, *args, **kwargs)
	# 	print(f"user request data ===== {request.data} =====")


	def get_queryset(self):
		"""User can only access questions from their surveys"""
		survey_id = self.kwargs.get("survey_id")
		return Question.objects.filter(
			survey__id=survey_id, survey__owner=self.request.user
		)


# ============================================
# VIEW 6: Add Option to Question
# ============================================
class QuestionOptionCreateView(generics.CreateAPIView):
	"""
	POST: Add option to question

	Endpoint: /api/surveys/<survey_id>/questions/<question_id>/options/

	Request body:
	{
		"option_text": "Green",
		"order": 2
	}
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = QuestionOptionSerializer

	def perform_create(self, serializer):
		"""Link option to question"""
		question_id = self.kwargs.get("question_id")
		survey_id = self.kwargs.get("survey_id")

		# Check question exists and user owns the survey
		question = get_object_or_404(
			Question,
			id=question_id,
			survey__id=survey_id,
			survey__owner=self.request.user,
		)
		serializer.save(question=question)


# ============================================
# VIEW 7: Update/Delete Option
# ============================================
class QuestionOptionDetailView(generics.RetrieveUpdateDestroyAPIView):
	"""
	GET: Get single option
	PATCH/PUT: Update option
	DELETE: Delete option

	Endpoint: /api/surveys/<survey_id>/questions/<question_id>/options/<option_id>/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = QuestionOptionSerializer
	lookup_field = "id"

	def get_queryset(self):
		"""User can only access options from their surveys"""
		survey_id = self.kwargs.get("survey_id")
		question_id = self.kwargs.get("question_id")
		return QuestionOption.objects.filter(
			question__id=question_id,
			question__survey__id=survey_id,
			question__survey__owner=self.request.user,
		)

	def destroy(self, request, *args, **kwargs):
		"""
		Override destroy to prevent deleting options with responses
		"""
		option = self.get_object()

		# Check if this option has any responses
		has_responses = AnswerSelection.objects.filter(selected_option=option).exists()

		if has_responses:
			return Response(
				{
					"error": "Cannot delete this option because survey responses reference it. "
					"This option will be hidden from new responses but kept for data integrity."
				},
				status=status.HTTP_400_BAD_REQUEST,
			)

		# Safe to delete - no responses exist for this option
		return super().destroy(request, *args, **kwargs)


# ============================================
# VIEW 8: Manage Allowed Emails (User's list)
# ============================================
class AllowedEmailListCreateView(generics.ListCreateAPIView):
	"""
	GET: List all allowed emails for current user
	POST: Create new allowed email

	Endpoint: /api/allowed-emails/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = AllowedEmailSerializer

	def get_queryset(self):
		"""Return only emails for current user"""
		return AllowedEmail.objects.filter(owner=self.request.user)

	def perform_create(self, serializer):
		"""Automatically set owner to current user"""
		serializer.save(owner=self.request.user)


class AllowedEmailDetailView(generics.RetrieveDestroyAPIView):
	"""
	GET: Get single allowed email
	DELETE: Delete allowed email

	Endpoint: /api/allowed-emails/<email_id>/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = AllowedEmailSerializer
	lookup_field = "id"

	def get_queryset(self):
		"""User can only access their own emails"""
		return AllowedEmail.objects.filter(owner=self.request.user)


# ============================================
# VIEW 9: Link Allowed Emails to Survey
# ============================================
class SurveyAllowedEmailsView(APIView):
	"""
	GET: List allowed emails selected for a survey
	POST: Add allowed emails to survey
	DELETE: Remove allowed email from survey

	Endpoint: /api/surveys/<survey_id>/allowed-emails/

	POST Request body:
	{
		"allowed_email_ids": ["uuid1", "uuid2"]
	}
	"""

	permission_classes = [IsAuthenticated]

	def get(self, request, survey_id):
		"""Get allowed emails for survey"""
		survey = get_object_or_404(Survey, id=survey_id, owner=request.user)

		allowed_emails = AllowedEmail.objects.filter(surveyallowedemail__survey=survey)
		serializer = AllowedEmailSerializer(allowed_emails, many=True)
		return Response(serializer.data)

	def post(self, request, survey_id):
		"""Add allowed emails to survey"""
		survey = get_object_or_404(Survey, id=survey_id, owner=request.user)

		allowed_email_ids = request.data.get("allowed_email_ids", [])
		if not allowed_email_ids:
			return Response(
				{"error": "Please provide allowed_email_ids"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		# Verify all emails belong to current user
		allowed_emails = AllowedEmail.objects.filter(
			id__in=allowed_email_ids, owner=request.user
		)

		if len(allowed_emails) != len(allowed_email_ids):
			return Response(
				{"error": "One or more emails not found or don't belong to you"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		# Clear existing and add new
		SurveyAllowedEmail.objects.filter(survey=survey).delete()

		created_count = 0
		for allowed_email in allowed_emails:
			_, created = SurveyAllowedEmail.objects.get_or_create(
				survey=survey, allowed_email=allowed_email
			)
			if created:
				created_count += 1

		serializer = AllowedEmailSerializer(allowed_emails, many=True)
		return Response(
			{
				"message": f"Added {created_count} emails to survey",
				"allowed_emails": serializer.data,
			},
			status=status.HTTP_201_CREATED,
		)

	def delete(self, request, survey_id):
		"""Remove allowed email from survey"""
		survey = get_object_or_404(Survey, id=survey_id, owner=request.user)

		allowed_email_id = request.data.get("allowed_email_id")
		if not allowed_email_id:
			return Response(
				{"error": "Please provide allowed_email_id"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		survey_allowed_email = get_object_or_404(
			SurveyAllowedEmail, survey=survey, allowed_email_id=allowed_email_id
		)
		survey_allowed_email.delete()

		return Response({"message": "Email removed from survey"})


# ============================================
# VIEW 10: Get Survey for Taking (Public Access)
# ============================================
class TakeSurveyView(APIView):
	"""
	GET: Get survey for taking (responder view)

	Endpoint: /api/surveys/take/<survey_id>/
	or: /api/surveys/take/<survey_id>/?token=<invitation_token>

	This is public - no authentication required
	"""

	permission_classes = [AllowAny]



	def get(self, request, survey_id):
		"""
		Get survey for taking

		Steps:
		1. Get survey
		2. Check if survey is active
		3. Check access permissions
		4. Return survey with questions
		"""
		

		# Step 1: Get survey
		survey = get_object_or_404(Survey, id=survey_id)
		ip  = get_client_ip(request)
		# Step 2: Check status
		if survey.status != "active":
			return Response(
				{"error": "This survey is not currently accepting responses."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		# Step 3: Check access based on access_type
		if survey.access_type == "public_anonymous":
			pass
			# Anyone can access
			# if SurveyResponse.objects.filter(survey=survey, ip_address=ip, is_complete=True).exists():
			# 	return Response({"error": "You have already responded this public survey."}, status=status.HTTP_400_BAD_REQUEST)

		elif survey.access_type == "public_authenticated":
			# Must be logged in
			if not request.user.is_authenticated:
				return Response(
					{"error": "You must be logged in to access this survey."},
					status=status.HTTP_401_UNAUTHORIZED,
				)

		elif survey.access_type == "private_invited":
			# Must be logged in with an email in the allowed list
			if not request.user.is_authenticated:
				return Response(
					{"error": "You must be logged in to access this survey."},
					status=status.HTTP_401_UNAUTHORIZED,
				)

			# Check if user email is in allowed emails
			is_allowed = AllowedEmail.objects.filter(
				surveyallowedemail__survey=survey, email=request.user.email
			).exists()

			if not is_allowed:
				return Response(
					{"error": "Your email is not authorized to access this survey."},
					status=status.HTTP_403_FORBIDDEN,
				)

		# Step 4: Return survey
		serializer = SurveyDetailSerializer(survey)
		return Response(serializer.data)


# ============================================
# VIEW 11: Submit Survey Response
# ============================================
class SubmitSurveyResponseView(APIView):
	"""
	POST /api/surveys/<survey_id>/submit/
	Body: { "answers": [ { "question_id": "uuid", "selected_options": ["uuid"] } ] }
	"""
	permission_classes = [AllowAny]

	@transaction.atomic
	def post(self, request, survey_id):
		survey = get_object_or_404(Survey, id=survey_id, status="active")

		# ---------- who are we? ----------
		user = request.user if request.user.is_authenticated else None
		ip  = get_client_ip(request)

		# ---------- one-response guard ----------
		if survey.access_type == "public_anonymous":
			pass
			# public → block duplicate IP
			# if SurveyResponse.objects.filter(survey=survey, ip_address=ip, is_complete=True).exists():
			# 	return Response({"error": "You have already responded this public survey."}, status=status.HTTP_400_BAD_REQUEST)
		else:
			# authenticated or invited → block duplicate user
			if user and not survey.allow_multiple_responses:
				if SurveyResponse.objects.filter(survey=survey, respondent=user, is_complete=True).exists():
					return Response({"error": "You have already responded."}, status=status.HTTP_400_BAD_REQUEST)

		# ---------- access check ----------
		email = None
		if survey.access_type == "public_authenticated" and not user:
			return Response({"error": "Login required."}, status=status.HTTP_401_UNAUTHORIZED)

		if survey.access_type == "private_invited":
			if not user:
				return Response({"error": "Login required."}, status=status.HTTP_401_UNAUTHORIZED)
			if not AllowedEmail.objects.filter(surveyallowedemail__survey=survey, email=user.email).exists():
				return Response({"error": "Email not authorised."}, status=status.HTTP_403_FORBIDDEN)
			email = user.email

		# ---------- create response ----------
		response_obj = SurveyResponse.objects.create(
			survey=survey,
			respondent=user,
			respondent_email=email,
			ip_address=ip,
		)

		# ---------- save answers ----------
		serializer = SubmitSurveyResponseSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		for ans in serializer.validated_data["answers"]:
			self._save_answer(response_obj, ans)

		# ---------- finish ----------
		response_obj.is_complete = True
		response_obj.completed_at = timezone.now()
		response_obj.save(update_fields=["is_complete", "completed_at"])

		return Response(
			{"message": "Survey submitted!", "response_id": str(response_obj.id)},
			status=status.HTTP_201_CREATED,
		)

	# ---------------- helpers ----------------
	def _save_answer(self, response_obj, ans):
		question = get_object_or_404(Question, id=ans["question_id"], survey=response_obj.survey)
		if question.question_type == "single_choice" and len(ans["selected_options"]) > 1:
			raise serializers.ValidationError("Only one option allowed for this question")

		answer = Answer.objects.create(response=response_obj, question=question)
		for opt_id in ans["selected_options"]:
			option = get_object_or_404(QuestionOption, id=opt_id, question=question)
			AnswerSelection.objects.create(answer=answer, selected_option=option)

	
	
# ============================================
# VIEW 12: View Survey Responses (Aggregated Stats)
# ============================================
class SurveyResponseListView(APIView):
	"""
	GET: Get aggregated response statistics for a survey

	Endpoint: /api/surveys/<survey_id>/responses/

	Returns:
	{
		"survey_id": "uuid",
		"survey_title": "My Survey",
		"total_responses": 10,
		"questions": [
			{
				"id": "uuid",
				"question_text": "How is the service?",
				"question_type": "single_choice",
				"total_answers": 10,
				"options": [
					{
						"id": "uuid",
						"option_text": "Good",
						"count": 5,
						"percentage": 50.0
					},
					{
						"id": "uuid",
						"option_text": "Bad",
						"count": 3,
						"percentage": 30.0
					},
					{
						"id": "uuid",
						"option_text": "Average",
						"count": 2,
						"percentage": 20.0
					}
				]
			}
		]
	}
 """

	permission_classes = [IsAuthenticated]

	def get(self, request, survey_id):
		"""Get aggregated response statistics"""
		# Verify ownership
		survey = get_object_or_404(Survey, id=survey_id, owner=request.user)

		# Get total complete responses
		total_responses = SurveyResponse.objects.filter(
			survey=survey, is_complete=True
		).count()

		# Build aggregated data
		questions_data = []

		for question in survey.questions.all():
			# Count answers for this question
			total_answers = Answer.objects.filter(
				response__survey=survey,
				response__is_complete=True,
				question=question,
			).count()

			options_data = []

			for option in question.options.all():
				# Count selections for this option
				count = AnswerSelection.objects.filter(
					answer__response__survey=survey,
					answer__response__is_complete=True,
					answer__question=question,
					selected_option=option,
				).count()

				# Calculate percentage
				percentage = (count / total_answers * 100) if total_answers > 0 else 0

				options_data.append({
					"id": str(option.id),
					"option_text": option.option_text,
					"count": count,
					"percentage": round(percentage, 2),
				})

			questions_data.append({
				"id": str(question.id),
				"question_text": question.question_text,
				"question_type": question.question_type,
				"total_answers": total_answers,
				"options": options_data,
			})

		# Serialize the aggregated data
		aggregated_data = {
			"survey_id": str(survey.id),
			"survey_title": survey.title,
			"total_responses": total_responses,
			"questions": questions_data,
		}

		serializer = AggregatedSurveyResponseSerializer(aggregated_data)
		return Response(serializer.data)


# ============================================
# VIEW 13: View Single Response Detail
# ============================================
class SurveyResponseDetailView(generics.RetrieveAPIView):
	"""
	GET: View single response detail

	Endpoint: /api/surveys/<survey_id>/responses/<response_id>/
	"""

	permission_classes = [IsAuthenticated]
	serializer_class = SurveyResponseSerializer
	lookup_field = "id"

	def get_queryset(self):
		"""User can only view responses from their surveys"""
		survey_id = self.kwargs.get("survey_id")
		return SurveyResponse.objects.filter(
			survey__id=survey_id, survey__owner=self.request.user, is_complete=True
		)


# ============================================
# VIEW 14: Publish/Close Survey
# ============================================
class SurveyStatusUpdateView(APIView):
	"""
	POST: Update survey status (publish/close)

	Endpoint: /api/surveys/<survey_id>/status/

	Request body:
	{
		"status": "active"  // or "closed" or "draft"
	}
	"""

	permission_classes = [IsAuthenticated]

	def post(self, request, survey_id):
		"""Update survey status"""
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
