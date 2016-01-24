import logging
import pickle
import aiohttp
import os

from settings import SESSION_FILENAME, COOKIE_KEY, COOKIE_VALUE, CHROME_UA

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def validate_session(session: aiohttp.ClientSession) -> bool:
    # Validate by visit settings, anonymous user will be redirected
    # to login page.
    settings_url = "https://www.zhihu.com/settings/profile"
    verify_rsp = yield from session.get(settings_url)
    verify_rsp.close()

    if not (verify_rsp.url == settings_url):
        obsolete_session_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             SESSION_FILENAME)
        if os.path.exists(obsolete_session_file):
            os.remove(obsolete_session_file)

        raise ValueError("check COOKIE_VALUE in settings.py.")

    return True


def get_or_create_session() -> aiohttp.ClientSession:
    try:
        with open(SESSION_FILENAME, "rb") as session_dump:
            session = pickle.load(session_dump)
            log.debug("Session loaded for user")

    except FileNotFoundError:
        # Request Session
        # session = requests.session()
        # session.headers["User-Agent"] = CHROME_UA
        # session.cookies.update({COOKIE_KEY: COOKIE_VALUE.strip()})

        # Aiohttp session
        # mount cookies and UA
        connector = aiohttp.TCPConnector(conn_timeout=5, keepalive_timeout=10)
        session = aiohttp.ClientSession(headers={"User-Agent": CHROME_UA},
                                        connector=connector)
        session.cookies[COOKIE_KEY] = COOKIE_VALUE

        # update cookies by visit website
        session.get("http://www.zhihu.com")

        validate_session(session)

        # Aiohttp session can't be serialized.
        # with open(SESSION_FILENAME, "wb") as session_dump:
        #     pickle.dump(session, session_dump)

    return session
