"""Regression tests: malformed LLM grouping output must degrade, and one
crashing benchmark entry must not kill the whole matrix."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmark"))
sys.path.insert(0, str(ROOT / "src"))

import runner  # noqa: E402
from target_agent.tools.omics import GEOMetadataAuditTool  # noqa: E402


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def json_completion(self, system, user):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def samples():
    return [{"sample_id": "GSM1", "title": "UC patient 1", "source": "rectum", "characteristics": "disease: uc"},
            {"sample_id": "GSM2", "title": "control 1", "source": "rectum", "characteristics": "disease: healthy"}]


def test_llm_groups_handles_nested_confidence_dict():
    tool = GEOMetadataAuditTool(llm=FakeLLM({
        "groups": {"GSM1": "case", "GSM2": "control"},
        "confidence": {"score": 0.9, "rationale": "clear labels"},  # the crash shape from the live matrix
    }))
    result = tool._llm_groups(samples(), "ulcerative colitis")
    assert result is not None
    groups, confidence = result
    assert groups == {"GSM1": "case", "GSM2": "control"}
    assert confidence == 0.9


def test_llm_groups_rejects_malformed_payloads_without_crashing():
    bad_payloads = [
        ["not", "a", "dict"],                                     # non-dict payload
        {"groups": ["GSM1"], "confidence": 0.9},                  # groups not a dict
        {"groups": {"GSM1": "case"}, "confidence": {"x": "y"}},   # confidence dict without numbers
        {"groups": {"GSM1": "case"}, "confidence": "high"},       # non-numeric confidence
    ]
    for payload in bad_payloads:
        tool = GEOMetadataAuditTool(llm=FakeLLM(payload))
        assert tool._llm_groups(samples(), "ulcerative colitis") is None, payload


def test_runner_isolates_a_crashing_entry(tmp_path):
    good = {"id": "BM-T1", "title": "unit gate", "category": "contract", "mode": "unit",
            "assertions": [{"type": "unit", "check": "contract_version_gate"}]}
    bad = {"id": "BM-T2", "title": "crashes", "category": "contract", "mode": "fake",
           "runtime": "langgraph", "registry": "fake",
           "task": {"task_type": "disease_to_target"},  # invalid: missing question/context
           "assertions": []}
    goldset = tmp_path / "g.jsonl"
    goldset.write_text(json.dumps(good) + "\n" + json.dumps(bad) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    rc = runner.main_for_test(goldset, out) if hasattr(runner, "main_for_test") else None
    if rc is None:  # call main() through argv
        sys.argv = ["runner.py", "--goldset", str(goldset), "--out", str(out)]
        rc = runner.main()
    report = json.loads((out / "benchmark_report.json").read_text(encoding="utf-8"))
    assert rc == 1  # matrix score < 1.0 because one entry failed
    by_id = {t["id"]: t for t in report["tasks"]}
    assert by_id["BM-T1"]["passed"] is True
    assert by_id["BM-T2"]["passed"] is False
    assert "task crashed" in by_id["BM-T2"]["results"][0]["failure"]
    assert report["summary"]["assertions"] == 2
    assert report["summary"]["assertions_passed"] == 1
