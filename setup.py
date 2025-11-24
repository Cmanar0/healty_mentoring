# setup.py - orchestrates build & deploy behavior based on DEVELOPMENT_MODE env variable
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "dev").lower()
PROJECT_DIR = Path(__file__).parent

def run_command(cmd):
    print("> " + cmd)
    rc = os.system(cmd)
    if rc != 0:
        print("Command failed:", cmd)
        sys.exit(rc)

def dev():
    print("Building in development mode (DEVELOPMENT_MODE='dev').")
    print("Installing requirements...")
    run_command("pip install -r requirements.txt")
    print("Applying migrations...")
    run_command("python manage.py migrate")
    print("Collect static (development uses static served by Django; whitenoise optional).")
    run_command("python manage.py collectstatic --noinput")
    print("Starting dev server on 127.0.0.1:8000")
    run_command("python manage.py runserver 0.0.0.0:8000")

def prod():
    print("Prepare production artifacts (DEVELOPMENT_MODE='prod').")
    # Simply build and up the unified stack
    run_command("docker compose -f docker-compose.yml build")
    run_command("docker compose -f docker-compose.yml up -d")

def main():
    if DEVELOPMENT_MODE == "dev" or DEVELOPMENT_MODE == "development":
        dev()
    elif DEVELOPMENT_MODE == "prod" or DEVELOPMENT_MODE == "production":
        prod()
    else:
        print("Unknown DEVELOPMENT_MODE:", DEVELOPMENT_MODE)
        print("Use 'dev' or 'prod'.")
        sys.exit(1)

if __name__ == "__main__":
    main()
