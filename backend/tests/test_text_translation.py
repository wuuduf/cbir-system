"""Tests for lightweight CLIP text query rewriting."""

from app.services.text_translation import rewrite_clip_query


def test_rewrite_chinese_color_and_category() -> None:
    translated, applied = rewrite_clip_query("红色汽车")

    assert applied is True
    assert translated == "red car"


def test_rewrite_chinese_modifier_and_category() -> None:
    translated, applied = rewrite_clip_query("一只可爱的小狗")

    assert applied is True
    assert translated == "small cute dog"


def test_rewrite_chinese_scene_query() -> None:
    translated, applied = rewrite_clip_query("傍晚在路上行驶的红色汽车")

    assert applied is True
    assert translated == "red car driving on the road at dusk"


def test_rewrite_english_query_unchanged() -> None:
    translated, applied = rewrite_clip_query("a red car")

    assert applied is False
    assert translated == "a red car"
