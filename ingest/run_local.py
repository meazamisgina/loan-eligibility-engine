from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from ingest.config import upload_dir
from ingest.handler import process_file

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Ingest user CSV files into PostgreSQL")
    parser.add_argument("files", nargs="*", help="CSV files (default: all in UPLOAD_DIR)")
    args = parser.parse_args()

    paths = [Path(item) for item in args.files] or sorted(upload_dir().glob("*.csv"))
    if not paths:
        logger.info("no CSV files found in %s", upload_dir())
        return 0

    exit_code = 0
    for path in paths:
        report = process_file(path)
        print(
            f"{report.source_filename}: total={report.total_rows} "
            f"valid={report.valid_rows} rejected={report.rejected_rows} "
            f"batch={report.batch_id}"
        )
        for row_number, reason in report.rejections[:10]:
            print(f"  row {row_number}: {reason}")
        if report.error:
            print(f"  FILE ERROR: {report.error}")
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())