import argparse
import json
import sys

from groq import Groq

from config import GROQ_API_KEY, logger
from pipeline import process_image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OCR invoice image → structured JSON"
    )
    parser.add_argument("input", help="Path to input JPEG image")
    parser.add_argument("output", help="Path to output JSON file")
    parser.add_argument(
        "--currency",
        default="EUR",
        help="Currency code (default: EUR)",
    )
    args = parser.parse_args()

    if not GROQ_API_KEY:
        logger.error(
            "GROQ_API_KEY environment variable is not set. "
            "Export it before running."
        )
        sys.exit(1)

    client = Groq(api_key=GROQ_API_KEY)

    try:
        doc = process_image(args.input, client, currency=args.currency)
    except Exception as e:
        logger.error("Pipeline failed: %s", e)
        sys.exit(1)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(doc.model_dump(), f, indent=2, ensure_ascii=False)

    logger.info("Output written to %s", args.output)


if __name__ == "__main__":
    main()
