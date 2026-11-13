"""
Small helpers shared by more than one module
"""
import asyncio
import smtplib
from email.message import EmailMessage
from pathlib import Path
from traceback import format_exc

from app.core.config import settings
from app.core.log_module import system_log

PROMPTS_DIR = Path(__file__).resolve().parent.parent / 'ai_service' / 'prompts'

log = system_log()


def load_prompt(name: str) -> str:
    """
    Read a prompt file from `app/ai_service/prompts/`.
    Args:
        name: File name including extension, e.g. 'orchestrator_system.md'
    Returns:
        Prompt text with surrounding whitespace stripped
    """
    return (PROMPTS_DIR / name).read_text(encoding='utf-8').strip()

def deliver_smtp(msg: EmailMessage) -> dict[str, tuple[int, bytes]]:
    """
    Blocking SMTP exchange (connect, login, send) with a 30 s timeout, call it through `asyncio.to_thread`
    Args:
        msg: Message with From, To and Subject already set

    Returns:
        Refused recipients as `{address: (code, reason)}`, empty when every address was accepted
    """
    # 465 is implicit SSL, anything else (587) connects plain and upgrades with STARTTLS
    if settings.SMTP_PORT == 465:
        server = smtplib.SMTP_SSL(settings.SMTP_HOSTNAME, settings.SMTP_PORT, timeout=30)
    else:
        server = smtplib.SMTP(settings.SMTP_HOSTNAME, settings.SMTP_PORT, timeout=30)
        server.starttls()
    with server:
        server.login(settings.MAIL_FROM, settings.SMTP_PASSWORD)
        refused = server.send_message(msg)
    return refused

async def send_email(send_to: list[str], subject: str, body: str, html: bool = False) -> list[str]:
    """
    Send email from mail address set in .env file, if any of `SMTP_HOSTNAME`, `SMTP_PORT`, `MAIL_FROM` or `SMTP_PASSWORD` env variables are not set, error will raise
    Args:
        send_to: List of email addresses to send to
        subject: Subject of the email
        body: Body of the email
        html: Send `body` as HTML instead of plain text

    Returns:
        List of successfully sent emails address
    """
    msg = EmailMessage()
    msg["From"] = settings.MAIL_FROM
    msg['To'] = ', '.join(send_to)
    msg['Subject'] = subject
    msg.set_content(body, subtype='html' if html else 'plain')
    try:
        # smtplib is sync, a thread keeps the event loop free while it talks to the server
        refused = await asyncio.to_thread(deliver_smtp, msg)
    except Exception:
        log.error(f'[EMAIL] send to {send_to} failed: {format_exc()}')
        raise
    for addr, reason in refused.items():
        log.warning(f'[EMAIL] {addr} refused: {reason}')
    sent = [addr for addr in send_to if addr not in refused]
    log.info(f'[EMAIL] sent "{subject}" to {len(sent)}/{len(send_to)} recipient(s)')
    return sent
