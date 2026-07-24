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
		return AllowedEmail.objects.filter(owner=self.request.user)

	def perform_create(self, serializer):
		serializer.save(owner=self.request.user)


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
		return AllowedEmail.objects.filter(owner=self.request.user)


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
			owner=request.user
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
			# Anyone can access
			if SurveyResponse.objects.filter(survey=survey, ip_address=ip, is_complete=True).exists():
				return Response({"error": "You have already responded this public survey."}, status=status.HTTP_400_BAD_REQUEST)
		

		elif survey.access_type == "public_authenticated":
			if not request.user.is_authenticated:
				return Response(
					{"error": "You must be logged in to access this survey."},
					status=status.HTTP_401_UNAUTHORIZED,
				)
			# Duplicate guard
			if not survey.allow_multiple_responses:
				if SurveyResponse.objects.filter(survey=survey, respondent=request.user, is_complete=True).exists():
					return Response(
						{"error": "You have already responded to this survey."},
						status=status.HTTP_400_BAD_REQUEST
					)

		elif survey.access_type == "private_invited":
			if not request.user.is_authenticated:
				return Response(
					{"error": "You must be logged in to access this survey."},
					status=status.HTTP_401_UNAUTHORIZED,
				)
			is_allowed = AllowedEmail.objects.filter(
				surveyallowedemail__survey=survey, email=request.user.email
			).exists()
			if not is_allowed:
				return Response(
					{"error": "You are not invited to access this survey."},
					status=status.HTTP_403_FORBIDDEN,
				)
			# Duplicate guard
			if not survey.allow_multiple_responses:
				if SurveyResponse.objects.filter(survey=survey, respondent=request.user, is_complete=True).exists():
					return Response(
						{"error": "You have already responded to this survey."},
						status=status.HTTP_400_BAD_REQUEST
					)

		# Step 4: Return survey
		serializer = SurveyDetailSerializer(survey)
		return Response(serializer.data)



class SubmitSurveyResponseView(APIView):
	"""
	POST /api/surveys/<survey_id>/submit/
	Body: { "answers": [ { "question_id": "uuid", "selected_options": ["uuid"] } ] }
	"""
	permission_classes = [AllowAny]

	@transaction.atomic
	def post(self, request, survey_id):
		survey = get_object_or_404(Survey, id=survey_id, status="active")

		user = request.user if request.user.is_authenticated else None
		ip = get_client_ip(request)

		# ── Duplicate response guard ──
		if survey.access_type == "public_anonymous":
			if SurveyResponse.objects.filter(survey=survey, ip_address=ip, is_complete=True).exists():
				return Response(
					{"error": "You have already responded to this survey."},
					status=status.HTTP_400_BAD_REQUEST
				)
		else:
			if user and not survey.allow_multiple_responses:
				if SurveyResponse.objects.filter(survey=survey, respondent=user, is_complete=True).exists():
					return Response(
						{"error": "You have already responded to this survey."},
						status=status.HTTP_400_BAD_REQUEST
					)

		# ── Access check ──
		email = None
		if survey.access_type == "public_authenticated" and not user:
			return Response({"error": "You must be logged in to access this survey."}, status=status.HTTP_401_UNAUTHORIZED)

		if survey.access_type == "private_invited":
			if not user:
				return Response({"error": "You must be logged in to access this survey."}, status=status.HTTP_401_UNAUTHORIZED)
			if not AllowedEmail.objects.filter(surveyallowedemail__survey=survey, email=user.email).exists():
				return Response({"error": "You are not invited to access this survey."}, status=status.HTTP_403_FORBIDDEN)
			email = user.email

		# ── Create response ──
		response_obj = SurveyResponse.objects.create(
			survey=survey,
			respondent=user,
			respondent_email=email or (user.email if user else ""),
			ip_address=ip,
		)

		# ── Save answers ──
		serializer = SubmitSurveyResponseSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		for ans in serializer.validated_data["answers"]:
			self._save_answer(response_obj, ans)

		# ── Complete ──
		response_obj.is_complete = True
		response_obj.completed_at = timezone.now()
		response_obj.save(update_fields=["is_complete", "completed_at"])

		return Response(
			{"message": "Survey submitted!", "response_id": str(response_obj.id)},
			status=status.HTTP_201_CREATED,
		)

	def _save_answer(self, response_obj, ans):
		question = get_object_or_404(Question, id=ans["question_id"], survey=response_obj.survey)
		if question.question_type == "single_choice" and len(ans["selected_options"]) > 1:
			raise serializers.ValidationError("Only one option allowed for this question")

		answer = Answer.objects.create(response=response_obj, question=question)
		for opt_id in ans["selected_options"]:
			option = get_object_or_404(QuestionOption, id=opt_id, question=question)
			AnswerSelection.objects.create(answer=answer, selected_option=option)


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


# ============================================
# VIEW 16: Survey Response Export (CSV / PDF)
# ============================================
class SurveyResponseExportView(APIView):
	"""
	GET: Export survey responses as CSV or PDF

	Endpoint: /api/surveys/<survey_id>/responses/export/

	Query params:
	  - export_format: csv | pdf   (required-ish, default csv)
	  - row_limit: number         (optional, how many individual rows)
	  - include_summary: true/false
	  - include_responses: true/false
	  - chart_style: none | bar | pie | both   (pdf only)

	Note: use export_format, not format — DRF reserves ?format= for renderers.
	"""

	permission_classes = [IsAuthenticated]

	def get(self, request, survey_id):
		from .export_utils import build_csv_response, build_pdf_response

		survey = get_object_or_404(Survey, id=survey_id, owner=request.user)
		export_format = (
			request.query_params.get("export_format")
			or request.query_params.get("type")
			or "csv"
		).lower()

		options = {
			"row_limit": request.query_params.get("row_limit"),
			"include_summary": self._bool_param(
				request, "include_summary", default=True
			),
			"include_responses": self._bool_param(
				request, "include_responses", default=True
			),
			"chart_style": request.query_params.get("chart_style") or "bar",
		}

		if export_format == "csv":
			return build_csv_response(survey, options)
		if export_format == "pdf":
			return build_pdf_response(survey, options)

		return Response(
			{"error": "Invalid export_format. Use csv or pdf."},
			status=status.HTTP_400_BAD_REQUEST,
		)

	def _bool_param(self, request, name, default=True):
		raw = request.query_params.get(name)
		if raw is None:
			return default
		return str(raw).lower() in ("1", "true", "yes", "on")

