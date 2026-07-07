import pytest
from mail_client import extract_code


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
