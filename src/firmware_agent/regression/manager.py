import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from firmware_agent.generators.models import TestScenario
from firmware_agent.verification.verifier import VerificationResult
from firmware_agent.diagnosis.localizer import DiagnosisResult

logger = logging.getLogger(__name__)


class RegressionManager:
    def __init__(self, corpus_dir: str):
        self.corpus_dir = Path(corpus_dir)
        self.corpus_dir.mkdir(parents=True, exist_ok=True)

    def save_regression(self, test_id: str, test_scenario: TestScenario, verification_result: VerificationResult, diagnosis: Optional[DiagnosisResult] = None) -> None:
        data = {
            "test_scenario": test_scenario.model_dump(),
            "verification_result": verification_result.model_dump(),
            "diagnosis": diagnosis.model_dump() if diagnosis else None
        }
        file_path = self.corpus_dir / f"{test_id}.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Saved regression test {test_id} to {file_path}")

    def load_corpus(self) -> List[TestScenario]:
        corpus = []
        for file_path in self.corpus_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    if "test_scenario" in data:
                        corpus.append(TestScenario.model_validate(data["test_scenario"]))
            except Exception as e:
                logger.error(f"Failed to load regression test from {file_path}: {e}")
        return corpus

    def has_regression(self, test_id: str) -> bool:
        return (self.corpus_dir / f"{test_id}.json").exists()

    def get_regression_count(self) -> int:
        return len(list(self.corpus_dir.glob("*.json")))
