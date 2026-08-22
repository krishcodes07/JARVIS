"""
OAuth 2.0 Loopback & PKCE Engine for JARVIS.

Implements RFC 8252 (OAuth 2.0 for Native Apps) using a local loopback
redirect server (http://127.0.0.1:port/callback), PKCE challenge generation,
system browser launch, and automated token exchange.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import secrets
import socket
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

import httpx

from jarvis.core.paths import get_jarvis_home
from jarvis.mcp.auth.token_store import token_store

logger = logging.getLogger(__name__)

# Premium Dark-Themed Callback HTML Page
SUCCESS_HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>JARVIS — Authentication Successful</title>
  <style>
    :root {
      --bg: #090d16;
      --card-bg: rgba(18, 26, 44, 0.85);
      --border: rgba(56, 189, 248, 0.25);
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --success: #22c55e;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: radial-gradient(circle at 50% 0%, #1e293b 0%, var(--bg) 80%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 2.5rem;
      max-width: 480px;
      width: 100%;
      text-align: center;
      box-shadow: 0 20px 45px -10px rgba(0, 0, 0, 0.6), 0 0 25px rgba(56, 189, 248, 0.15);
      backdrop-filter: blur(12px);
      animation: fadeIn 0.4s ease-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .icon-container {
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: rgba(34, 197, 94, 0.15);
      border: 2px solid var(--success);
      color: var(--success);
      font-size: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1.5rem auto;
    }
    h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem; color: #ffffff; }
    p { font-size: 0.95rem; color: var(--text-muted); line-height: 1.5; margin-bottom: 1.75rem; }
    .badge {
      display: inline-block;
      padding: 0.35rem 0.85rem;
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: var(--accent);
      border-radius: 9999px;
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.03em;
      margin-bottom: 1.25rem;
    }
    .footer {
      font-size: 0.85rem;
      color: #64748b;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 1.25rem;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon-container">✓</div>
    <div class="badge">JARVIS INTEGRATION ACTIVE</div>
    <h1>Authentication Successful</h1>
    <p>Your account has been connected to <strong>JARVIS</strong>. You can safely close this browser tab and return to your terminal.</p>
    <div class="footer">Model Context Protocol • Secure Local OAuth Loopback</div>
  </div>
</body>
</html>
"""

ERROR_HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>JARVIS — Authentication Failed</title>
  <style>
    body { font-family: sans-serif; background: #090d16; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
    .card { background: rgba(18, 26, 44, 0.9); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 16px; padding: 2.5rem; max-width: 480px; text-align: center; }
    h1 { color: #ef4444; margin-bottom: 1rem; }
    p { color: #94a3b8; line-height: 1.5; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Authentication Failed</h1>
    <p>JARVIS was unable to complete authentication. Please return to the terminal and try again.</p>
  </div>
</body>
</html>
"""


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE (code_verifier, code_challenge) with SHA-256."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return code_verifier, code_challenge


def find_free_port() -> int:
    """Find an available port on 127.0.0.1."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return int(s.getsockname()[1])


class _OAuthHTTPServer(HTTPServer):
    """Internal HTTPServer carrying captured OAuth query parameters."""

    auth_params: dict[str, str]

    def __init__(self, server_address: tuple[str, int], RequestHandlerClass: type[BaseHTTPRequestHandler]) -> None:
        super().__init__(server_address, RequestHandlerClass)
        self.auth_params = {}


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Internal HTTP handler for capturing OAuth loopback redirects."""

    server: _OAuthHTTPServer

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress standard logging to keep terminal clean
        pass

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # Store captured query params in server instance
        self.server.auth_params = {k: v[0] for k, v in params.items() if v}

        if "code" in params:
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(SUCCESS_HTML_PAGE.encode("utf-8"))
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(ERROR_HTML_PAGE.encode("utf-8"))


class OAuthLoopbackServer:
    """Ephemeral loopback server for native desktop browser authentication."""

    def __init__(self, port: int | None = None) -> None:
        self.port = port or find_free_port()
        self.redirect_uri = f"http://127.0.0.1:{self.port}/callback"
        self._httpd: _OAuthHTTPServer | None = None
        self._server_thread: Thread | None = None

    def start(self) -> None:
        """Start the loopback server in a background thread."""
        self._httpd = _OAuthHTTPServer(("127.0.0.1", self.port), _OAuthCallbackHandler)
        self._server_thread = Thread(target=self._httpd.serve_forever, daemon=True)
        self._server_thread.start()
        logger.debug("OAuth loopback server listening on %s", self.redirect_uri)

    def stop(self) -> None:
        """Shut down the loopback server."""
        if self._httpd:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception as e:
                logger.debug("Error shutting down loopback server: %s", e)
            self._httpd = None

    async def wait_for_callback(self, timeout_seconds: float = 120.0) -> dict[str, str]:
        """Wait for the user to complete browser authentication and return parameters."""
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
            if self._httpd and self._httpd.auth_params:
                params = self._httpd.auth_params
                if "code" in params or "error" in params:
                    return dict(params)
            await asyncio.sleep(0.2)

        raise TimeoutError(f"OAuth authentication timed out after {timeout_seconds}s.")


class GoogleOAuthHelper:
    """Google Workspace OAuth 2.0 flow helper (Gmail, Calendar, Drive)."""

    # Standard Google OAuth 2.0 endpoints
    AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URI = "https://oauth2.googleapis.com/token"
    USERINFO_URI = "https://www.googleapis.com/oauth2/v2/userinfo"

    # Default Google Scopes for Gmail & Productivity
    DEFAULT_SCOPES = [
        "https://mail.google.com/",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar",
        "openid",
        "email",
        "profile",
    ]

    # Optional default Google Cloud Desktop App Client credentials
    DEFAULT_CLIENT_ID = ""
    DEFAULT_CLIENT_SECRET = None

    @classmethod
    def get_client_credentials(cls) -> tuple[str, str | None]:
        """Get Google OAuth client ID and secret from env, credential files, or built-in defaults."""
        client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip() or None

        # Check for credential files if not in env
        if not client_id:
            candidate_paths = [
                get_jarvis_home() / "auth" / "google_client.json",
                get_jarvis_home() / "auth" / "credentials.json",
                get_jarvis_home() / "auth" / "client_secret.json",
                Path.cwd() / "credentials.json",
                Path.cwd() / "client_secret.json",
            ]
            for p in candidate_paths:
                if p.exists():
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                        installed = data.get("installed", data.get("web", data))
                        c_id = installed.get("client_id")
                        c_secret = installed.get("client_secret")
                        if c_id:
                            client_id = str(c_id).strip()
                            client_secret = str(c_secret).strip() if c_secret else None
                            logger.info("Loaded Google OAuth credentials from %s", p)
                            break
                    except Exception as e:
                        logger.debug("Failed parsing credentials file %s: %s", p, e)

        # Fallback to built-in official JARVIS Desktop App credentials
        if not client_id:
            client_id = cls.DEFAULT_CLIENT_ID
            if not client_secret:
                client_secret = cls.DEFAULT_CLIENT_SECRET

        return client_id, client_secret

    @classmethod
    async def start_browser_login(
        cls,
        scopes: list[str] | None = None,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Initiate OAuth loopback browser login for Google Workspace."""
        client_id, client_secret = cls.get_client_credentials()
        scopes = scopes or cls.DEFAULT_SCOPES

        loopback = OAuthLoopbackServer()
        loopback.start()

        code_verifier, code_challenge = generate_pkce_pair()
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        auth_params = {
            "client_id": client_id,
            "redirect_uri": loopback.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{cls.AUTH_URI}?{urllib.parse.urlencode(auth_params)}"

        logger.info("Opening system browser for Google OAuth: %s", loopback.redirect_uri)
        try:
            # Launch browser
            webbrowser.open(auth_url)

            # Wait for callback
            callback_params = await loopback.wait_for_callback(timeout_seconds=timeout)

            if "error" in callback_params:
                raise ValueError(f"Google OAuth Error: {callback_params.get('error_description', callback_params['error'])}")

            received_code = callback_params.get("code")
            received_state = callback_params.get("state")

            if received_state != state:
                raise ValueError("OAuth State mismatch (possible CSRF attack).")

            if not received_code:
                raise ValueError("No authorization code received in callback.")

            # Exchange authorization code for tokens
            token_payload = {
                "client_id": client_id,
                "grant_type": "authorization_code",
                "code": received_code,
                "redirect_uri": loopback.redirect_uri,
                "code_verifier": code_verifier,
            }
            if client_secret:
                token_payload["client_secret"] = client_secret

            token_data: dict[str, Any] = {}
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(cls.TOKEN_URI, data=token_payload)
                if res.status_code != 200:
                    raise ValueError(f"Failed to exchange OAuth code: {res.text}")
                parsed_json = res.json()
                token_data = dict(parsed_json) if isinstance(parsed_json, dict) else {}

                # Fetch user profile email
                email_addr = ""
                access_token = token_data.get("access_token")
                if access_token:
                    try:
                        u_res = await client.get(
                            cls.USERINFO_URI,
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
                        if u_res.status_code == 200:
                            u_data = u_res.json()
                            email_addr = u_data.get("email", "")
                            token_data["email"] = email_addr
                    except Exception as e:
                        logger.debug("Failed to fetch user email: %s", e)

            # Save to persistent token store
            token_data["client_id"] = client_id
            if client_secret:
                token_data["client_secret"] = client_secret
            token_store.save_token("google", token_data)

            # Sync to environment and ~/.jarvis/.env
            if email_addr:
                os.environ["GMAIL_EMAIL"] = email_addr
            if access_token:
                os.environ["GMAIL_ACCESS_TOKEN"] = access_token

            env_updates: dict[str, str] = {}
            if email_addr:
                env_updates["GMAIL_EMAIL"] = email_addr
            if access_token:
                env_updates["GMAIL_ACCESS_TOKEN"] = access_token
            if env_updates:
                try:
                    env_file = get_jarvis_home() / ".env"
                    env_file.parent.mkdir(parents=True, exist_ok=True)
                    lines: list[str] = []
                    if env_file.exists():
                        lines = env_file.read_text(encoding="utf-8").splitlines()
                    existing_keys = set()
                    new_lines = []
                    for line in lines:
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#") and "=" in stripped:
                            k, _ = stripped.split("=", 1)
                            k = k.strip()
                            if k in env_updates:
                                new_lines.append(f'{k}="{env_updates[k]}"')
                                existing_keys.add(k)
                                continue
                        new_lines.append(line)
                    for k, v in env_updates.items():
                        if k not in existing_keys:
                            new_lines.append(f'{k}="{v}"')
                    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                except Exception as e:
                    logger.debug("Failed updating ~/.jarvis/.env with Google OAuth credentials: %s", e)

            logger.info("Google OAuth successfully authenticated for '%s'", email_addr or "user")
            return token_data

        finally:
            loopback.stop()

    @classmethod
    async def refresh_access_token(cls) -> str | None:
        """Refresh Google access token using the stored refresh_token."""
        stored = token_store.get_token("google")
        if not stored:
            return None

        refresh_token = stored.get("refresh_token")
        if not refresh_token:
            return None

        client_id, client_secret = cls.get_client_credentials()
        client_id = stored.get("client_id") or client_id
        client_secret = stored.get("client_secret") or client_secret

        payload = {
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        if client_secret:
            payload["client_secret"] = client_secret

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(cls.TOKEN_URI, data=payload)
                if res.status_code == 200:
                    new_data = res.json()
                    stored.update(new_data)
                    token_store.save_token("google", stored)
                    logger.debug("Successfully refreshed Google OAuth access token.")
                    return stored.get("access_token")
                else:
                    logger.warning("Failed to refresh Google OAuth token: %s", res.text)
                    return None
        except Exception as e:
            logger.error("Error refreshing Google OAuth token: %s", e)
            return None

    @classmethod
    async def get_valid_token(cls) -> str | None:
        """Get a valid access token, auto-refreshing if expired."""
        if not token_store.is_authenticated("google"):
            return None

        if token_store.is_expired("google"):
            return await cls.refresh_access_token()

        return token_store.get_access_token("google")
