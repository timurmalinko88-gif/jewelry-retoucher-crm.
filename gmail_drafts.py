"""Gmail API integration for Retoucher CRM.

Creates email drafts only (strictly NO automated sending).
Supports variables: {brand}, {name}, {portfolio_url}, {my_name}.
"""

import base64
from email.message import EmailMessage
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Optional Google API libraries with graceful fallback
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
CRM_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = CRM_DIR / "credentials.json"
TOKEN_FILE = CRM_DIR / "token.json"

# Built-in tested outreach templates for jewelry retouching
OUTREACH_TEMPLATES: Dict[str, Dict[str, str]] = {
    "cold_initial": {
        "title": "Холодное первое касание (Cold Initial)",
        "subject": "Quick jewelry retouching sample for {brand}",
        "body": (
            "Hi {name},\n\n"
            "I came across {brand}'s jewelry collection and was really impressed by the craftsmanship.\n\n"
            "I'm a jewelry retoucher specializing in high-end e-commerce and editorial post-production "
            "(metal polishing, reflections preservation, gemstone clarity, and diamond brilliance).\n\n"
            "Here is a short before/after portfolio of recent ring and necklace work: {portfolio_url}\n\n"
            "Would you be open to a complimentary test retouch on 1-2 raw files from your upcoming batch, "
            "so you can evaluate the quality with zero commitment?\n\n"
            "Best regards,\n"
            "{my_name}"
        ),
    },
    "followup_1": {
        "title": "Фоллоу-ап #1 (Follow-up Value)",
        "subject": "Re: Quick jewelry retouching sample for {brand}",
        "body": (
            "Hi {name},\n\n"
            "Following up on my previous note regarding {brand}'s imagery.\n\n"
            "I know new collection launches keep schedules packed. If you have upcoming product photos "
            "or CAD renders needing photorealism, my test offer still stands.\n\n"
            "Portfolio link: {portfolio_url}\n\n"
            "Best regards,\n"
            "{my_name}"
        ),
    },
    "case_study": {
        "title": "Фоллоу-ап #2 (Кейс / Сравнение)",
        "subject": "Metal reflection & gemstone clarity example for {brand}",
        "body": (
            "Hi {name},\n\n"
            "Sharing a quick side-by-side example of metal smoothing on fine gold & platinum pieces: {portfolio_url}\n\n"
            "We typically deliver 24-48h turnarounds for e-commerce catalogs with consistent color matching.\n\n"
            "Would it be helpful to discuss pricing packages for {brand}'s next catalog?\n\n"
            "Best regards,\n"
            "{my_name}"
        ),
    },
    "breakup": {
        "title": "Финальное касание (Breakup Email)",
        "subject": "Closing the loop / {brand}",
        "body": (
            "Hi {name},\n\n"
            "I assume post-production retouching isn't a priority for {brand} right now, so I won't follow up further.\n\n"
            "If you ever need high-end retouching support or rush capacity during peak seasons, feel free to reach out anytime.\n\n"
            "Wishing {brand} continued success!\n\n"
            "Best regards,\n"
            "{my_name}"
        ),
    },
}


def render_template(template_str: str, context: Dict[str, str]) -> str:
    """Safely replace variables like {brand}, {name} without crashing on missing keys."""
    res = template_str
    for key, val in context.items():
        res = res.replace(f"{{{key}}}", str(val or ""))
    return res


def is_gmail_configured() -> bool:
    """Check if Gmail credentials or existing token are available."""
    if not GMAIL_API_AVAILABLE:
        return False
    return TOKEN_FILE.exists() or CREDENTIALS_FILE.exists()


def get_gmail_service() -> Optional[Any]:
    """Authenticate and return Gmail API service instance."""
    if not GMAIL_API_AVAILABLE:
        return None

    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        else:
            if not CREDENTIALS_FILE.exists():
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception:
                return None

        if creds:
            with open(TOKEN_FILE, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

    if creds and creds.valid:
        return build("gmail", "v1", credentials=creds)
    return None


def create_gmail_draft(
    to_email: str,
    subject: str,
    body_text: str,
) -> Dict[str, Any]:
    """Create a draft in Gmail. Strictly does NOT send the email.

    Returns:
        dict with success status, draft_id, or error message.
    """
    if not GMAIL_API_AVAILABLE:
        return {
            "success": False,
            "error": "Библиотека google-api-python-client не установлена. Запустите: pip install google-api-python-client google-auth-oauthlib",
        }

    if not is_gmail_configured():
        return {
            "success": False,
            "error": "Файл credentials.json не найден в папке /crm. Поместите client_secrets в crm/credentials.json.",
        }

    try:
        service = get_gmail_service()
        if not service:
            return {"success": False, "error": "Не удалось авторизовать Gmail API."}

        msg = EmailMessage()
        msg.set_content(body_text)
        msg["To"] = to_email.strip()
        msg["Subject"] = subject.strip()

        encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        create_message = {"message": {"raw": encoded_message}}

        draft = service.users().drafts().create(userId="me", body=create_message).execute()
        return {
            "success": True,
            "draft_id": draft.get("id"),
            "message": "Черновик успешно создан в вашем Gmail!",
        }
    except Exception as e:
        return {"success": False, "error": f"Ошибка создания черновика: {str(e)}"}
