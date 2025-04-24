# Edocebiv

A Django web application with Google OAuth authentication.

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/edocebiv.git
   cd edocebiv
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create settings.py from the template:
   ```bash
   cp edocebiv/settings_template.py edocebiv/settings.py
   ```

5. Edit the settings.py file:
   - Generate a new SECRET_KEY
   - Update the Google OAuth credentials with your own
   - Adjust other settings as needed

6. Run migrations:
   ```bash
   python manage.py migrate
   ```

7. Create a superuser (optional):
   ```bash
   python manage.py createsuperuser
   ```

8. Run the development server:
   ```bash
   python manage.py runserver
   ```

9. Access the application at http://localhost:8000

### Google OAuth Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to "APIs & Services" > "Credentials"
4. Create an OAuth 2.0 Client ID
5. Add the following authorized redirect URIs:
   - http://localhost:8000/accounts/google/login/callback/
   - https://edocebiv.com/accounts/google/login/callback/ (for production)
6. Copy the Client ID and Client Secret to your settings.py file

## Features

- User authentication with email and password
- Google OAuth sign-in
- User profile management
- Responsive design with Bootstrap

## License

This project is licensed under the terms of the license included in the repository.
