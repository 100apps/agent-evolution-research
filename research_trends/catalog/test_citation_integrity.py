"""Negative controls for exact DOI-to-work citation evidence joins."""
import unittest

from validate_master_csv import verify_citation_observation


class CitationIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.cache = {
            "request-a": {
                "audit": {"raw_sha256": "raw-a", "at_utc": "2026-10-09T00:00:00Z"},
                "requested": {"10.1/paper-a", "10.1/paper-b"},
                "works": {
                    ("10.1/paper-a", "https://openalex.org/W1"): {"cited_by_count": 5},
                    ("10.1/paper-b", "https://openalex.org/W2"): {"cited_by_count": 9},
                },
            }
        }

    def row(self, doi, count):
        return {"doi": doi, "citation_count": str(count),
                "citation_as_of": "2026-10-09T00:00:00Z"}

    def observation(self, doi, work_id, count):
        return {"value": count, "source": {
            "request_fingerprint": "request-a", "matched_identifier": doi,
            "record_id": work_id, "raw_sha256": "raw-a", "provider": "OpenAlex",
            "identifier_match": "exact_doi", "raw_field": "cited_by_count",
            "retrieved_at": "2026-10-09T00:00:00Z"}}

    def test_frozen_pairs_pass_and_swapped_observations_fail(self):
        a = self.row("10.1/paper-a", 5)
        b = self.row("10.1/paper-b", 9)
        observation_a = self.observation("10.1/paper-a", "https://openalex.org/W1", 5)
        observation_b = self.observation("10.1/paper-b", "https://openalex.org/W2", 9)
        self.assertEqual([], verify_citation_observation(a, observation_a, self.cache))
        self.assertEqual([], verify_citation_observation(b, observation_b, self.cache))
        self.assertTrue(verify_citation_observation(a, observation_b, self.cache))
        self.assertTrue(verify_citation_observation(b, observation_a, self.cache))


if __name__ == "__main__":
    unittest.main()
