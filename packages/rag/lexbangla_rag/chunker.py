"""
Legal document chunker with awareness of Bangla legal structure.

Splitting priority:
  1. Section/article boundary (ধারা, অনুচ্ছেদ, আর্টিকেল, etc.)
  2. Double newline (paragraph boundary)
  3. Single newline
  4. Sentence-end punctuation (।, ?, !)
  5. Hard char-length split as final fallback
"""
import re
from .models import DocumentChunk

# Common Bangla and mixed-script section markers in legal documents
_SECTION_PATTERNS = re.compile(
    r"(?m)^(?:"
    r"ধারা\s*[\d০-৯]+|"   # ধারা ১, ধারা ১০
    r"অনুচ্ছেদ\s*[\d০-৯]+|"
    r"আর্টিকেল\s*[\d০-৯]+|"
    r"Section\s+\d+|"
    r"Article\s+\d+|"
    r"\(\s*[\d০-৯]+\s*\)|"  # (১) (2)
    r"(?:\d+|[ivxlcdmIVXLCDM]+)\.\s+"  # 1. / iv.
    r")"
)


class LegalDocumentChunker:
    """Chunk legal text into overlapping windows respecting legal boundaries."""

    def __init__(
        self,
        chunk_size: int = 1500,
        chunk_overlap: int = 200,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk(self, text: str, source: str = "") -> list[DocumentChunk]:
        """Return a list of DocumentChunk objects for *text*."""
        text = self._normalise(text)
        sections = self._split_sections(text)
        chunks: list[DocumentChunk] = []
        chunk_idx = 0

        for section_title, body in sections:
            for chunk_text, char_start, char_end in self._window(body):
                chunks.append(
                    DocumentChunk(
                        text=chunk_text,
                        chunk_index=chunk_idx,
                        source=source,
                        section_title=section_title,
                        char_start=char_start,
                        char_end=char_end,
                    )
                )
                chunk_idx += 1

        return chunks

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(text: str) -> str:
        """Collapse excessive whitespace while preserving paragraph breaks."""
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _split_sections(self, text: str) -> list[tuple[str, str]]:
        """Split text on section markers; return (title, body) pairs."""
        boundaries = [m.start() for m in _SECTION_PATTERNS.finditer(text)]
        if not boundaries:
            return [("", text)]

        sections: list[tuple[str, str]] = []

        # Text before the first boundary
        if boundaries[0] > 0:
            sections.append(("", text[: boundaries[0]].strip()))

        for i, start in enumerate(boundaries):
            end = boundaries[i + 1] if i + 1 < len(boundaries) else len(text)
            block = text[start:end]
            # First line is the title
            nl = block.find("\n")
            if nl == -1:
                title, body = block.strip(), ""
            else:
                title = block[:nl].strip()
                body = block[nl:].strip()
            sections.append((title, body))

        return [(t, b) for t, b in sections if t or b]

    def _window(self, text: str) -> list[tuple[str, int, int]]:
        """
        Slide a window of *chunk_size* chars with *chunk_overlap* over *text*.
        Splits prefer the paragraph/sentence separators above hard boundaries.
        """
        separators = ["\n\n", "\n", "।", "?", "!", ". ", " "]
        pieces = self._recursive_split(text, separators)

        windows: list[tuple[str, int, int]] = []
        current: list[str] = []
        current_len = 0
        offset = 0  # approximate char offset in original text

        for piece in pieces:
            p_len = len(piece)
            if current_len + p_len > self.chunk_size and current:
                chunk_text = " ".join(current).strip()
                windows.append((chunk_text, offset, offset + len(chunk_text)))
                # keep overlap
                overlap_buf: list[str] = []
                overlap_len = 0
                for tok in reversed(current):
                    if overlap_len + len(tok) > self.chunk_overlap:
                        break
                    overlap_buf.insert(0, tok)
                    overlap_len += len(tok)
                offset += current_len - overlap_len
                current = overlap_buf
                current_len = overlap_len
            current.append(piece)
            current_len += p_len

        if current:
            chunk_text = " ".join(current).strip()
            windows.append((chunk_text, offset, offset + len(chunk_text)))

        return windows

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split until all pieces are <= chunk_size."""
        if not separators or len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        sep, *rest = separators
        parts = text.split(sep)
        result: list[str] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(part) > self.chunk_size:
                result.extend(self._recursive_split(part, rest))
            else:
                result.append(part)
        return result
