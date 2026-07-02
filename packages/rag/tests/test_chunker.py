"""Unit tests for LegalDocumentChunker — no external dependencies."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from lexbangla_rag.chunker import LegalDocumentChunker


SAMPLE_BANGLA_LAW = """
ধারা ১ — সংজ্ঞা

এই আইনে, প্রসঙ্গ অন্যরূপ না হলে —

(ক) "আদালত" অর্থ সংশ্লিষ্ট এখতিয়ারসম্পন্ন দেওয়ানি আদালত।

(খ) "সম্পত্তি" অর্থ যেকোনো স্থাবর বা অস্থাবর সম্পদ।

ধারা ২ — প্রয়োগ

এই আইনের বিধানাবলি বাংলাদেশের সমগ্র ভূখণ্ডে প্রযোজ্য হইবে।
তবে শর্ত থাকে যে, বিশেষ বিধান প্রযোজ্য ক্ষেত্রে সেই বিধানই প্রাধান্য পাইবে।

ধারা ৩ — ব্যাখ্যা

এই আইনের কোনো বিধান সম্পর্কে সন্দেহ দেখা দিলে সরকার গেজেট বিজ্ঞপ্তির মাধ্যমে
সেই বিধানের ব্যাখ্যা প্রদান করিতে পারিবে।
""".strip()


def test_chunk_returns_list():
    chunker = LegalDocumentChunker()
    chunks = chunker.chunk(SAMPLE_BANGLA_LAW, source="test.txt")
    assert isinstance(chunks, list)
    assert len(chunks) >= 1


def test_chunk_source_preserved():
    chunker = LegalDocumentChunker()
    chunks = chunker.chunk(SAMPLE_BANGLA_LAW, source="test_doc.txt")
    assert all(c.source == "test_doc.txt" for c in chunks)


def test_chunk_indices_sequential():
    chunker = LegalDocumentChunker()
    chunks = chunker.chunk(SAMPLE_BANGLA_LAW, source="test.txt")
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))


def test_section_titles_extracted():
    chunker = LegalDocumentChunker()
    chunks = chunker.chunk(SAMPLE_BANGLA_LAW, source="test.txt")
    titled = [c for c in chunks if c.section_title]
    assert len(titled) >= 1, "Expected at least one chunk with a section title"


def test_empty_text():
    chunker = LegalDocumentChunker()
    assert chunker.chunk("", source="empty.txt") == []


def test_small_text_single_chunk():
    chunker = LegalDocumentChunker(chunk_size=5000)
    text = "এটি একটি ছোট পরীক্ষার বাক্য।"
    chunks = chunker.chunk(text, source="small.txt")
    assert len(chunks) == 1
    assert text in chunks[0].text


def test_large_text_splits():
    chunker = LegalDocumentChunker(chunk_size=100, chunk_overlap=20)
    text = ("এটি একটি পরীক্ষার বাক্য। " * 50).strip()
    chunks = chunker.chunk(text, source="large.txt")
    assert len(chunks) > 1


def test_mixed_script_section_markers():
    text = "Section 1\nSome content here.\n\nSection 2\nMore content."
    chunker = LegalDocumentChunker()
    chunks = chunker.chunk(text, source="mixed.txt")
    assert any("Section" in c.section_title for c in chunks)
