# surveys/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
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

User = get_user_model()


# ============================================
# SERIALIZER 1: QuestionOption (Answer choices)
# ============================================
class QuestionOptionSerializer(serializers.ModelSerializer):
	"""
	Serializer for question options (choices)
	Used when creating/viewing question options
	"""

	class Meta:
		model = QuestionOption
		fields = ["id", "option_text", "order", "created_at"]
		read_only_fields = ["id", "created_at"]


# ============================================
# SERIALIZER 2: Question
# ============================================
# serializers.py
class QuestionSerializer(serializers.ModelSerializer):
    """
    Serializer for questions
    - Includes all options for the question
    - Handles nested option updates
    """
    options = QuestionOptionSerializer(many=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "question_text",
            "question_type",
            "order",
            "is_required",
            "options",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def update(self, instance, validated_data):
        """
        Custom update to handle nested options
        Steps:
        1. Update question fields
        2. Handle options (create/update/delete)
        """
        # Step 1: Update question fields
        options_data = validated_data.pop('options', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Step 2: Get existing option IDs
        existing_option_ids = [opt.id for opt in instance.options.all()]
        incoming_option_ids = [opt.get('id') for opt in options_data if opt.get('id')]

        # Step 3: Delete options not in the update
        for option in instance.options.all():
            if option.id not in incoming_option_ids:
                option.delete()

        # Step 4: Update existing and create new options
        for option_data in options_data:
            option_id = option_data.get('id')
            if option_id and option_id in existing_option_ids:
                # Update existing option
                option = QuestionOption.objects.get(id=option_id, question=instance)
                for attr, value in option_data.items():
                    setattr(option, attr, value)
                option.save()
            else:
                # Create new option
                QuestionOption.objects.create(question=instance, **option_data)

        return instance

# ============================================
# SERIALIZER 3: Question Create (Nested)
# ============================================
class QuestionCreateSerializer(serializers.ModelSerializer):
	"""
	Special serializer for creating questions WITH options
	- Allows creating question and options in one request
	"""

	options = QuestionOptionSerializer(many=True, required=False)

	class Meta:
		model = Question
		fields = [
			"question_text", "question_type", "order", "is_required", "options"]

	def create(self, validated_data):
		"""
		Custom create method to handle nested options

		Steps:
		1. Extract options data from validated_data
		2. Create the question
		3. Create each option and link to question
		4. Return the question
		"""
		# Step 1: Get options data and remove from validated_data
		options_data = validated_data.pop("options", [])

		# Step 2: Create the question
		question = Question.objects.create(**validated_data)

		# Step 3: Create each option
		for option_data in options_data:
			QuestionOption.objects.create(question=question, **option_data)

		# Step 4: Return question
		return question


# ============================================
# SERIALIZER 4: Survey List (Simple view)
# ============================================
class SurveyListSerializer(serializers.ModelSerializer):
	"""
	Simple serializer for listing surveys
	- Shows basic info only (no questions)
	- Used in survey list endpoint
	"""

	owner_username = serializers.CharField(source="owner.username", read_only=True)
	question_count = serializers.SerializerMethodField()
	response_count = serializers.SerializerMethodField()

	class Meta:
		model = Survey
		fields = [
			"id",
			"title",
			"description",
			"access_type",
			"display_mode",
			"status",
			"owner_username",
			"question_count",
			"response_count",
			"created_at",
		]
		read_only_fields = ["id", "created_at"]

	def get_question_count(self, obj):
		"""Count total questions in survey"""
		return obj.questions.count()

	def get_response_count(self, obj):
		"""Count total responses to survey"""
		return obj.responses.filter(is_complete=True).count()


# ============================================
# SERIALIZER 5: Survey Detail (Full view)
# ============================================
class SurveyDetailSerializer(serializers.ModelSerializer):
	"""
	Detailed serializer for single survey
	- Includes all questions and options
	- Used when viewing/editing a survey
	"""

	questions = QuestionSerializer(many=True, read_only=True)
	owner_username = serializers.CharField(source="owner.username", read_only=True)

	class Meta:
		model = Survey
		fields = [
			"id",
			"title",
			"description",
			"access_type",
			"display_mode",
			"questions_per_page",
			"status",
			"allow_multiple_responses",
			"show_progress_bar",
			"owner_username",
			"questions",
			"created_at",
			"updated_at",
		]
		read_only_fields = ["id", "owner_username", "created_at", "updated_at"]


# ============================================
# SERIALIZER 6: Survey Create
# ============================================
class SurveyCreateSerializer(serializers.ModelSerializer):
	"""
	Serializer for creating surveys
	"""

	class Meta:
		model = Survey
		fields = [
			"id",
			"title",
			"description",
			"access_type",
			"display_mode",
			"questions_per_page",
			"allow_multiple_responses",
			"show_progress_bar",
		]
		read_only_fields = ["id"]

	def validate_questions_per_page(self, value):
		"""Validate questions_per_page is positive"""
		if value < 1:
			raise serializers.ValidationError("Questions per page must be at least 1.")
		return value


# ============================================
# SERIALIZER 7: Allowed Email
# ============================================
class AllowedEmailSerializer(serializers.ModelSerializer):
	"""
	Serializer for allowed emails
	- User can create a list of emails for private surveys
	"""

	class Meta:
		model = AllowedEmail
		fields = ["id", "email", "created_at"]
		read_only_fields = ["id", "created_at"]


# ============================================
# SERIALIZER 8: Answer Selection (for responses)
# ============================================
class AnswerSelectionSerializer(serializers.ModelSerializer):
	"""
	Serializer for selected options in an answer
	"""

	option_text = serializers.CharField(
		source="selected_option.option_text", read_only=True
	)

	class Meta:
		model = AnswerSelection
		fields = ["id", "selected_option", "option_text"]
		read_only_fields = ["id", "option_text"]


# ============================================
# SERIALIZER 9: Answer (for responses)
# ============================================
class AnswerSerializer(serializers.ModelSerializer):
	"""
	Serializer for answers
	- Shows question and selected options
	"""

	selections = AnswerSelectionSerializer(many=True, read_only=True)
	question_text = serializers.CharField(
		source="question.question_text", read_only=True
	)

	class Meta:
		model = Answer
		fields = ["id", "question", "question_text", "selections", "created_at"]
		read_only_fields = ["id", "created_at"]


# ============================================
# SERIALIZER 10: Survey Response (Submit)
# ============================================
class SurveyResponseSerializer(serializers.ModelSerializer):
	"""
	Serializer for viewing survey responses
	"""

	answers = AnswerSerializer(many=True, read_only=True)
	respondent_email = serializers.SerializerMethodField()

	class Meta:
		model = SurveyResponse
		fields = [
			"id",
			"survey",
			"respondent_email",
			"started_at",
			"completed_at",
			"is_complete",
			"answers",
		]
		read_only_fields = ["id", "started_at", "completed_at"]

	def get_respondent_email(self, obj):
		"""
		Return email based on survey access type
		- If anonymous: return 'Anonymous'
		- If authenticated: return user email
		- If private invited: return respondent_email
		"""
		if obj.survey.access_type == "public_anonymous":
			return "Anonymous"
		elif obj.respondent:
			return obj.respondent.email
		elif obj.respondent_email:
			return obj.respondent_email
		return "Unknown"


# ============================================
# SERIALIZER 11: Submit Survey Response
# ============================================
class SubmitSurveyResponseSerializer(serializers.Serializer):
	"""
	Serializer for submitting survey responses

	Expected format:
	{
		"answers": [
			{
				"question_id": "uuid-here",
				"selected_options": ["option-uuid-1", "option-uuid-2"]
			},
			{
				"question_id": "uuid-here",
				"selected_options": ["option-uuid-1"]
			}
		]
	}
	"""

	answers = serializers.ListField(child=serializers.DictField(), required=True)

	def validate_answers(self, value):
		"""
		Validate answers format
		Each answer must have:
		- question_id (UUID)
		- selected_options (list of UUIDs)
		"""
		for answer in value:
			if "question_id" not in answer:
				raise serializers.ValidationError("Each answer must have 'question_id'")
			if "selected_options" not in answer:
				raise serializers.ValidationError(
					"Each answer must have 'selected_options'"
				)
			if not isinstance(answer["selected_options"], list):
				raise serializers.ValidationError("'selected_options' must be a list")
		return value
