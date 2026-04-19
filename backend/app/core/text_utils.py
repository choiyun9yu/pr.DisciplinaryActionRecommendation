from __future__ import annotations

import re
from typing import Iterable, Optional


REQUIRED_COLUMNS = ["audit_source", "finding_title", "finding_detail", "action"]

ACTION_ORDER = [
    "통보",
    "개선",
    "시정",
    "주의",
    "경고",
    "부서경고",
    "경징계",
    "중징계",
]

ACTION_META: dict[str, dict[str, object]] = {
    "통보": {"group": "행정상 조치", "rank": 0},
    "개선": {"group": "행정상 조치", "rank": 1},
    "시정": {"group": "행정상 조치", "rank": 2},
    "주의": {"group": "비징계 신분상 조치", "rank": 3},
    "경고": {"group": "비징계 신분상 조치", "rank": 4},
    "부서경고": {"group": "기관/부서 조치", "rank": 5},
    "경징계": {"group": "징계", "rank": 6},
    "중징계": {"group": "징계", "rank": 7},
}

ACTION_PATTERNS: list[tuple[str, list[str]]] = [
    ("중징계", ["파면", "해임", "강등", "정직", "중징계"]),
    ("경징계", ["감봉", "견책", "경징계"]),
    ("부서경고", ["부서경고", "부서 경고", "기관경고", "기관 경고"]),
    ("경고", ["엄중경고", "엄중 경고", "경고"]),
    ("주의", ["엄중주의", "엄중 주의", "주의", "훈계"]),
    ("시정", ["현지시정", "시정"]),
    ("개선", ["개선"]),
    ("통보", ["통보"]),
]


def normalize_space(value: object) -> str:
    if value is None:
        return ""
    try:
        # NaN 방지
        if value != value:
            return ""
    except Exception:
        pass
    text = str(value)
    text = text.replace("\uf000", " ").replace("", " ").replace("•", " ")
    text = re.sub(r"[\t\r\n]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_text(value: object) -> str:
    text = normalize_space(value)
    text = text.replace("- ", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def validate_required_columns(columns: Iterable[str]) -> None:
    normalized = {col.lower() for col in columns}
    missing = [col for col in REQUIRED_COLUMNS if col.lower() not in normalized]
    if missing:
        raise ValueError(
            "입력 파일에 필수 컬럼이 없습니다. "
            f"필수 컬럼: {REQUIRED_COLUMNS} / 누락: {missing}"
        )


def extract_action_components(action: object) -> list[str]:
    raw = normalize_text(action).replace(" ", "")
    found: list[str] = []
    for canonical, patterns in ACTION_PATTERNS:
        if any(pattern.replace(" ", "") in raw for pattern in patterns):
            found.append(canonical)

    deduped: list[str] = []
    seen: set[str] = set()
    for label in ACTION_ORDER:
        if label in found and label not in seen:
            deduped.append(label)
            seen.add(label)
    return deduped


def choose_primary_action(action: object) -> Optional[str]:
    components = extract_action_components(action)
    if not components:
        return None
    return max(components, key=lambda label: int(ACTION_META[label]["rank"]))


def build_case_text(title: object, detail: object) -> str:
    title_text = normalize_text(title)
    detail_text = normalize_text(detail)

    parts: list[str] = []
    if title_text:
        parts.append(f"지적 내용: {title_text}")
    if detail_text:
        parts.append(f"세부 설명: {detail_text}")
    return "\n".join(parts).strip()
