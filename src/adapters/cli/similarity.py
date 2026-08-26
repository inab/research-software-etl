"""
Command-line interface for computing and storing tool-similarity scores.
"""

import argparse
import logging
import os

from dotenv import load_dotenv

from application.use_cases.stats.generate_similarity import compute_and_store_similarities
from infrastructure.config import Credentials, PipelineConfig
from infrastructure.db.repositories import from_config
from infrastructure.logging_config import resolve_level


def main():
    parser = argparse.ArgumentParser(
        description="Compute embedding-based similarity scores for research software tools."
    )
    parser.add_argument(
        "--collections", "-c",
        default="tools",
        help=(
            "Tool selection scope. "
            "Use 'tools' to process all tools, or provide a tag to process only tools "
            "whose data.tags contains that value."
        ),
    )
    parser.add_argument(
        "--k",
        type=int,
        default=12,
        help="Number of nearest neighbours to store per tool (default: 10).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recomputation even when similaritiesDev already contains data.",
    )
    parser.add_argument(
        "--model",
        default="Alibaba-NLP/gte-modernbert-base",
        help="HuggingFace sentence-transformers model name.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Encoding batch size (tune to available memory).",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Row-chunk size for the similarity computation pass.",
    )
    parser.add_argument(
        "--env-file", "-e",
        default=".env",
        help="File containing environment variables.",
    )
    parser.add_argument(
        "--loglevel", "-l",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level (default: LOG_LEVEL env var, else INFO).",
    )

    args = parser.parse_args()

    load_dotenv(args.env_file, override=True)

    logging.basicConfig(level=resolve_level(args.loglevel))

    repos = from_config(PipelineConfig.from_env())
    creds = Credentials.from_env()

    compute_and_store_similarities(
        repos,
        tag_or_tools=args.collections,
        k=args.k,
        force=args.force,
        model_name=args.model,
        batch_size=args.batch_size,
        chunk_size=args.chunk_size,
        hf_token=creds.huggingface_api_key,
    )


if __name__ == "__main__":
    main()
