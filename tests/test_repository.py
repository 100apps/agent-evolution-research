from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RepositoryContractTest(unittest.TestCase):
    def test_pdf_manifest_and_hashes(self):
        manifest = load("metadata/pdf_manifest.json")
        self.assertEqual(manifest["status_counts"], {"ok": 39})
        self.assertEqual(len(manifest["records"]), 39)
        for record in manifest["records"]:
            path = ROOT / record["path"]
            self.assertTrue(path.is_file(), record["path"])
            self.assertEqual(sha256(path), record["sha256"], record["path"])

    def test_registry_identity_and_links(self):
        registry = load("metadata/paper_registry.json")
        self.assertEqual(registry["count"], 39)
        ids = [paper["paper_id"] for paper in registry["papers"]]
        self.assertEqual(len(ids), len(set(ids)))
        for paper in registry["papers"]:
            self.assertTrue((ROOT / paper["local_pdf"]).is_file())
            self.assertTrue((ROOT / paper["local_text"]).is_file())
            self.assertTrue((ROOT / paper["analysis_file"]).is_file())

    def test_topic_map_coverage(self):
        topic_map = load("metadata/agent_evolution_map.json")
        papers = [paper for group in topic_map["groups"] for paper in group["papers"]]
        keys = [str(paper["inventory_index"]) for paper in papers]
        self.assertEqual(topic_map["count"], 39)
        self.assertEqual(len(keys), 39)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("S01", keys)

    def test_experiment_evidence_counts(self):
        manifests = [
            load(f"experiments/{name}/experiment_manifest.json")
            for name in ("acrouter_replay", "evoc2f_scheduler", "validation_bias")
        ]
        levels = [item["evidence_level"] for item in manifests]
        self.assertEqual(levels.count("公开工件回放"), 1)
        self.assertEqual(levels.count("合成机制实验"), 2)
        for item in manifests:
            self.assertIn("expected", item)
            self.assertIn("actual", item)
            self.assertIn("tolerance", item)
            self.assertIn("command", item)


if __name__ == "__main__":
    unittest.main()
