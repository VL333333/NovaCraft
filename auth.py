"""Вхід через Microsoft (OAuth 2.0 + PKCE) за допомогою minecraft_launcher_lib."""
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from minecraft_launcher_lib import microsoft_account as ms
from minecraft_launcher_lib.exceptions import InvalidRefreshToken, SecurityError

import config
import storage
from errors import AuthError

_PAGE = ("<html><head><meta charset='utf-8'><title>MyCraft Launcher</title></head>"
         "<body style='font-family:Segoe UI,sans-serif;background:#1e1f22;color:#f2f3f5;"
         "text-align:center;padding-top:80px'><h2>Вхід виконано</h2>"
         "<p>Можна закрити цю вкладку й повернутися до лаунчера.</p></body></html>")


def _wait_for_redirect() -> tuple[HTTPServer, dict]:
    result: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            query = parse_qs(urlparse(self.path).query)
            if "code" in query or "error" in query:
                result["path"] = self.path
                body = _PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:  # напр. запит favicon.ico
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):  # без виводу в консоль
            pass

    try:
        server = HTTPServer(("127.0.0.1", config.REDIRECT_PORT), Handler)
    except OSError as e:
        raise AuthError(
            f"Не вдалося відкрити локальний порт {config.REDIRECT_PORT} для входу "
            f"(можливо, зайнятий іншою програмою або лаунчер уже запущено): {e}"
        )
    server.timeout = 1
    return server, result


def interactive_login() -> dict:
    login_url, state, code_verifier = ms.get_secure_login_data(
        config.CLIENT_ID, config.REDIRECT_URI
    )
    server, result = _wait_for_redirect()  # сервер стартує ДО відкриття браузера
    try:
        webbrowser.open(login_url)
        deadline = time.monotonic() + config.LOGIN_TIMEOUT_SECONDS
        while "path" not in result and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()

    if "path" not in result:
        raise AuthError("Час очікування входу вичерпано. Натисніть «ГРАТИ» і завершіть вхід у браузері.")

    query = parse_qs(urlparse(result["path"]).query)
    if "error" in query:
        desc = query.get("error_description", query["error"])[0]
        raise AuthError(f"Microsoft повернув помилку входу: {desc}")

    try:
        code = ms.parse_auth_code_url(config.REDIRECT_URI + result["path"], state)
    except (AssertionError, SecurityError, KeyError):
        raise AuthError("Перевірка безпеки входу (state) не пройшла. Спробуйте увійти ще раз.")

    return ms.complete_login(
        client_id=config.CLIENT_ID,
        client_secret=None,
        redirect_uri=config.REDIRECT_URI,
        auth_code=code,
        code_verifier=code_verifier,
    )


def get_account(on_detail) -> dict:
    """Повертає dict з ключами id, name, access_token, refresh_token."""
    saved = storage.load_account()
    refresh_token = saved.get("refresh_token")
    if refresh_token:
        on_detail("Оновлення входу…")
        try:
            data = ms.complete_refresh(
                client_id=config.CLIENT_ID,
                client_secret=None,
                redirect_uri=None,
                refresh_token=refresh_token,
            )
            storage.save_account(data["name"], data["id"], data.get("refresh_token", refresh_token))
            return data
        except InvalidRefreshToken:
            storage.clear_account()  # потрібен новий вхід

    on_detail("Завершіть вхід у браузері…")
    data = interactive_login()
    storage.save_account(data["name"], data["id"], data["refresh_token"])
    return data
