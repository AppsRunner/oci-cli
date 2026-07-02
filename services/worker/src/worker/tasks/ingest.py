import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Source adapters are keyed by source_id; each returns a list of document dicts.
# In production these would call real crawlers / APIs.
_ADAPTERS: Dict[str, Any] = {}


def register_adapter(source_id: str):
    def decorator(fn):
        _ADAPTERS[source_id] = fn
        return fn
    return decorator


@register_adapter("gazette")
def _fetch_gazette(date: str, **_) -> list:
    logger.debug("Fetching Bangladesh Gazette for %s", date)
    time.sleep(0.01)  # simulate I/O
    return [{"doc_id": f"gazette-{date}-001", "source": "gazette", "date": date}]


@register_adapter("supreme_court")
def _fetch_supreme_court(date: str, **_) -> list:
    logger.debug("Fetching Supreme Court judgments for %s", date)
    time.sleep(0.01)
    return [{"doc_id": f"sc-{date}-001", "source": "supreme_court", "date": date}]


@register_adapter("hc_division")
def _fetch_hc_division(date: str, **_) -> list:
    logger.debug("Fetching High Court Division for %s", date)
    time.sleep(0.01)
    return [{"doc_id": f"hcd-{date}-001", "source": "hc_division", "date": date}]


@register_adapter("law_commission")
def _fetch_law_commission(date: str, **_) -> list:
    logger.debug("Fetching Law Commission reports for %s", date)
    time.sleep(0.01)
    return [{"doc_id": f"lc-{date}-001", "source": "law_commission", "date": date}]


@register_adapter("ministry_circulars")
def _fetch_ministry_circulars(date: str, **_) -> list:
    logger.debug("Fetching Ministry Circulars for %s", date)
    time.sleep(0.01)
    return [{"doc_id": f"mc-{date}-001", "source": "ministry_circulars", "date": date}]


def run(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingest documents from a single legal source for a given date.

    Expected payload keys:
        source_id (str): identifier matching a registered adapter
        date      (str): ISO-8601 date string (YYYY-MM-DD)
        category  (str): document category label
    """
    source_id = payload["source_id"]
    date = payload["date"]
    category = payload.get("category", "unknown")

    adapter = _ADAPTERS.get(source_id)
    if adapter is None:
        raise ValueError(f"No adapter registered for source '{source_id}'")

    logger.info("Ingesting source=%s date=%s category=%s", source_id, date, category)

    documents = adapter(date=date)

    indexed = 0
    for doc in documents:
        _index_document(doc)
        indexed += 1

    result = {"source_id": source_id, "date": date, "documents_ingested": indexed}
    logger.info("Ingest complete: %s", result)
    return result


def _index_document(doc: Dict[str, Any]) -> None:
    """Persist document to the search index (stub — replace with real Elasticsearch call)."""
    logger.debug("Indexing document %s", doc.get("doc_id"))
