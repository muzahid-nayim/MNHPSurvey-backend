# MNHPSurvey Backend Setup Instructions

# 1. Clone the Repository
git clone <repository-url>
cd MNHPSurvey/Backend

# 2. Create and Activate Virtual Environment
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Set Up Environment Variables
# Create a .env file in the project root and add:
DEBUG=True
SECRET_KEY=<your-secret-key>
DATABASE_URL=postgres://user:password@localhost:5432/dbname

# 5. Apply Migrations
python manage.py makemigrations
python manage.py migrate

# 6. Create Superuser
python manage.py createsuperuser

# 7. Run the Development Server
python manage.py runserver

# Usage
# Access the admin panel at http://127.0.0.1:8000/admin/ using the superuser credentials
