"""Lightweight Chinese-to-English query rewriting for CLIP search."""

from __future__ import annotations

import re


_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

_COLOR_TERMS: list[tuple[str, str]] = [
    ("红色", "red"),
    ("红", "red"),
    ("蓝色", "blue"),
    ("蓝", "blue"),
    ("绿色", "green"),
    ("绿", "green"),
    ("黄色", "yellow"),
    ("黄", "yellow"),
    ("黑色", "black"),
    ("黑", "black"),
    ("白色", "white"),
    ("白", "white"),
    ("灰色", "gray"),
    ("灰", "gray"),
    ("棕色", "brown"),
    ("棕", "brown"),
    ("褐色", "brown"),
    ("橙色", "orange"),
    ("橙", "orange"),
    ("紫色", "purple"),
    ("紫", "purple"),
]

_SIZE_TERMS: list[tuple[str, str]] = [
    ("小型", "small"),
    ("小", "small"),
    ("大型", "large"),
    ("大", "large"),
]

_QUALITY_TERMS: list[tuple[str, str]] = [
    ("可爱", "cute"),
    ("漂亮", "beautiful"),
    ("模糊", "blurry"),
    ("清晰", "clear"),
]

_ACTION_TERMS: list[tuple[str, str]] = [
    ("正在行驶", "driving"),
    ("行驶", "driving"),
    ("开着", "driving"),
    ("奔跑", "running"),
    ("跑步", "running"),
    ("飞行", "flying"),
    ("飞翔", "flying"),
    ("航行", "sailing"),
    ("停着", "parked"),
    ("停放", "parked"),
]

_LOCATION_TERMS: list[tuple[str, str]] = [
    ("在路上", "on the road"),
    ("路上", "on the road"),
    ("道路上", "on the road"),
    ("马路上", "on the road"),
    ("街道上", "on the street"),
    ("街上", "on the street"),
    ("天空中", "in the sky"),
    ("天上", "in the sky"),
    ("水里", "in the water"),
    ("水上", "on the water"),
    ("海上", "on the sea"),
    ("草地上", "on the grass"),
    ("森林里", "in the forest"),
]

_TIME_TERMS: list[tuple[str, str]] = [
    ("傍晚", "at dusk"),
    ("黄昏", "at dusk"),
    ("晚上", "at night"),
    ("夜晚", "at night"),
    ("白天", "in the daytime"),
    ("早晨", "in the morning"),
    ("清晨", "in the morning"),
    ("中午", "at noon"),
]

_CLASS_TERMS: list[tuple[str, str]] = [
    ("小汽车", "car"),
    ("汽车", "car"),
    ("轿车", "car"),
    ("车辆", "car"),
    ("货车", "truck"),
    ("卡车", "truck"),
    ("大车", "truck"),
    ("飞机", "airplane"),
    ("客机", "airplane"),
    ("飞行器", "airplane"),
    ("轮船", "ship"),
    ("船只", "ship"),
    ("船", "ship"),
    ("小鸟", "bird"),
    ("鸟类", "bird"),
    ("鸟", "bird"),
    ("小猫", "cat"),
    ("猫咪", "cat"),
    ("猫", "cat"),
    ("小狗", "dog"),
    ("狗狗", "dog"),
    ("狗", "dog"),
    ("梅花鹿", "deer"),
    ("鹿", "deer"),
    ("青蛙", "frog"),
    ("蛙", "frog"),
    ("马匹", "horse"),
    ("马", "horse"),
    ("车", "car"),
]


def rewrite_clip_query(text: str) -> tuple[str, bool]:
    """Translate simple Chinese image queries into English CLIP prompts.

    The current CLIP model is English-first. For CIFAR-style queries, a small
    controlled vocabulary is more predictable than depending on online
    translation services.
    """

    query = " ".join(text.strip().split())
    if not query or not _CJK_RE.search(query):
        return query, False

    descriptors: list[str] = []
    descriptors.extend(_find_terms(query, _COLOR_TERMS))
    descriptors.extend(_find_terms(query, _SIZE_TERMS))
    descriptors.extend(_find_terms(query, _QUALITY_TERMS))
    category = _find_first_term(query, _CLASS_TERMS)
    actions = _find_terms(query, _ACTION_TERMS)
    locations = _find_terms(query, _LOCATION_TERMS)
    times = _find_terms(query, _TIME_TERMS)

    words: list[str] = []
    words.extend(descriptors)
    if category:
        words.append(category)
    words.extend(actions)
    words.extend(locations)
    words.extend(times)

    if not words:
        return query, False
    return " ".join(_dedupe(words)), True


def _find_terms(query: str, terms: list[tuple[str, str]]) -> list[str]:
    found: list[str] = []
    for source, target in terms:
        if source in query:
            found.append(target)
    return _dedupe(found)


def _find_first_term(query: str, terms: list[tuple[str, str]]) -> str | None:
    for source, target in terms:
        if source in query:
            return target
    return None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
