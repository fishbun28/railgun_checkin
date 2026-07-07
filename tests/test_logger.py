import logging
import os
from logger import setup_logger


def test_setup_logger_creates_file(tmp_path):
    log_file = tmp_path / "test.log"
    logger = setup_logger("test", str(log_file))
    logger.info("hello")
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "hello" in content


def test_setup_logger_no_duplicate_handlers(tmp_path):
    log_file = tmp_path / "dup.log"
    logger1 = setup_logger("dup_test", str(log_file))
    logger1.info("first")
    logger2 = setup_logger("dup_test", str(log_file))
    logger2.info("second")
    content = log_file.read_text(encoding="utf-8")
    assert content.count("first") == 1
    assert content.count("second") == 1
