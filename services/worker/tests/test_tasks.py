import pytest

from worker.tasks import ingest, reindex


class TestIngestTask:
    def test_known_source_returns_result(self):
        result = ingest.run({"source_id": "gazette", "date": "2025-01-01", "category": "legislation"})
        assert result["source_id"] == "gazette"
        assert result["date"] == "2025-01-01"
        assert result["documents_ingested"] >= 0

    def test_all_registered_sources_succeed(self):
        for source_id in ingest._ADAPTERS:
            result = ingest.run({"source_id": source_id, "date": "2025-01-01", "category": "test"})
            assert "documents_ingested" in result

    def test_unknown_source_raises(self):
        with pytest.raises(ValueError, match="No adapter registered"):
            ingest.run({"source_id": "nonexistent", "date": "2025-01-01", "category": "x"})

    def test_missing_source_id_raises(self):
        with pytest.raises(KeyError):
            ingest.run({"date": "2025-01-01"})


class TestReindexTask:
    def test_returns_result_with_category(self):
        result = reindex.run({"category": "judgments", "full": True})
        assert result["category"] == "judgments"
        assert result["mode"] == "full"

    def test_incremental_mode(self):
        result = reindex.run({"category": "legislation", "full": False})
        assert result["mode"] == "incremental"

    def test_defaults_to_incremental(self):
        result = reindex.run({"category": "reports"})
        assert result["mode"] == "incremental"
