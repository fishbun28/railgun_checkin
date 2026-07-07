from email.message import EmailMessage
from unittest.mock import MagicMock, patch

import pytest

from mail_client import (
    QQMailClient,
    _decode_payload,
    extract_code,
    get_text_from_email,
)


def test_extract_code_6_digits():
    body = "您的验证码是 123456，5分钟内有效。"
    assert extract_code(body) == "123456"


def test_extract_code_4_digits():
    body = "验证码：8888"
    assert extract_code(body) == "8888"


def test_extract_code_not_found():
    body = "这是一封没有验证码的邮件。"
    assert extract_code(body) is None


def test_extract_code_prefers_longer():
    body = "code 1234 and 123456"
    assert extract_code(body) == "123456"


def test_extract_code_chinese_adjacent():
    body = "验证码123456有效"
    assert extract_code(body) == "123456"

    body = "您的验证码4567已发送"
    assert extract_code(body) == "4567"


def test_decode_payload_utf_8():
    msg = EmailMessage()
    msg.set_content("验证码 123456", charset="utf-8")
    assert _decode_payload(msg) == "验证码 123456\n"


def test_decode_payload_gbk():
    msg = EmailMessage()
    msg.set_content("验证码 123456", charset="gbk")
    assert _decode_payload(msg) == "验证码 123456\n"


def test_get_text_from_email_multipart():
    outer = EmailMessage()
    outer.make_mixed()

    text_part = EmailMessage()
    text_part.set_content("验证码 123456", charset="utf-8")
    outer.attach(text_part)

    html_part = EmailMessage()
    html_part.set_content("<p>code 654321</p>", subtype="html", charset="utf-8")
    outer.attach(html_part)

    text = get_text_from_email(outer)
    assert "123456" in text
    assert "654321" in text


def test_find_code_with_mock_predicate():
    client = QQMailClient("test@example.com", "secret")

    msg_with_code = EmailMessage()
    msg_with_code.set_content("您的验证码是 987654", charset="utf-8")

    msg_without_code = EmailMessage()
    msg_without_code.set_content("普通邮件", charset="utf-8")

    with patch.object(
        client,
        "fetch_latest_emails",
        return_value=[msg_without_code, msg_with_code],
    ):
        predicate = lambda m: "验证码" in get_text_from_email(m)
        assert client.find_code(predicate=predicate) == "987654"
