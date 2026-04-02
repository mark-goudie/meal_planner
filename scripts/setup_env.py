#!/usr/bin/env python3
"""
Environment setup script for Django Meal Planner.

This script helps generate secure configuration values and validates environment setup.
"""

import secrets
import string
import sys
from pathlib import Path


def generate_secret_key():
    """Generate a secure Django secret key."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return "".join(secrets.choice(chars) for _ in range(50))


def create_env_file(environment="development"):
    """Create a .env file with secure defaults."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"

    if env_file.exists():
        response = input(".env file already exists. Overwrite? (y/N): ")
        if response.lower() != "y":
            print("Aborted.")
            return

    secret_key = generate_secret_key()

    env_content = f"""# Django Meal Planner Environment Configuration
# Generated automatically - customize as needed

# Environment setting
DJANGO_ENVIRONMENT={environment}

# Security
SECRET_KEY={secret_key}
DEBUG={'True' if environment == 'development' else 'False'}
ALLOWED_HOSTS={'localhost,127.0.0.1,0.0.0.0' if environment == 'development' else 'yourdomain.com'}

# Localization
TIME_ZONE=Australia/Sydney

# API Keys (add your keys here)
ANTHROPIC_API_KEY=

# Database (PostgreSQL for staging/production)
DB_NAME=meal_planner_db
DB_USER=meal_planner_user
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
DB_SSLMODE=require

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@mealplanner.com
SERVER_EMAIL=server@mealplanner.com

# Cache (Redis for staging/production)
REDIS_URL=redis://127.0.0.1:6379/1

# Security (production)
CSRF_TRUSTED_ORIGINS=https://yourdomain.com

# Logging
LOG_FILE=/var/log/meal_planner/app.log

# Optional: Error Tracking
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.1

# Admin emails (format: Name,email@example.com)
ADMINS=Admin Name,admin@example.com
"""

    with open(env_file, "w") as f:
        f.write(env_content)

    print(f"✓ Created .env file for {environment} environment")
    print("✓ Generated secure SECRET_KEY")
    print("\nNext steps:")
    print("1. Edit .env file with your specific configuration")
    print("2. Add your API keys and database credentials")
    print("3. Run: python manage.py migrate")
    print("4. Run: python manage.py createsuperuser")


def validate_environment():
    """Validate that all required environment variables are set."""
    try:
        from decouple import config
    except ImportError:
        print("❌ python-decouple not installed. Run: pip install python-decouple")
        return False

    required_vars = {
        "SECRET_KEY": "Django secret key",
        "DJANGO_ENVIRONMENT": "Django environment (development/staging/production)",
        "ALLOWED_HOSTS": "Comma-separated list of allowed hosts",
    }

    optional_vars = {
        "ANTHROPIC_API_KEY": "Anthropic API key for AI features",
        "DB_NAME": "Database name (required for staging/production)",
        "DB_USER": "Database user (required for staging/production)",
        "DB_PASSWORD": "Database password (required for staging/production)",
        "EMAIL_HOST_USER": "Email host user for sending emails",
        "REDIS_URL": "Redis URL for caching (required for staging/production)",
    }

    print("Validating environment configuration...")
    print("\nRequired variables:")

    all_good = True
    for var, description in required_vars.items():
        try:
            value = config(var)
            if value:
                print(f"✓ {var}: {description}")
            else:
                print(f"❌ {var}: {description} (empty)")
                all_good = False
        except Exception:
            print(f"❌ {var}: {description} (missing)")
            all_good = False

    print("\nOptional variables:")
    for var, description in optional_vars.items():
        try:
            value = config(var, default="")
            if value:
                print(f"✓ {var}: {description}")
            else:
                print(f"⚠️  {var}: {description} (not set)")
        except Exception:
            print(f"⚠️  {var}: {description} (not set)")

    environment = config("DJANGO_ENVIRONMENT", default="development")
    if environment in ["staging", "production"]:
        print("\nProduction/Staging specific checks:")
        prod_required = ["DB_NAME", "DB_USER", "DB_PASSWORD", "REDIS_URL"]
        for var in prod_required:
            try:
                value = config(var)
                if value:
                    print(f"✓ {var}: Required for {environment}")
                else:
                    print(f"❌ {var}: Required for {environment} (empty)")
                    all_good = False
            except Exception:
                print(f"❌ {var}: Required for {environment} (missing)")
                all_good = False

    return all_good


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Django Meal Planner Environment Setup")
        print("\nUsage:")
        print("  python setup_env.py create [environment]  - Create .env file")
        print("  python setup_env.py validate              - Validate environment")
        print("  python setup_env.py generate-key          - Generate secret key")
        print("\nEnvironments: development (default), staging, production")
        return

    command = sys.argv[1]

    if command == "create":
        environment = sys.argv[2] if len(sys.argv) > 2 else "development"
        if environment not in ["development", "staging", "production"]:
            print("❌ Invalid environment. Use: development, staging, or production")
            return
        create_env_file(environment)

    elif command == "validate":
        if validate_environment():
            print("\n✅ Environment configuration looks good!")
        else:
            print(
                "\n❌ Environment configuration has issues. Please fix the errors above."
            )
            sys.exit(1)

    elif command == "generate-key":
        print("Generated Django SECRET_KEY:")
        print(generate_secret_key())

    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
