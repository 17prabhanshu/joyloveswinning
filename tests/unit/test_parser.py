import pytest
from firmware_agent.analyzer.parser import FirmwareParser
def test_parser_init():
    parser = FirmwareParser()
    assert parser is not None
