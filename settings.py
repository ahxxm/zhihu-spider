import os

DB_HOST = os.environ.get("DB_HOST", "mongo")
DB_PORT = os.environ.get("DB_PORT", 27017)
SESSION_FILENAME = "session.p"

# Only z_c0 is required
COOKIES = 'z_c0="cookiecontent"'

# Go through this amount of users' answers.
EXPLORE_USER_COUNT = 200
EXPLORE_QUESTION_COUNT = 1000

CONCURRENCY = 10
