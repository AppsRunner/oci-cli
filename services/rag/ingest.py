"""
LexBangla document ingestion pipeline.

Usage:
    python ingest.py --input /path/to/docs --collection lexbangla
    python ingest.py --input doc.txt --collection lexbangla --recreate
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

load_dotenv()

sys.path.insert(0, str(Path(__file__).parents[2] / "packages" / "rag"))

from lexbangla_rag import LegalDocumentChunker, Embedder, VectorStore  # noqa: E402

console = Console()
logging.basicConfig(level=logging.WARNING)


@click.command()
@click.option(
    "--input", "-i", "input_path",
    required=True,
    help="File or directory of .txt / .md legal documents to ingest.",
)
@click.option(
    "--collection", "-c",
    default="lexbangla",
    show_default=True,
    help="Qdrant collection name.",
)
@click.option(
    "--chunk-size", default=1500, show_default=True,
    help="Max characters per chunk.",
)
@click.option(
    "--chunk-overlap", default=200, show_default=True,
    help="Overlap in characters between consecutive chunks.",
)
@click.option(
    "--model", default="paraphrase-multilingual-mpnet-base-v2", show_default=True,
    help="Sentence-transformer model name.",
)
@click.option(
    "--batch-size", default=64, show_default=True,
    help="Embedding batch size.",
)
@click.option(
    "--recreate", is_flag=True, default=False,
    help="Drop and recreate the Qdrant collection before ingesting.",
)
@click.option(
    "--dry-run", is_flag=True, default=False,
    help="Chunk and embed without writing to Qdrant.",
)
def main(
    input_path: str,
    collection: str,
    chunk_size: int,
    chunk_overlap: int,
    model: str,
    batch_size: int,
    recreate: bool,
    dry_run: bool,
) -> None:
    """Ingest legal documents into the LexBangla vector store."""
    path = Path(input_path)
    files = _resolve_files(path)
    if not files:
        console.print(f"[red]No .txt or .md files found at {path}[/red]")
        raise SystemExit(1)

    console.print(f"[bold green]LexBangla Ingestion Pipeline[/bold green]")
    console.print(f"  Files:      {len(files)}")
    console.print(f"  Collection: {collection}")
    console.print(f"  Model:      {model}")
    console.print(f"  Dry run:    {dry_run}\n")

    chunker = LegalDocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        embed_task = progress.add_task("Loading embedder …", total=None)
        embedder = Embedder(model_name=model)
        _ = embedder.dimension  # trigger lazy load
        progress.update(embed_task, description="Embedder ready", total=1, completed=1)

        if not dry_run:
            store = VectorStore(collection=collection, dimension=embedder.dimension)
            store.ensure_collection(recreate=recreate)

        total_chunks = 0
        ingest_task = progress.add_task("Ingesting …", total=len(files))

        for file in files:
            text = file.read_text(encoding="utf-8", errors="replace")
            source = str(file)
            chunks = chunker.chunk(text, source=source)

            if not chunks:
                progress.advance(ingest_task)
                continue

            texts = [c.text for c in chunks]
            vectors = embedder.embed(texts, batch_size=batch_size)

            if not dry_run:
                if recreate:
                    store.delete_by_source(source)
                store.upsert(chunks, vectors)

            total_chunks += len(chunks)
            progress.advance(ingest_task)

    console.print(f"\n[bold]Done.[/bold] {total_chunks} chunks from {len(files)} files.")
    if dry_run:
        console.print("[yellow]Dry run — nothing written to Qdrant.[/yellow]")
    else:
        info = store.collection_info()
        console.print(
            f"Collection '{collection}': "
            f"{info['vectors_count']} vectors, status={info['status']}"
        )


def _resolve_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(path.rglob("*.txt")) + sorted(path.rglob("*.md"))


if __name__ == "__main__":
    main()
