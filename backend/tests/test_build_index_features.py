from scripts.build_index import parse_features


def test_parse_all_features_includes_dinov2() -> None:
    features = parse_features("all")

    assert "deep_cnn" in features
    assert "deep_triplet" in features
    assert "clip" in features
    assert "dinov2" in features


def test_parse_dinov2_feature() -> None:
    assert parse_features("dinov2") == ["dinov2"]


def test_parse_split_deep_features() -> None:
    assert parse_features("deep_cnn,deep_triplet") == ["deep_cnn", "deep_triplet"]
