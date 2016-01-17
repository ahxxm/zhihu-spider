import os

DB_HOST = os.environ.get("DB_HOST", "mongo")
DB_PORT = os.environ.get("DB_PORT", 27017)
SESSION_FILENAME = "session.p"

# Only z_c0 is required
COOKIE_KEY = "z_c0"
COOKIE_VALUE = """
values_after_"z_c0="
"""

CHROME_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/537.36 " \
            "(KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36"

# Go through this amount of users' answers.
EXPLORE_USER_COUNT = 200
EXPLORE_QUESTION_COUNT = 1000

CONCURRENCY = 10
