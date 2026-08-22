"""
Local Embedding Backend — offline, key-free text embeddings.

Wraps the ONNX ``all-MiniLM-L6-v2`` model that ships with ``chromadb`` (already a
hard dependency of JARVIS) so vector memory works on a fresh install with no API
key and no extra packages.

Why this module exists rather than calling ChromaDB's ``DefaultEmbeddingFunction``
directly: ChromaDB's own downloader streams an ~80 MB archive in 1 KiB chunks
using httpx's default 5-second read timeout and only retries on a checksum
mismatch — never on a network timeout. On ordinary connections it fails partway
through and leaves no usable model behind. :func:`ensure_model_available` does
the same download with a long timeout, large chunks, resume support and real
retries, then hands off to ChromaDB, which finds the archive already present.

Every model constant (URL, checksum, cache layout) is read off the ChromaDB
class at runtime, so this keeps working if ChromaDB changes its bundled model.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
import tarfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# The files ChromaDB expects inside the extracted model folder.
_EXPECTED_MODEL_FILES = (
    "config.json",
    "model.onnx",
    "special_tokens_map.json",
    "tokenizer_config.json",
    "tokenizer.json",
    "vocab.txt",
)

_DOWNLOAD_CHUNK_SIZE = 1024 * 512  # 512 KiB
_DOWNLOAD_ATTEMPTS = 4

ProgressCallback = Callable[[int, int], None]
"""Called as ``(bytes_downloaded, total_bytes)``; ``total_bytes`` is 0 if unknown."""


class LocalEmbeddingError(RuntimeError):
    """Raised when the local embedding model cannot be prepared or run."""


def _onnx_embedding_class() -> Any:
    """Return ChromaDB's ONNX MiniLM embedding-function class.

    Raises:
        LocalEmbeddingError: If chromadb is not installed.
    """
    try:
        from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
    except Exception as e:  # pragma: no cover - depends on chromadb layout
        raise LocalEmbeddingError(
            "chromadb is required for local embeddings. Install it with `pip install chromadb`."
        ) from e
    return ONNXMiniLM_L6_V2


def get_model_name() -> str:
    """Name of the bundled local embedding model (e.g. ``all-MiniLM-L6-v2``)."""
    return str(_onnx_embedding_class().MODEL_NAME)


def _model_paths() -> tuple[Path, Path, str, str]:
    """Resolve (download_dir, extracted_dir, archive_url, expected_sha256)."""
    cls = _onnx_embedding_class()
    download_dir = Path(cls.DOWNLOAD_PATH)
    extracted_dir = download_dir / cls.EXTRACTED_FOLDER_NAME
    return (
        download_dir,
        extracted_dir,
        str(cls.MODEL_DOWNLOAD_URL),
        str(cls._MODEL_SHA256),
    )


def is_model_downloaded() -> bool:
    """Return True if the local embedding model is already extracted and usable."""
    try:
        _, extracted_dir, _, _ = _model_paths()
    except LocalEmbeddingError:
        return False
    return all((extracted_dir / f).exists() for f in _EXPECTED_MODEL_FILES)


def _sha256(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download_archive(
    url: str,
    dest: Path,
    expected_sha256: str,
    on_progress: ProgressCallback | None = None,
) -> None:
    """Download the model archive with resume, retries and checksum verification.

    Raises:
        LocalEmbeddingError: If every attempt fails or the checksum never matches.
    """
    import httpx

    partial = dest.with_suffix(dest.suffix + ".part")
    last_error: Exception | None = None

    for attempt in range(1, _DOWNLOAD_ATTEMPTS + 1):
        resume_from = partial.stat().st_size if partial.exists() else 0
        headers = {"Range": f"bytes={resume_from}-"} if resume_from else {}

        try:
            timeout = httpx.Timeout(connect=30.0, read=120.0, write=120.0, pool=30.0)
            with (
                httpx.Client(timeout=timeout, follow_redirects=True) as client,
                client.stream("GET", url, headers=headers) as resp,
            ):
                    if resume_from and resp.status_code == 200:
                        # Server ignored the Range header; restart from scratch.
                        resume_from = 0
                    elif resume_from and resp.status_code != 206:
                        resp.raise_for_status()
                        resume_from = 0
                    else:
                        resp.raise_for_status()

                    total = int(resp.headers.get("content-length", 0)) + resume_from
                    mode = "ab" if resume_from else "wb"
                    done = resume_from

                    with open(partial, mode) as f:
                        for chunk in resp.iter_bytes(chunk_size=_DOWNLOAD_CHUNK_SIZE):
                            done += f.write(chunk)
                            if on_progress:
                                on_progress(done, total)

            actual = _sha256(partial)
            if actual != expected_sha256:
                partial.unlink(missing_ok=True)
                raise LocalEmbeddingError(
                    f"Checksum mismatch for {dest.name} "
                    f"(expected {expected_sha256[:12]}…, got {actual[:12]}…)."
                )

            partial.replace(dest)
            return

        except Exception as e:
            last_error = e
            logger.warning(
                "Local embedding model download attempt %d/%d failed: %s",
                attempt,
                _DOWNLOAD_ATTEMPTS,
                e,
            )

    raise LocalEmbeddingError(
        f"Could not download the local embedding model from {url}: {last_error}"
    )


def ensure_model_available(on_progress: ProgressCallback | None = None) -> Path:
    """Download and extract the local embedding model if it is not already present.

    Safe to call repeatedly; returns immediately once the model is on disk.

    Args:
        on_progress: Optional ``(downloaded, total)`` progress callback.

    Returns:
        Path to the extracted model directory.

    Raises:
        LocalEmbeddingError: If the model cannot be downloaded or extracted.
    """
    download_dir, extracted_dir, url, expected_sha256 = _model_paths()

    if is_model_downloaded():
        return extracted_dir

    download_dir.mkdir(parents=True, exist_ok=True)
    archive = download_dir / _onnx_embedding_class().ARCHIVE_FILENAME

    if not archive.exists() or _sha256(archive) != expected_sha256:
        logger.info("Downloading local embedding model %s…", get_model_name())
        _download_archive(url, archive, expected_sha256, on_progress)

    try:
        # Extract to a staging dir first so a failure can't leave a half-written
        # model that passes the file-existence check.
        staging = download_dir / ".extract_tmp"
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)

        with tarfile.open(archive, mode="r:gz") as tar:
            try:
                tar.extractall(path=staging, filter="data")
            except TypeError:
                # `filter` was added in Python 3.12.
                tar.extractall(path=staging)

        produced = staging / _onnx_embedding_class().EXTRACTED_FOLDER_NAME
        source = produced if produced.is_dir() else staging

        extracted_dir.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            target = extracted_dir / item.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    target.unlink()
            shutil.move(str(item), str(target))

        shutil.rmtree(staging, ignore_errors=True)
    except LocalEmbeddingError:
        raise
    except Exception as e:
        raise LocalEmbeddingError(
            f"Failed to extract the local embedding model archive {archive}: {e}"
        ) from e

    if not is_model_downloaded():
        missing = [f for f in _EXPECTED_MODEL_FILES if not (extracted_dir / f).exists()]
        raise LocalEmbeddingError(
            f"Local embedding model is incomplete after extraction; missing: {missing}"
        )

    logger.info("Local embedding model ready at %s", extracted_dir)
    return extracted_dir


class LocalEmbedder:
    """Offline embedding backend using ChromaDB's bundled ONNX MiniLM model.

    Requires no API key and no network access once the model has been downloaded.
    The model is loaded lazily on first use, off the event loop.
    """

    def __init__(self) -> None:
        self._fn: Any | None = None
        self._dimension: int | None = None
        self._lock = asyncio.Lock()

    @property
    def model_name(self) -> str:
        """Name of the underlying model."""
        return get_model_name()

    @property
    def dimension(self) -> int | None:
        """Embedding dimension, known only after the first successful embed."""
        return self._dimension

    @staticmethod
    def is_ready() -> bool:
        """Return True if the model is already on disk (no download needed)."""
        return is_model_downloaded()

    async def prepare(self, on_progress: ProgressCallback | None = None) -> None:
        """Ensure the model is downloaded and loaded. Idempotent."""
        async with self._lock:
            await self._load(on_progress)

    def _load_sync(self, on_progress: ProgressCallback | None) -> Any:
        """Blocking model preparation and instantiation."""
        ensure_model_available(on_progress)
        return _onnx_embedding_class()()

    async def _load(self, on_progress: ProgressCallback | None = None) -> Any:
        """Load the embedding function, downloading the model if needed."""
        if self._fn is None:
            self._fn = await asyncio.to_thread(self._load_sync, on_progress)
        return self._fn

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts locally.

        Args:
            texts: Texts to embed.

        Returns:
            One embedding vector per input text.

        Raises:
            LocalEmbeddingError: If the model is unavailable or embedding fails.
        """
        if not texts:
            return []

        async with self._lock:
            fn = await self._load()

        try:
            vectors = await asyncio.to_thread(fn, list(texts))
        except Exception as e:
            raise LocalEmbeddingError(f"Local embedding failed: {e}") from e

        result = [[float(x) for x in vec] for vec in vectors]
        if result and self._dimension is None:
            self._dimension = len(result[0])
        return result
