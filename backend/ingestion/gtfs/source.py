"""Obtaining GTFS files: download the ZIP, verify it and extract it safely."""

import hashlib
import logging
import zipfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class GtfsSourceError(Exception):
    """The GTFS feed could not be downloaded or opened."""


def download_feed(url: str, target_dir: Path, user_agent: str, timeout: float = 60.0) -> Path:
    """Stream the GTFS ZIP to disk (it is ~60 MB, so we never hold it in memory)."""
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "gtfs_feed.zip"
    partial = target.with_suffix(".zip.part")
    logger.info("Downloading GTFS feed from %s", url)
    try:
        with httpx.stream(
            "GET", url, follow_redirects=True, timeout=timeout, headers={"User-Agent": user_agent}
        ) as response:
            response.raise_for_status()
            with partial.open("wb") as file:
                for chunk in response.iter_bytes(chunk_size=1 << 20):
                    file.write(chunk)
    except httpx.HTTPError as exc:
        partial.unlink(missing_ok=True)
        raise GtfsSourceError(f"Could not download GTFS feed from {url}: {exc}") from exc
    partial.replace(target)
    logger.info("Downloaded %.1f MB to %s", target.stat().st_size / 1e6, target)
    return target


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_feed(zip_path: Path, target_dir: Path) -> Path:
    """Extract the `.txt` files of a GTFS ZIP into `target_dir` and return that directory.

    Files inside a sub-folder of the archive are flattened (some publishers nest them).
    Only plain file names are written, which protects against "zip slip" path tricks.
    """
    if not zipfile.is_zipfile(zip_path):
        raise GtfsSourceError(f"{zip_path} is not a valid ZIP file")
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        members = [m for m in archive.infolist() if not m.is_dir() and m.filename.endswith(".txt")]
        if not members:
            raise GtfsSourceError(f"{zip_path} contains no GTFS .txt files")
        for member in members:
            name = Path(member.filename).name
            with archive.open(member) as src, (target_dir / name).open("wb") as dst:
                while block := src.read(1 << 20):
                    dst.write(block)
    logger.info("Extracted %d GTFS files", len(members))
    return target_dir
