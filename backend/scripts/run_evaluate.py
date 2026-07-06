"""Run one evaluation from the command line and print JSON metrics."""

from __future__ import annotations

import argparse
import json

from app.db.database import SessionLocal
from app.services.eval_service import evaluate_dataset_feature


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate one CBIR feature")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--feature", default="deep_triplet")
    parser.add_argument("--metric", default="cosine")
    parser.add_argument("--k", type=int, default=12)
    parser.add_argument("--sample", type=int, default=100)
    args = parser.parse_args()
    with SessionLocal() as db:
        result = evaluate_dataset_feature(
            db,
            dataset=args.dataset,
            feature=args.feature,
            metric=args.metric,
            k=args.k,
            sample=args.sample,
        )
    print(
        json.dumps(
            {
                "dataset": args.dataset,
                "feature": result.feature,
                "metric": result.metric,
                "map": result.map,
                "p_at_k": result.p_at_k,
                "query_count": result.query_count,
                "elapsed_ms": result.elapsed_ms,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
