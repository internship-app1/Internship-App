"""
Sentence embedding utilities for semantic job-resume matching.

Model: all-MiniLM-L6-v2 (~90MB, 384-dim vectors, CPU-friendly)
Loaded lazily on first call so Railway startup time is unchanged.
"""
import json
import logging

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        logger.info("Loading sentence-transformer model (first call only)...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded.")
    return _model


def embed_text(text: str) -> list:
    """Embed a single string. Returns a 384-dim float list (L2-normalised)."""
    if not text or not text.strip():
        return []
    model = _get_model()
    return model.encode(text.strip(), normalize_embeddings=True).tolist()


def embed_batch(texts: list) -> list:
    """Embed a list of strings. Returns a list of 384-dim float lists."""
    non_empty = [t.strip() for t in texts if t and t.strip()]
    if not non_empty:
        return [[] for _ in texts]
    model = _get_model()
    vecs = model.encode(non_empty, batch_size=32, normalize_embeddings=True).tolist()
    # Re-align with original list (empty inputs get empty vectors)
    result = []
    vec_iter = iter(vecs)
    for t in texts:
        if t and t.strip():
            result.append(next(vec_iter))
        else:
            result.append([])
    return result


def cosine_similarity(a: list, b: list) -> float:
    """Cosine similarity between two L2-normalised vectors (dot product)."""
    if not a or not b:
        return 0.0
    import numpy as np
    return float(np.dot(np.array(a, dtype=float), np.array(b, dtype=float)))


def compute_resume_embedding(resume_text: str) -> list:
    """Embed the full resume text for use at match time."""
    # Truncate to ~8k chars — enough semantic content, avoids model token limits
    return embed_text(resume_text[:8000])


def generate_job_embeddings_sync(jobs_flat: list) -> None:
    """
    Compute and persist embeddings for a batch of job dicts (from the crawl pipeline).
    Each job dict must have 'job_hash' and 'description'.
    Safe to call repeatedly — existing embeddings are overwritten.
    """
    from job_database import save_job_embeddings, get_db, close_db

    jobs_with_desc = [(j["job_hash"], j.get("description", "") or "") for j in jobs_flat if j.get("job_hash")]
    if not jobs_with_desc:
        return

    hashes = [h for h, _ in jobs_with_desc]
    descs = [d for _, d in jobs_with_desc]

    logger.info("Generating embeddings for %d crawled jobs...", len(hashes))
    try:
        vectors = embed_batch(descs)
        db = get_db()
        try:
            save_job_embeddings(hashes, vectors, db)
            db.commit()
        finally:
            close_db(db)
        logger.info("Embeddings saved for %d jobs.", len(hashes))
    except Exception as exc:
        logger.error("Embedding generation failed: %s", exc)
