"""CLI script and utility to download Dhan daily scrip master CSV and ingest into PostgreSQL."""

from __future__ import annotations

import argparse
import io
import logging
import sys
from pathlib import Path

from app.contracts import heartbeat as hb
from app.dhan.instruments import IngestSummary, ingest_instruments
from app.dhan.transport import download_remote_file

logger = logging.getLogger("app.dhan.sync_master")

DHAN_DETAILED_SCRIP_MASTER_URL = (
    "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"
)
DHAN_COMPACT_SCRIP_MASTER_URL = (
    "https://images.dhan.co/api-data/api-scrip-master.csv"
)


def download_scrip_master(url: str = DHAN_DETAILED_SCRIP_MASTER_URL, timeout: int = 60) -> bytes:
    """Download Dhan scrip master CSV data over HTTP/HTTPS."""
    logger.info("Downloading Dhan scrip master from %s ...", url)
    content = download_remote_file(url, timeout=float(timeout))
    logger.info("Downloaded %d bytes from %s", len(content), url)
    return content


def sync_scrip_master(
    csv_source: str | bytes | Path | io.StringIO | io.BytesIO | None = None,
    source_url: str = DHAN_DETAILED_SCRIP_MASTER_URL,
    batch_size: int = 2000,
) -> IngestSummary:
    """Sync Dhan scrip master into PostgreSQL database.

    If csv_source is provided, ingests that source directly.
    Otherwise downloads the live detailed CSV from Dhan CDN.
    """
    engine = hb.make_engine()

    if csv_source is None:
        try:
            csv_data = download_scrip_master(url=source_url)
        except Exception as exc:
            logger.warning(
                "Failed to download from %s: %s. Falling back to compact URL...",
                source_url,
                exc,
            )
            csv_data = download_scrip_master(url=DHAN_COMPACT_SCRIP_MASTER_URL)
        csv_source = csv_data

    logger.info("Parsing and ingesting scrip master into PostgreSQL...")
    summary = ingest_instruments(engine, csv_source=csv_source, batch_size=batch_size)
    logger.info(
        "Sync completed: %d total rows, %d upserted, %d skipped, segments: %s",
        summary.total_rows,
        summary.inserted_or_updated,
        summary.skipped,
        summary.distinct_segments,
    )
    return summary


def main() -> None:
    """CLI entry point for syncing Dhan instruments."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Sync Dhan detailed scrip master into PostgreSQL.")
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=None,
        help="Path to local scrip master CSV file instead of downloading",
    )
    parser.add_argument(
        "--url",
        "-u",
        type=str,
        default=DHAN_DETAILED_SCRIP_MASTER_URL,
        help="Remote URL to download scrip master CSV from",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=2000,
        help="Database bulk upsert batch size",
    )
    args = parser.parse_args()

    try:
        if args.file:
            if not args.file.exists():
                logger.error("Specified file does not exist: %s", args.file)
                sys.exit(1)
            summary = sync_scrip_master(csv_source=args.file, batch_size=args.batch_size)
        else:
            summary = sync_scrip_master(source_url=args.url, batch_size=args.batch_size)

        print("\n--- Ingestion Summary ---")
        print(f"Total Rows: {summary.total_rows}")
        print(f"Upserted:   {summary.inserted_or_updated}")
        print(f"Skipped:    {summary.skipped}")
        print(f"Segments:   {', '.join(summary.distinct_segments)}")
        if summary.errors:
            print(f"Errors ({len(summary.errors)}): {summary.errors[:5]}")
    except Exception as exc:
        logger.exception("Failed to sync Dhan scrip master: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
