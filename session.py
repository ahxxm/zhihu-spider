import logging
import pickle
import requests
import os

from settings import SESSION_FILENAME, COOKIE_KEY, COOKIE_VALUE, CHROME_UA

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def validate_session(session: requests.session) -> bool:
    # Validate by visit settings, anonymous user will be redirected
    # to login page.
    settings_url = "https://www.zhihu.com/settings/profile"
    verify_rsp = session.get(settings_url)

    if not (verify_rsp.url == settings_url):
        obsolete_session_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             SESSION_FILENAME)
        if os.path.exists(obsolete_session_file):
            os.remove(obsolete_session_file)

        raise ValueError("check COOKIE_VALUE in settings.py.")

    return True


def get_or_create_session() -> requests.session:
    try:
        with open(SESSION_FILENAME, "rb") as session_dump:
            session = pickle.load(session_dump)
            log.debug("Session loaded for user")

    except FileNotFoundError:
        session = requests.session()

        # mount cookies and UA
        session.cookies.update({COOKIE_KEY: COOKIE_VALUE.strip()})
        session.headers["User-Agent"] = CHROME_UA

        # update cookies by visit website
        session.get("http://www.zhihu.com")

        validate_session(session)
        with open(SESSION_FILENAME, "wb") as session_dump:
            pickle.dump(session, session_dump)

    return session
