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
