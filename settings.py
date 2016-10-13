import os

DB_HOST = os.environ.get("DB_HOST", "mongo")
DB_PORT = os.environ.get("DB_PORT", 27017)
SESSION_FILENAME = "session.p"

# Only z_c0 is required
COOKIE_KEY = "z_c0"
COOKIE_VALUE = """
REPLACE_THIS_LINE_WITH_values_after_"z_c0="
"""

CHROME_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/537.36 " \
            "(KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36"

# Go through this amount of users' answers.
EXPLORE_USER_COUNT = 200
EXPLORE_QUESTION_COUNT = 100

CONCURRENCY = 10

SOCKS_ADDR = "localhost"
SOCKS_PORT = 1080
