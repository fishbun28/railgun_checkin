import imaplib
import re
import time
from collections.abc import Callable
from email.message import Message
from email import message_from_bytes


CODE_PATTERN = re.compile(r"\b\d{4,6}\b")


def extract_code(text: str) -> str | None:
    """Extract the longest 4-6 digit code from *text*, or None if not found."""
    if not text:
        return None
    matches = CODE_PATTERN.findall(text)
    if not matches:
        return None
    return max(matches, key=len)


def _decode_payload(msg: Message) -> str:
    """Decode an email message payload using its declared charset when possible."""
    payload = msg.get_payload(decode=True)
    if isinstance(payload, str):
        return payload
    if payload is None:
        return ""

    charset = msg.get_content_charset()
    encodings = [charset] if charset else []
    encodings.extend(["utf-8", "gbk", "gb2312", "gb18030", "latin-1"])

    for encoding in encodings:
        try:
            return payload.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return payload.decode("latin-1", errors="replace")


def get_text_from_email(msg: Message) -> str:
    """Recursively extract text content from a possibly multipart email."""
    if msg.is_multipart():
        parts = []
        for part in msg.walk() if hasattr(msg, "walk") else []:
            if part is msg:
                continue
            text = get_text_from_email(part)
            if text:
                parts.append(text)
        return "\n".join(parts)

    content_type = msg.get_content_type()
    if content_type and content_type.startswith("text/"):
        return _decode_payload(msg)
    return ""


class QQMailClient:
    """Simple IMAP client for reading verification codes from QQ Mail."""

    def __init__(
        self,
        email: str,
        auth_code: str,
        imap_server: str = "imap.qq.com",
        imap_port: int = 993,
    ):
        self.email = email
        self.auth_code = auth_code
        self.imap_server = imap_server
        self.imap_port = imap_port
        self._imap: imaplib.IMAP4_SSL | None = None

    def fetch_latest_emails(self, limit: int = 10) -> list[Message]:
        """Connect to the IMAP inbox and return the latest *limit* messages."""
        messages: list[Message] = []
        with imaplib.IMAP4_SSL(self.imap_server, self.imap_port) as mail:
            mail.login(self.email, self.auth_code)
            status, _ = mail.select("inbox")
            if status != "OK":
                return messages

            status, data = mail.search(None, "ALL")
            if status != "OK" or not data or not data[0]:
                return messages

            ids = data[0].split()
            latest_ids = ids[-limit:] if limit else ids
            for msg_id in reversed(latest_ids):
                status, fetched = mail.fetch(msg_id, "(RFC822)")
                if status != "OK" or not fetched:
                    continue
                for response in fetched:
                    if isinstance(response, tuple):
                        raw_msg = response[1]
                        if isinstance(raw_msg, bytes):
                            messages.append(message_from_bytes(raw_msg))
        return messages

    def find_code(
        self,
        predicate: Callable[[Message], bool] | None = None,
        max_attempts: int = 12,
        interval: int = 5,
    ) -> str | None:
        """Poll the inbox for a verification code.

        Args:
            predicate: Optional filter called with each email message.
            max_attempts: Maximum number of polling attempts.
            interval: Seconds to wait between attempts.

        Returns:
            The extracted verification code, or None if not found.
        """
        for _ in range(max_attempts):
            for msg in self.fetch_latest_emails(limit=10):
                if predicate is not None and not predicate(msg):
                    continue
                text = get_text_from_email(msg)
                code = extract_code(text)
                if code:
                    return code
            if _ < max_attempts - 1:
                time.sleep(interval)
        return None
