"""Tests for Triplet Loss metric-learning helpers."""

import torch

from scripts.train_cifar_triplet import (
    batch_hard_triplet_loss,
    retrieval_precision_at_k,
)


def test_batch_hard_triplet_loss_is_small_for_separated_classes() -> None:
    embeddings = torch.tensor(
        [
            [1.0, 0.0],
            [0.9, 0.1],
            [-1.0, 0.0],
            [-0.9, -0.1],
        ],
        dtype=torch.float32,
    )
    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
    labels = torch.tensor([0, 0, 1, 1])

    loss = batch_hard_triplet_loss(embeddings, labels, margin=0.2)

    assert float(loss.item()) == 0.0


def test_retrieval_precision_at_k_matches_same_class_neighbors() -> None:
    embeddings = torch.tensor(
        [
            [1.0, 0.0],
            [0.9, 0.1],
            [0.0, 1.0],
            [0.1, 0.9],
        ],
        dtype=torch.float32,
    )
    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
    labels = torch.tensor([0, 0, 1, 1])

    assert retrieval_precision_at_k(embeddings, labels, k=1) == 1.0
