"""Ingest knowledge markdown files into the Qdrant collection.

Reads every .md file under KNOWLEDGE_DIR, splits them into chunks, embeds
with the configured HuggingFace model, and (re)creates the Qdrant
collection from scratch — safe to re-run whenever documents change.

Prerequisite: Qdrant is running (see README / docker run command).
Run:  uv run python scripts/ingest_knowledge.py
"""

from pathlib import Path
from typing import Dict, List

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from core.config import settings
from core.logger import setup_logger
from infrastructure.vector_store.qdrant import build_embeddings


def load_documents() -> List[Document]:
    """Load every markdown file in KNOWLEDGE_DIR as one Document each."""
    knowledge_dir = Path(settings.KNOWLEDGE_DIR)
    paths = sorted(knowledge_dir.glob("*.md"))
    if not paths:
        raise SystemExit(f"Can not find any markdown files in {knowledge_dir.resolve()}")

    documents = [
        Document(
            page_content=path.read_text(encoding="utf-8"),
            metadata={
                "document_id": path.stem,
                "title": path.stem.replace("-", " "),
                "source_file": path.name,
            },
        )
        for path in paths
    ]
    logger.info("Loaded documents [count={}, files={}]", len(documents), [p.name for p in paths])
    return documents


def main() -> None:
    """Split, embed, and upsert the knowledge base into Qdrant."""
    setup_logger()

    documents = load_documents()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(documents)

    # Retriever reads chunk_index from metadata; the splitter only copies the
    # parent document's metadata, so number the chunks per source file here.
    index_per_file: Dict[str, int] = {}
    for chunk in chunks:
        source_file = chunk.metadata["source_file"]
        chunk.metadata["chunk_index"] = index_per_file.get(source_file, 0)
        index_per_file[source_file] = chunk.metadata["chunk_index"] + 1

    logger.info("Split into chunks [count={}]", len(chunks))

    QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=build_embeddings(),
        url=settings.QDRANT_URL,
        collection_name=settings.QDRANT_COLLECTION,
        force_recreate=True,
    )
    logger.info(
        "Ingest DONE [collection={}, chunks={}]", settings.QDRANT_COLLECTION, len(chunks)
    )


if __name__ == "__main__":
    main()
