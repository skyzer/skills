"""Swappable providers for sending mail and verifying addresses.

Nothing else in the codebase names a vendor. Change `providers.email.type` or
`providers.verifier.type` in settings.yaml and everything downstream is unchanged.

Adding a provider means implementing one small class here and adding it to the
registry at the bottom. That's the whole extension point.

Mailers implement:
    send(to, subject, body, from_addr, from_name) -> (message_id, error)
    draft_reply(...)                              -> (draft_id, error) or NotSupported
    supports_drafts                               -> bool

Verifiers implement:
    verify(email) -> a raw verdict string, which channels.py maps to a tier
"""
import base64
import os
import sys
import urllib.parse
import urllib.request
from email.mime.text import MIMEText


class NotSupported(Exception):
    """Raised when a provider can't do something. Callers must degrade, not fail
    silently: a reply that quietly doesn't get drafted is worse than an error."""


# ---------------------------------------------------------------------------
# Mailers
# ---------------------------------------------------------------------------

class GmailServiceAccount:
    """Google Workspace with domain-wide delegation.

    Sending and drafting use separate credentials on purpose. The draft path
    requests gmail.compose, which cannot send. That's the reply guard: not a
    rule asking the agent to behave, an absence of the permission.
    """
    supports_drafts = True

    SEND_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
    DRAFT_SCOPES = ["https://www.googleapis.com/auth/gmail.compose",
                    "https://www.googleapis.com/auth/gmail.readonly"]
    READ_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
                   "https://www.googleapis.com/auth/gmail.modify"]

    def __init__(self, cfg):
        self.cfg = cfg
        self.sa_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
        self.subject = os.environ.get("SEND_AS")
        if not self.sa_file or not self.subject:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_FILE and SEND_AS must be set in .env")

    def _service(self, scopes):
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds = service_account.Credentials.from_service_account_file(
            self.sa_file, scopes=scopes).with_subject(self.subject)
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def send(self, to, subject, body, from_addr, from_name=""):
        msg = MIMEText(body)
        msg["To"] = to
        msg["From"] = f"{from_name} <{from_addr}>".strip()
        msg["Subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        try:
            sent = self._service(self.SEND_SCOPES).users().messages().send(
                userId="me", body={"raw": raw}).execute()
            return sent.get("id"), None
        except Exception as exc:  # noqa: BLE001 - the reason belongs in the log
            return None, str(exc)

    def read_service(self):
        return self._service(self.READ_SCOPES)

    def draft_reply(self, original_message_id, body):
        svc = self._service(self.DRAFT_SCOPES)
        original = svc.users().messages().get(
            userId="me", id=original_message_id, format="full").execute()

        def header(name):
            for h in original.get("payload", {}).get("headers", []):
                if h["name"].lower() == name.lower():
                    return h["value"]
            return ""

        subject = header("Subject")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        msg = MIMEText(body)
        msg["To"] = header("From")
        msg["Subject"] = subject
        original_id = header("Message-ID")
        msg["In-Reply-To"] = original_id
        msg["References"] = f"{header('References')} {original_id}".strip()

        draft = svc.users().drafts().create(userId="me", body={"message": {
            "raw": base64.urlsafe_b64encode(msg.as_bytes()).decode(),
            "threadId": original.get("threadId"),
        }}).execute()
        return draft["id"], header("From"), subject

    def list_drafts(self, limit=50):
        svc = self._service(self.DRAFT_SCOPES)
        return svc.users().drafts().list(userId="me", maxResults=limit).execute().get("drafts", [])


class SMTP:
    """Any SMTP server. Sends fine, cannot create drafts.

    With SMTP the agent writes reply drafts to state/reply_drafts/ instead. That
    is weaker than a draft sitting in your mailbox, but the important property
    holds: there is no code path that sends a reply.
    """
    supports_drafts = False

    def __init__(self, cfg):
        self.host = os.environ.get("SMTP_HOST")
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.user = os.environ.get("SMTP_USER")
        self.password = os.environ.get("SMTP_PASSWORD")
        if not (self.host and self.user and self.password):
            raise RuntimeError("SMTP_HOST, SMTP_USER and SMTP_PASSWORD must be set in .env")

    def send(self, to, subject, body, from_addr, from_name=""):
        import smtplib
        msg = MIMEText(body)
        msg["To"] = to
        msg["From"] = f"{from_name} <{from_addr}>".strip()
        msg["Subject"] = subject
        try:
            with smtplib.SMTP(self.host, self.port, timeout=30) as s:
                s.starttls()
                s.login(self.user, self.password)
                s.send_message(msg)
            return f"smtp:{to}", None
        except Exception as exc:  # noqa: BLE001
            return None, str(exc)

    def read_service(self):
        raise NotSupported(
            "SMTP can't read a mailbox. Use IMAP or a Gmail provider for inbox checks.")

    def draft_reply(self, original_message_id, body):
        raise NotSupported(
            "SMTP has no drafts. Write the reply to state/reply_drafts/ instead.")


# ---------------------------------------------------------------------------
# Verifiers
# ---------------------------------------------------------------------------

def _get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "outbound-master/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode().strip()


class EmailListVerify:
    def __init__(self, cfg):
        self.key = os.environ.get("EMAIL_VERIFIER_KEY", "")

    def verify(self, email):
        url = ("https://apps.emaillistverify.com/api/verifyEmail?"
               + urllib.parse.urlencode({"secret": self.key, "email": email}))
        return _get(url).lower()


class MillionVerifier:
    def __init__(self, cfg):
        self.key = os.environ.get("EMAIL_VERIFIER_KEY", "")

    def verify(self, email):
        import json
        url = ("https://api.millionverifier.com/api/v3/?"
               + urllib.parse.urlencode({"api": self.key, "email": email, "timeout": 20}))
        return (json.loads(_get(url)).get("result") or "unknown").lower()


class MXOnly:
    """Confirms the domain can receive mail at all. Much weaker than
    verification and should never be the steady state, because a domain that
    resolves tells you nothing about whether the mailbox exists."""

    def __init__(self, cfg):
        pass

    def verify(self, email):
        import socket
        try:
            socket.getaddrinfo(email.split("@")[-1], None)
            return "unknown"
        except Exception:  # noqa: BLE001
            return "invalid_mx"


class NoVerifier:
    def __init__(self, cfg):
        pass

    def verify(self, email):
        return "unknown"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

MAILERS = {"gmail_service_account": GmailServiceAccount, "smtp": SMTP}
VERIFIERS = {"emaillistverify": EmailListVerify, "millionverifier": MillionVerifier,
             "mx_only": MXOnly, "none": NoVerifier}


def get_mailer(config):
    spec = (config.get("providers") or {}).get("email") or {}
    kind = spec.get("type", "gmail_service_account")
    if kind not in MAILERS:
        sys.exit(f"Unknown email provider {kind!r}. Available: {', '.join(MAILERS)}")
    return MAILERS[kind](spec)


def get_verifier(config):
    spec = (config.get("providers") or {}).get("verifier") or {}
    kind = spec.get("type", "none")
    if kind not in VERIFIERS:
        sys.exit(f"Unknown verifier {kind!r}. Available: {', '.join(VERIFIERS)}")
    if kind in ("emaillistverify", "millionverifier") and not os.environ.get("EMAIL_VERIFIER_KEY"):
        print(f"WARNING: verifier is {kind} but EMAIL_VERIFIER_KEY is empty. "
              f"Falling back to an MX check, which is much weaker.", file=sys.stderr)
        return MXOnly(spec)
    return VERIFIERS[kind](spec)
