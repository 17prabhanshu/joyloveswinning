import pytest
from firmware_agent.verification.verifier import Verifier
def test_verifier_init():
    verifier = Verifier()
    assert verifier is not None
