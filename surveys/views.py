# surveys/views.py
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action

from .models import (
    Survey, Question, QuestionOption, 
    SurveyInvitation, SurveyResponse, 
    Answer, AnswerSelection
)
from .serializers import (
    SurveyListSerializer, SurveyDetailSerializer, SurveyCreateSerializer,
    QuestionSerializer, QuestionCreateSerializer, QuestionOptionSerializer,
    SurveyInvitationSerializer, SurveyResponseSerializer,
    SubmitSurveyResponseSerializer
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
        if self.request.method == 'POST':
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
    lookup_field = 'id'
    
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
        survey_id = self.kwargs.get('survey_id')
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
        survey_id = self.kwargs.get('survey_id')
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
    lookup_field = 'id'
    
    def get_queryset(self):
        """User can only access questions from their surveys"""
        survey_id = self.kwargs.get('survey_id')
        return Question.objects.filter(survey__id=survey_id, survey__owner=self.request.user)


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
        question_id = self.kwargs.get('question_id')
        survey_id = self.kwargs.get('survey_id')
        
        # Check question exists and user owns the survey
        question = get_object_or_404(
            Question, 
            id=question_id, 
            survey__id=survey_id, 
            survey__owner=self.request.user
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
    lookup_field = 'id'
    
    def get_queryset(self):
        """User can only access options from their surveys"""
        survey_id = self.kwargs.get('survey_id')
        question_id = self.kwargs.get('question_id')
        return QuestionOption.objects.filter(
            question__id=question_id,
            question__survey__id=survey_id,
            question__survey__owner=self.request.user
        )


# ============================================
# VIEW 8: Send Invitations (Private Survey)
# ============================================
class SendInvitationsView(APIView):
    """
    POST: Send invitations to emails for private survey
    
    Endpoint: /api/surveys/<survey_id>/invite/
    
    Request body:
    {
        "emails": ["user1@example.com", "user2@example.com"]
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, survey_id):
        """
        Send invitations to list of emails
        
        Steps:
        1. Check survey exists and user owns it
        2. Check survey is 'private_invited' type
        3. Create invitation for each email
        4. Send invitation email (TODO: implement email sending)
        5. Return list of created invitations
        """
        # Step 1: Get survey
        survey = get_object_or_404(Survey, id=survey_id, owner=request.user)
        
        # Step 2: Check survey type
        if survey.access_type != 'private_invited':
            return Response(
                {"error": "Can only send invitations to private surveys."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Step 3: Get emails from request
        emails = request.data.get('emails', [])
        if not emails or not isinstance(emails, list):
            return Response(
                {"error": "Please provide a list of emails."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Step 4: Create invitations
        created_invitations = []
        for email in emails:
            # Check if already invited
            invitation, created = SurveyInvitation.objects.get_or_create(
                survey=survey,
                email=email
            )
            if created:
                created_invitations.append(invitation)
                # TODO: Send email with invitation link
                # send_invitation_email(invitation)
        
        # Step 5: Return created invitations
        serializer = SurveyInvitationSerializer(created_invitations, many=True)
        return Response({
            "message": f"Invited {len(created_invitations)} users.",
            "invitations": serializer.data
        }, status=status.HTTP_201_CREATED)


# ============================================
# VIEW 9: List Invitations
# ============================================
class InvitationListView(generics.ListAPIView):
    """
    GET: List all invitations for a survey
    
    Endpoint: /api/surveys/<survey_id>/invitations/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SurveyInvitationSerializer
    
    def get_queryset(self):
        """Get all invitations for this survey"""
        survey_id = self.kwargs.get('survey_id')
        survey = get_object_or_404(Survey, id=survey_id, owner=self.request.user)
        return SurveyInvitation.objects.filter(survey=survey)


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
        
        # Step 2: Check status
        if survey.status != 'active':
            return Response(
                {"error": "This survey is not currently accepting responses."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Step 3: Check access based on access_type
        if survey.access_type == 'public_anonymous':
            # Anyone can access
            pass
        
        elif survey.access_type == 'public_authenticated':
            # Must be logged in
            if not request.user.is_authenticated:
                return Response(
                    {"error": "You must be logged in to access this survey."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        elif survey.access_type == 'private_invited':
            # Must have valid invitation token
            token = request.query_params.get('token')
            if not token:
                return Response(
                    {"error": "Invitation token required."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Verify token
            invitation = get_object_or_404(SurveyInvitation, survey=survey, token=token)
            
            # Update opened_at if first time
            if not invitation.opened_at:
                invitation.opened_at = timezone.now()
                invitation.status = 'opened'
                invitation.save()
        
        # Step 4: Return survey
        serializer = SurveyDetailSerializer(survey)
        return Response(serializer.data)


# ============================================
# VIEW 11: Submit Survey Response
# ============================================
class SubmitSurveyResponseView(APIView):
    """
    POST: Submit survey response
    
    Endpoint: /api/surveys/submit/<survey_id>/
    or: /api/surveys/submit/<survey_id>/?token=<invitation_token>
    
    Request body:
    {
        "answers": [
            {
                "question_id": "uuid-here",
                "selected_options": ["option-uuid-1", "option-uuid-2"]
            }
        ]
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request, survey_id):
        """
        Submit survey response
        
        Steps:
        1. Validate request data
        2. Check survey access
        3. Create SurveyResponse
        4. Create Answers and AnswerSelections
        5. Mark response as complete
        6. Update invitation if applicable
        """
        # Step 1: Validate
        serializer = SubmitSurveyResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Step 2: Get survey
        survey = get_object_or_404(Survey, id=survey_id)
        
        if survey.status != 'active':
            return Response(
                {"error": "Survey is not accepting responses."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Step 3: Check access and prepare response data
        response_data = {
            'survey': survey,
            'ip_address': self.get_client_ip(request)
        }
        
        invitation = None
        
        if survey.access_type == 'public_anonymous':
            # Anonymous - no user tracking
            pass
        
        elif survey.access_type == 'public_authenticated':
            # Must be logged in
            if not request.user.is_authenticated:
                return Response(
                    {"error": "Login required."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            response_data['respondent'] = request.user
            
            # Check if already responded
            if not survey.allow_multiple_responses:
                existing = SurveyResponse.objects.filter(
                    survey=survey,
                    respondent=request.user,
                    is_complete=True
                ).exists()
                if existing:
                    return Response(
                        {"error": "You have already responded to this survey."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        elif survey.access_type == 'private_invited':
            # Must have valid token
            token = request.query_params.get('token')
            if not token:
                return Response(
                    {"error": "Invitation token required."},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            invitation = get_object_or_404(SurveyInvitation, survey=survey, token=token)
            
            # Check if already completed
            if invitation.status == 'completed':
                return Response(
                    {"error": "You have already completed this survey."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            response_data['invitation'] = invitation
        
        # Step 4: Create response
        survey_response = SurveyResponse.objects.create(**response_data)
        
        # Step 5: Create answers
        answers_data = serializer.validated_data['answers']
        
        for answer_data in answers_data:
            question_id = answer_data['question_id']
            selected_option_ids = answer_data['selected_options']
            
            # Get question
            try:
                question = Question.objects.get(id=question_id, survey=survey)
            except Question.DoesNotExist:
                survey_response.delete()  # Rollback
                return Response(
                    {"error": f"Question {question_id} not found in this survey."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create answer
            answer = Answer.objects.create(
                response=survey_response,
                question=question
            )
            
            # Create selections
            for option_id in selected_option_ids:
                try:
                    option = QuestionOption.objects.get(id=option_id, question=question)
                    AnswerSelection.objects.create(
                        answer=answer,
                        selected_option=option
                    )
                except QuestionOption.DoesNotExist:
                    survey_response.delete()  # Rollback
                    return Response(
                        {"error": f"Option {option_id} not found for question {question_id}."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Validate single vs multiple choice
            if question.question_type == 'single_choice' and len(selected_option_ids) > 1:
                survey_response.delete()  # Rollback
                return Response(
                    {"error": f"Question '{question.question_text}' allows only one answer."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Step 6: Mark as complete
        survey_response.is_complete = True
        survey_response.completed_at = timezone.now()
        survey_response.save()
        
        # Step 7: Update invitation if applicable
        if invitation:
            invitation.completed_at = timezone.now()
            invitation.status = 'completed'
            invitation.save()
        
        return Response({
            "message": "Survey submitted successfully!",
            "response_id": str(survey_response.id)
        }, status=status.HTTP_201_CREATED)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ============================================
# VIEW 12: View Survey Responses (Survey Owner)
# ============================================
class SurveyResponseListView(generics.ListAPIView):
    """
    GET: List all responses for a survey
    
    Endpoint: /api/surveys/<survey_id>/responses/
    
    Only survey owner can view responses
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SurveyResponseSerializer
    
    def get_queryset(self):
        """Get all complete responses for this survey"""
        survey_id = self.kwargs.get('survey_id')
        survey = get_object_or_404(Survey, id=survey_id, owner=self.request.user)
        return SurveyResponse.objects.filter(survey=survey, is_complete=True)


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
    lookup_field = 'id'
    
    def get_queryset(self):
        """User can only view responses from their surveys"""
        survey_id = self.kwargs.get('survey_id')
        return SurveyResponse.objects.filter(
            survey__id=survey_id,
            survey__owner=self.request.user,
            is_complete=True
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
        
        new_status = request.data.get('status')
        
        if new_status not in ['draft', 'active', 'closed']:
            return Response(
                {"error": "Invalid status. Choose: draft, active, or closed."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate survey has questions before publishing
        if new_status == 'active' and survey.questions.count() == 0:
            return Response(
                {"error": "Cannot publish survey without questions."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        survey.status = new_status
        survey.save()
        
        return Response({
            "message": f"Survey status updated to '{new_status}'.",
            "status": survey.status
        })