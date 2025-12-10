import numpy as np
from typing import List, Optional, Union, Tuple

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.core.logging import logger


settings = get_settings()
_embedding_model: Optional[SentenceTransformer] = None


# -----------------------------------------------------------------------
# Lifecycle
# -----------------------------------------------------------------------

async def load_embedding_model():
    global _embedding_model

    try:
        if _embedding_model is None:
            logger.info("Loading embedding model...")

            try:
                _embedding_model = SentenceTransformer(
                    settings.EMBEDDING_MODEL_NAME
                )
            except Exception as err:
                logger.exception(
                    f"Failed to initialize embedding model: {err}"
                )
                raise

            logger.info("Embedding model loaded.")
    except Exception:
        # Bubble error to caller to preserve baseline behavior
        raise


async def unload_embedding_model():
    global _embedding_model

    try:
        if _embedding_model is not None:
            logger.info("Unloading embedding model...")
            _embedding_model = None
    except Exception as err:
        logger.warning(f"Failed unloading embedding model cleanly: {err}")


def _ensure_model() -> SentenceTransformer:
    if _embedding_model is None:
        raise RuntimeError(
            "Embedding model not loaded yet. Call load_embedding_model() at startup."
        )
    return _embedding_model


# -----------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    try:
        if not text:
            return ""
        return " ".join(text.strip().split())
    except Exception:
        return ""


def numpy_to_list(v) -> List[float]:
    if v is None:
        return []

    try:
        return np.asarray(v, dtype=np.float32).tolist()
    except Exception:
        try:
            return [float(x) for x in v]
        except Exception:
            return []


# -----------------------------------------------------------------------
# RAW TEXT EMBEDDING — MATCHES ORIGINAL ENGINE
# -----------------------------------------------------------------------

def embed_text(text: str) -> List[float]:
    """
    Encodes raw text using SentenceTransformer

    Used for:
      - Query embedding
      - Individual document fields
    """

    try:
        model = _ensure_model()
    except Exception:
        # Preserve baseline behavior (exception bubbles)
        raise

    try:
        emb = model.encode(
            _normalize_text(text or ""),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
    except Exception as err:
        logger.exception(f"Embedding encode failed: {err}")
        return []

    try:
        return numpy_to_list(emb)
    except Exception:
        return []


# -----------------------------------------------------------------------
# MULTI-VECTOR FUSION — EXACT BASELINE PARITY
# -----------------------------------------------------------------------

def embed_multivector(
    description: str,
    steps: Union[str, List[str]],
    summary: str,
) -> Tuple[List[float], List[float], List[float], List[float]]:
    """
    PRIMARY EMBEDDING LOGIC (MATCHES ORIGINAL app.py)

    Computes:

      1. desc_embedding    ← encode(description)
      2. steps_embedding   ← encode(steps)
      3. summary_embedding ← encode(summary)

      main_vector = mean(desc, steps, summary)

    Returns:
        desc_embedding,
        steps_embedding,
        summary_embedding,
        main_vector
    """

    try:
        if isinstance(steps, list):
            steps_text = " ".join(str(s) for s in steps if s)
        else:
            steps_text = str(steps or "")
    except Exception:
        steps_text = ""

    try:
        desc_emb = embed_text(description)
    except Exception:
        desc_emb = []

    try:
        steps_emb = embed_text(steps_text)
    except Exception:
        steps_emb = []

    try:
        summary_emb = embed_text(summary)
    except Exception:
        summary_emb = []

    vectors = []

    try:
        if desc_emb:
            vectors.append(np.asarray(desc_emb, dtype=np.float32))
    except Exception:
        pass

    try:
        if steps_emb:
            vectors.append(np.asarray(steps_emb, dtype=np.float32))
    except Exception:
        pass

    try:
        if summary_emb:
            vectors.append(np.asarray(summary_emb, dtype=np.float32))
    except Exception:
        pass

    if vectors:
        try:
            avg = np.mean(vectors, axis=0)
            main_vector = numpy_to_list(avg)
        except Exception:
            main_vector = []
    else:
        try:
            main_vector = embed_text("")
        except Exception:
            main_vector = []

    return desc_emb, steps_emb, summary_emb, main_vector
