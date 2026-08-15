"""Credential resolution for GA4 + Search Console, first match wins:

1. GA4_SA_JSON               — service-account JSON as an env-var string (CI/Actions secret)
2. GOOGLE_APPLICATION_CREDENTIALS — path to a service-account JSON file
3. GA4_CLIENT_ID / GA4_CLIENT_SECRET / GA4_REFRESH_TOKEN — OAuth refresh-token env triple
4. ~/.growth-reporter/token.json — OAuth token file written by `growth-reporter init`

For Search Console with a service account: add the service-account email as a
(restricted) user on the GSC property, same idea as GA4 Viewer access.
"""
import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]
TOKEN_PATH = Path.home() / ".growth-reporter" / "token.json"


def credential_source() -> str:
    if os.environ.get("GA4_SA_JSON"):
        return "service account (GA4_SA_JSON env)"
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return f"service account file ({os.environ['GOOGLE_APPLICATION_CREDENTIALS']})"
    if all(os.environ.get(k) for k in ("GA4_CLIENT_ID", "GA4_CLIENT_SECRET", "GA4_REFRESH_TOKEN")):
        return "OAuth refresh token (env vars)"
    if TOKEN_PATH.exists():
        return f"OAuth token file ({TOKEN_PATH})"
    return "none"


def get_credentials():
    sa_json = os.environ.get("GA4_SA_JSON")
    if sa_json:
        return service_account.Credentials.from_service_account_info(
            json.loads(sa_json), scopes=SCOPES)

    sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if sa_path and Path(sa_path).exists():
        return service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)

    cid = os.environ.get("GA4_CLIENT_ID")
    csec = os.environ.get("GA4_CLIENT_SECRET")
    rtok = os.environ.get("GA4_REFRESH_TOKEN")
    if cid and csec and rtok:
        creds = Credentials(
            token=None, refresh_token=rtok,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=cid, client_secret=csec, scopes=SCOPES,
        )
        creds.refresh(Request())
        return creds

    if TOKEN_PATH.exists():
        data = json.loads(TOKEN_PATH.read_text())
        creds = Credentials(
            token=None, refresh_token=data["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=data["client_id"], client_secret=data["client_secret"],
            scopes=SCOPES,
        )
        creds.refresh(Request())
        return creds

    raise RuntimeError(
        "No credentials found. Run `growth-reporter init` to sign in with Google. "
        "For servers/CI, use a service account: set GOOGLE_APPLICATION_CREDENTIALS "
        "or GA4_SA_JSON (and add the service-account email to both GA4 and Search Console)."
    )


def oauth_login(client_secrets_path: str | None = None):
    """Browser sign-in. Saves a refresh token to ~/.growth-reporter/token.json."""
    import json as _json
    from google_auth_oauthlib.flow import InstalledAppFlow
    from .oauth_client import EMBEDDED_CLIENT_ID, EMBEDDED_CLIENT_SECRET

    path = client_secrets_path or os.environ.get("GA4_OAUTH_CLIENT_JSON")
    if path and Path(path).expanduser().exists():
        flow = InstalledAppFlow.from_client_secrets_file(
            str(Path(path).expanduser()), scopes=SCOPES)
    elif EMBEDDED_CLIENT_ID and EMBEDDED_CLIENT_SECRET:
        flow = InstalledAppFlow.from_client_config({
            "installed": {
                "client_id": EMBEDDED_CLIENT_ID,
                "client_secret": EMBEDDED_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }, scopes=SCOPES)
    else:
        raise RuntimeError(
            "No OAuth client available. Point GA4_OAUTH_CLIENT_JSON at a "
            "client_secrets.json (Desktop-app OAuth client, with the Analytics Data, "
            "Analytics Admin, and Search Console APIs enabled), or embed one in "
            "reporter/oauth_client.py."
        )

    creds = flow.run_local_server(port=0, prompt="consent",
                                  authorization_prompt_message="")
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(_json.dumps({
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }))
    TOKEN_PATH.chmod(0o600)
    return creds
