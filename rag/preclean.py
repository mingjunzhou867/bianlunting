from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from rag.chunk_schema import RagChunk


ARTICLE_HEADING_RE = re.compile(r"^第[一二三四五六七八九十百千0-9]+条(?:\s+.*)?$")
SECTION_HEADING_RE = re.compile(r"^[一二三四五六七八九十]+、.+$")
SUBSECTION_HEADING_RE = re.compile(r"^（[一二三四五六七八九十0-9]+）.+$")
PAGE_NOISE_RE = re.compile(
    r"^(第\s*\d+\s*页\s*/\s*共\s*\d+\s*页|\d+\s*/\s*\d+|—?\s*\d+\s*—?)$"
)
SOFT_LINE_END_RE = re.compile(r"[，、；：,.]$")
STRUCTURE_START_RE = re.compile(
    r"^(第[一二三四五六七八九十百千0-9]+条|[一二三四五六七八九十]+、|（[一二三四五六七八九十0-9]+）)"
)
ARTICLE_INLINE_RE = re.compile(r"第[一二三四五六七八九十百千0-9]+条")
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([，。；：！？、）】》])")
SPACE_AFTER_OPEN_RE = re.compile(r"([（【《])\s+")
QUOTE_NOISE_RE = re.compile(r"[“”\"'`]+")
WEB_NOISE_PATTERNS = (
    re.compile(r"https?://\S+", re.IGNORECASE),
    re.compile(r"\bwww\.\S+", re.IGNORECASE),
    re.compile(r"\b\d{4}/\d{1,2}/\d{1,2}\s+\d{1,2}:\d{2}\b"),
    re.compile(r"中国政府网"),
    re.compile(r"国务院文件"),
    re.compile(r"当前位置[:：].*$"),
)


@dataclass(slots=True)
class RawPage:
    page_no: int
    text: str


@dataclass(slots=True)
class StructuredBlock:
    belong_id: str
    title: str
    lines: list[str]

    def render(self) -> str:
        return "\n".join(line for line in self.lines if line.strip()).strip()


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    text = SPACE_AFTER_OPEN_RE.sub(r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_page_text(text: str) -> str:
    text = normalize_text(text)
    kept_lines: list[str] = []
    for raw_line in text.splitlines():
        line = strip_line_noise(raw_line)
        if not line or PAGE_NOISE_RE.match(line):
            continue
        kept_lines.extend(split_inline_structure(line))
    return "\n".join(kept_lines)


def merge_pages_without_breaking_structure(pages: list[RawPage]) -> list[str]:
    merged_lines: list[str] = []

    for page in pages:
        page_text = clean_page_text(page.text)
        if not page_text:
            continue

        for line in page_text.splitlines():
            if not merged_lines:
                merged_lines.append(line)
                continue

            previous = merged_lines[-1]
            if _should_merge_lines(previous, line):
                merged_lines[-1] = f"{previous}{line}"
            else:
                merged_lines.append(line)

    return merged_lines


def chunk_document(
    doc_id: int,
    title: str,
    pages: list[RawPage],
    max_chars: int = 1800,
) -> list[RagChunk]:
    merged_lines = merge_pages_without_breaking_structure(pages)
    blocks = build_structured_blocks(title=title, merged_lines=merged_lines)
    return blocks_to_chunks(doc_id=doc_id, blocks=blocks, max_chars=max_chars)


def build_structured_blocks(title: str, merged_lines: list[str]) -> list[StructuredBlock]:
    blocks: list[StructuredBlock] = []
    current = StructuredBlock(belong_id="000", title=title, lines=[])

    for line in merged_lines:
        line = line.strip()
        if not line:
            continue

        if ARTICLE_HEADING_RE.match(line):
            if current.lines:
                blocks.append(current)
            current = StructuredBlock(
                belong_id=extract_belong_id(line),
                title=title,
                lines=[line],
            )
            continue

        if SECTION_HEADING_RE.match(line) or SUBSECTION_HEADING_RE.match(line):
            if current.lines:
                current.lines.append(line)
            else:
                current = StructuredBlock(
                    belong_id=extract_belong_id(line),
                    title=title,
                    lines=[line],
                )
            continue

        current.lines.append(line)

    if current.lines:
        blocks.append(current)

    return blocks


def blocks_to_chunks(doc_id: int, blocks: list[StructuredBlock], max_chars: int = 1800) -> list[RagChunk]:
    chunks: list[RagChunk] = []
    chunk_seq = 1

    for block in blocks:
        for piece in normalize_block_pieces(block.render(), max_chars=max_chars):
            chunks.append(
                RagChunk(
                    chunk_id=chunk_seq,
                    doc_id=doc_id,
                    title=block.title,
                    belong_id=infer_piece_belong_id(piece, default=block.belong_id),
                    context=piece,
                )
            )
            chunk_seq += 1

    return chunks


def normalize_block_pieces(text: str, max_chars: int) -> list[str]:
    text = normalize_text(text)
    if not text:
        return []

    article_pieces = split_inline_article_blob(text)
    normalized: list[str] = []
    for piece in article_pieces:
        piece = normalize_text(piece)
        if not piece:
            continue
        if len(piece) <= max_chars:
            normalized.append(piece)
        else:
            normalized.extend(split_long_block_preserving_lines(piece, max_chars=max_chars))
    return normalized


def split_long_block_preserving_lines(text: str, max_chars: int = 1800) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    pieces: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in lines:
        separator_len = 1 if current else 0
        projected = current_len + separator_len + len(line)
        if projected <= max_chars:
            current.append(line)
            current_len = projected
            continue

        if current:
            pieces.append("\n".join(current))
            current = []
            current_len = 0

        if len(line) <= max_chars:
            current.append(line)
            current_len = len(line)
            continue

        wrapped = split_single_line(line, max_chars=max_chars)
        pieces.extend(wrapped[:-1])
        current = [wrapped[-1]]
        current_len = len(wrapped[-1])

    if current:
        pieces.append("\n".join(current))

    return pieces


def split_single_line(text: str, max_chars: int = 1800) -> list[str]:
    parts: list[str] = []
    remaining = text
    while len(remaining) > max_chars:
        cut_at = find_preferred_cut(remaining, max_chars)
        parts.append(remaining[:cut_at].strip())
        remaining = remaining[cut_at:].strip()
    if remaining:
        parts.append(remaining)
    return parts


def find_preferred_cut(text: str, max_chars: int) -> int:
    window = text[:max_chars]
    for marker in ("。", "；", "：", "，", " "):
        idx = window.rfind(marker)
        if idx >= max_chars // 2:
            return idx + 1
    return max_chars


def extract_belong_id(line: str) -> str:
    article_match = re.match(r"^(第[一二三四五六七八九十百千0-9]+条)", line)
    if article_match:
        return article_match.group(1)

    section_match = re.match(r"^([一二三四五六七八九十]+、)", line)
    if section_match:
        return section_match.group(1)

    subsection_match = re.match(r"^(（[一二三四五六七八九十0-9]+）)", line)
    if subsection_match:
        return subsection_match.group(1)

    return "000"


def strip_line_noise(line: str) -> str:
    cleaned = line.strip()
    for pattern in WEB_NOISE_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = QUOTE_NOISE_RE.sub("", cleaned)
    cleaned = normalize_text(cleaned)
    return cleaned.strip(" -_[]|")


def split_inline_structure(line: str) -> list[str]:
    line = normalize_text(line)
    if not line:
        return []

    matches = list(ARTICLE_INLINE_RE.finditer(line))
    if not matches:
        return [line]

    pieces: list[str] = []
    first_start = matches[0].start()
    if first_start > 0:
        prefix = line[:first_start].strip()
        if prefix:
            pieces.append(prefix)

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(line)
        piece = line[start:end].strip()
        if piece:
            pieces.append(piece)
    return pieces


def split_inline_article_blob(text: str) -> list[str]:
    matches = list(ARTICLE_INLINE_RE.finditer(text))
    if len(matches) <= 1:
        return [text]

    pieces: list[str] = []
    first_start = matches[0].start()
    if first_start > 0:
        prefix = text[:first_start].strip()
        if prefix:
            pieces.append(prefix)

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
    return pieces


def infer_piece_belong_id(piece: str, default: str) -> str:
    inferred = extract_belong_id(piece)
    return inferred if inferred != "000" else default


def _should_merge_lines(previous: str, current: str) -> bool:
    if not previous.strip() or not current.strip():
        return False
    if STRUCTURE_START_RE.match(current):
        return False
    if ARTICLE_HEADING_RE.match(previous) or SECTION_HEADING_RE.match(previous) or SUBSECTION_HEADING_RE.match(previous):
        return False
    if SOFT_LINE_END_RE.search(previous):
        return True
    if len(previous) < 18:
        return False
    return True
