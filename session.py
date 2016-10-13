import asyncio
import aiohttp
import aiosocks
import logging
import os
import pickle


from settings import SESSION_FILENAME, COOKIE_KEY, COOKIE_VALUE, CHROME_UA
from settings import SOCKS_ADDR, SOCKS_PORT

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def validate_session(session: aiohttp.ClientSession) -> bool:
    # Validate by visit settings, anonymous user will be redirected
    # to login page.
    settings_url = "https://www.zhihu.com/settings/profile"
    verify_rsp = yield from session.get(settings_url)
    verify_rsp.close()

    if not (verify_rsp.url == settings_url):
        old_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                SESSION_FILENAME)
        if os.path.exists(old_file):
            os.remove(old_file)

        raise ValueError("check COOKIE_VALUE in settings.py.")

    return True


def gen_conn():
    if SOCKS_ADDR == "" and SOCKS_ADDR == 0:
        connector = aiohttp.TCPConnector(conn_timeout=10,
                                         keepalive_timeout=300,
                                         use_dns_cache=True,
                                         share_cookies=True)
    else:
        # FIXME:
        log.info("Using socks5: {}:{}".format(SOCKS_ADDR, SOCKS_PORT))
        from aiosocks.connector import proxy_connector
        addr = aiosocks.Socks5Addr(SOCKS_ADDR, SOCKS_PORT)
        connector = proxy_connector(proxy=addr, remote_resolve=False)
    return connector


def get_or_create_session() -> aiohttp.ClientSession:
    conn = gen_conn()
    try:
        with open(SESSION_FILENAME, "rb") as session_dump:
            cookies = pickle.load(session_dump)
            session = aiohttp.ClientSession(headers={"User-Agent": CHROME_UA},
                                            connector=conn, cookies=cookies)
            log.debug("Session loaded for user")

    except FileNotFoundError:
        # Aiohttp session
        # mount cookies and UA
        cookies = {COOKIE_KEY: COOKIE_VALUE}
        session = aiohttp.ClientSession(headers={"User-Agent": CHROME_UA},
                                        connector=conn, cookies=cookies)
        session._cookie_jar.update_cookies({COOKIE_KEY: COOKIE_VALUE.strip()})

        # update cookies by visit website
        validate_session(session)
        with open(SESSION_FILENAME, "wb") as session_dump:
            pickle.dump(session.cookies, session_dump)

    return session


@asyncio.coroutine
def test(session):
    rsp = yield from session.get("https://www.zhihu.com/settings/profile")
    r = yield from rsp.read()
    return r


if __name__ == "__main__":
    session = get_or_create_session()
    loop = asyncio.get_event_loop()
    ff = asyncio.wait([test(session)])
    rr = loop.run_until_complete(ff)
    bb = rr[0].pop()
    aa = bb.result()
    print(aa.decode())
