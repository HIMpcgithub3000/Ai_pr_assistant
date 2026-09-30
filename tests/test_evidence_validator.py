import os
import tempfile

from src.services.evidence_validator import EvidenceValidator


def test_evidence_validator_drops_hallucinations():
    validator = EvidenceValidator()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a real file with 5 lines
        real_file_rel = "service/auth.py"
        real_file_full = os.path.join(tmpdir, real_file_rel)
        os.makedirs(os.path.dirname(real_file_full), exist_ok=True)
        with open(real_file_full, "w") as f:
            f.write("def login(user, password):\n    if not user:\n        raise ValueError()\n    return True\n")

        raw_findings = [
            # 1. Legitimate finding on existing line
            {
                "file_path": real_file_rel,
                "line_number": 2,
                "symbol_name": "if not user",
                "category": "QUALITY",
                "title": "Check user validation",
                "description": "Validation check looks good.",
            },
            # 2. Hallucinated file
            {
                "file_path": "service/phantom_nonexistent.py",
                "line_number": 10,
                "category": "BUG",
                "title": "Fake bug in fake file",
                "description": "Hallucinated file finding.",
            },
            # 3. Real file, but hallucinated out-of-bounds line number
            {
                "file_path": real_file_rel,
                "line_number": 999,
                "category": "BUG",
                "title": "Out of bounds line",
                "description": "Hallucinated line number.",
            },
        ]

        validated = validator.filter_and_validate(tmpdir, raw_findings)

        # Only the legitimate finding should be admitted!
        assert len(validated) == 1
        assert validated[0]["file_path"] == real_file_rel
        assert validated[0]["line_number"] == 2
        assert validated[0]["verified"] is True
        assert validated[0]["confidence"] > 0.9
