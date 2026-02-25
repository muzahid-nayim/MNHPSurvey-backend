# Changelog

All notable changes to this project will be documented in this file.

## Versioning Rules

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** version `X.0.0`: Increment for incompatible API changes or breaking changes.
- **MINOR** version `0.Y.0`: Increment for backward-compatible additions (new features, enhancements).
- **PATCH** version `0.0.Z`: Increment for backward-compatible bug fixes and documentation tweaks.

---

## [0.3.0] - 2026-02-25

### Added

- **Comprehensive Code Documentation**

    - Documented all 15 API views with their purposes and relationships
    - Added database relationship diagrams
    - Included common tasks with step-by-step explanations

- **Simplified & Refactored Code for Beginners**
    - Refactored `SurveyResponseListView` with helper methods for clarity
    - Split complex logic into `_get_question_statistics()` and `_get_option_statistics()` helpers
    - Refactored `TakeSurveyView` with `_verify_user_access()` helper for clearer logic
    - Enhanced `SurveyListCreateView` with improved comments and clarity
    - Enhanced `QuestionCreateView` with better step-by-step documentation

### Changed

- **Improved Code Readability**
    - Added detailed comments explaining each step in views
    - Enhanced docstrings with practical examples
    - Improved variable naming for clarity
    - Added step-by-step process explanations in all major views
    - Enhanced model documentation with relationship diagrams
    - Improved serializer documentation with usage examples

- **Better Error Handling**
    - More descriptive error messages in views
    - Clearer validation error handling in serializers

### Enhancement

- Code organization now optimized for new programmers to understand the codebase
- All complex methods broken down into smaller, focused helper methods
- Every function has comprehensive docstrings explaining inputs, outputs, and logic

## [0.3.0] - 2026-02-25

### Added

- Refactored views code for better readability and maintainability
- Enhanced code comments and docstrings throughout views, models, and serializers

### Changed

- Simplified complex view logic by breaking into helper methods
- Improved code organization for new programmers

## [0.2.8] - 2026-02-25

### Fixed

- **Critical: Fixed data loss bug** where editing questions/options cascading-deleted all survey responses
- Protected QuestionSerializer.update() to check if options have response data before deletion
- Added validation in QuestionOptionDetailView to block deletion of options referenced in responses
- Prevents cascading AnswerSelection deletion when modifying survey structure

## [0.2.7] - 2025-02-19

### Fixed

- Fixed first_name and last_name is not saving during ragistration by adding those field in serializer.

## [0.2.6] - 2025-01-05

### changes

- add user first name and last name field in serializer.

## [0.2.5] - 2025-12-30

### Fixed

Fixed question option not adding issue while editing question.

- Added custom update method to QuestionSerializer
- Handles create/update/delete of options based on incoming IDs
- Preserves existing option IDs while allowing new options
- Automatically removes options not included in update request
- No view changes needed - works with existing QuestionDetailView

## [0.2.4] - 2025-12-13

### Fixed

- Fixed some small issue and use reusavle ip tracker

## [0.2.3] - 2025-12-12

### Changed

-Use tab indentation all over the project.

## [0.2.3] - 2025-12-09

### Added

- AllowedEmail model for managing user's allowed email list (reusable across surveys)
- SurveyAllowedEmail model for linking surveys to allowed emails
- Email access control endpoints for private surveys
- Comprehensive documentation on models and relationships
- Professional section markers and comments in models, serializers, and views
- AllowedEmailSerializer for email management
- SurveyAllowedEmailsView for survey-specific email management
- Email validation in survey response submission

### Changed

- Migrated from SurveyInvitation model to AllowedEmail + SurveyAllowedEmail system
- Replaced sendInvitations endpoint with addSurveyAllowedEmails
- Updated API responses for email management endpoints
- Improved URL routing structure with better organization
- Enhanced serializer field control documentation

### Fixed

- Email access control security (verify user ownership)

## [0.2.2] - 2025-11-21

### Fixed

- sending user data in login response .

## [0.2.1] - 2025-11-16

### Fixed

- fixed some minor bugs .

## [0.2.0] - 2025-11-11

### Fixed

- fixed some minor bugs in CustomTokenObtainPairSerializer

## [0.2.0] - 2025-11-10

### Added

- Implemented basic survay functionality with models and serializers
- Created endpoints for creating, retrieving, updating, and deleting surveys
- Added survey response submission endpoint
- Integrated survey functionality with user authentication

### Fixed

- Fix some minor bugs in settings

## [0.1.0] - 2025-11-01

### Added

- Complete JWT authentication system with djangorestframework-simplejwt
- Custom User model with UUID primary key and email verification support
- User registration endpoint with automatic verification email
- Email verification system with 24-hour token expiry
- Resend verification email functionality
- Custom login endpoint with email verification check
- Token refresh endpoint for renewing access tokens
- Password reset request and confirmation endpoints with 1-hour token expiry
- Change password endpoint for authenticated users
- User profile view and update endpoints
- Logout functionality with token blacklisting
- Delete account endpoint with password confirmation
- Email utility functions for verification and password reset emails
- Token blacklist support for secure logout
- CORS configuration for Next.js frontend integration
- Environment variable support using python-decouple
- Custom token serializer with user data in login response

### Changed

- Migrated from default User model to custom User model
- Configured email backend to use SMTP (Gmail)
- Set ACCESS_TOKEN_LIFETIME to 60 minutes
- Set REFRESH_TOKEN_LIFETIME to 7 days
- Enabled token rotation and blacklisting after rotation

### Database Schema

- `users` table with UUID id, email, username, email verification status
- `email_verification_tokens` table for email verification
- `password_reset_tokens` table for password reset flow
- Token blacklist tables for secure logout

### Security

- Password validation with Django's built-in validators
- Email enumeration protection in password reset flow
- JWT token-based authentication
- Token blacklisting on logout
- Secure password hashing

## [0.0.1] - Initial Setup

### Added

- Initial project setup with Django 5.2.7 and Django Rest Framework
- Created `backend` project structure
- Configured SQLite database for development
- Basic project configuration and admin panel setup
