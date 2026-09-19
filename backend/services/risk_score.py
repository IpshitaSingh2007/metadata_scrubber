from typing import Any, Dict, List, Optional


# Base scores based on the extractor's existing risk level.
BASE_RISK_SCORES = {
    "low": 15,
    "medium": 40,
    "high": 75,
}


# Extra points for fields explicitly marked sensitive.
SENSITIVITY_MODIFIER = 10


# Extra points for particularly specific or identifying fields.
SPECIFICITY_MODIFIERS = {
    "GPS.GPSLatitude": 15,
    "GPS.GPSLongitude": 15,
    "SerialNumber": 15,
    "Artist": 10,
    "Copyright": 10,
    "Author": 10,
    "DateTimeOriginal": 5,
    "DateTimeDigitized": 5,
    "CreationDate": 5,
    "ModDate": 5,
}


def calculate_field_score(field: Dict[str, Any]) -> int:
    """
    Calculate the privacy risk score for one metadata field.

    Score =
        base risk
        + sensitivity modifier
        + field-specific modifier

    The final score is capped at 100.
    """

    risk = str(field.get("risk", "low")).lower()

    base_score = BASE_RISK_SCORES.get(risk, 0)

    sensitivity_modifier = (
        SENSITIVITY_MODIFIER
        if field.get("sensitive", False)
        else 0
    )

    specificity_modifier = SPECIFICITY_MODIFIERS.get(
        field.get("key", ""),
        0,
    )

    score = (
        base_score
        + sensitivity_modifier
        + specificity_modifier
    )

    return min(score, 100)


def get_risk_level(score: float) -> str:
    """
    Convert a numerical risk score into a user-facing risk level.

    0-29   = LOW
    30-59  = MEDIUM
    60-79  = HIGH
    80-100 = CRITICAL
    """

    if score < 30:
        return "LOW"

    if score < 60:
        return "MEDIUM"

    if score < 80:
        return "HIGH"

    return "CRITICAL"


def calculate_overall_score(
    fields: List[Dict[str, Any]]
) -> int:
    """
    Calculate the overall privacy risk score.

    The highest-risk field has full weight.
    Additional fields contribute with diminishing weights.

    This prevents a highly sensitive field such as GPS coordinates
    from being averaged away by many low-risk fields.
    """

    if not fields:
        return 0

    scores = sorted(
        (
            calculate_field_score(field)
            for field in fields
        ),
        reverse=True,
    )

    weights = [
        1.0,
        0.30,
        0.20,
        0.10,
        0.05,
    ]

    total = 0.0

    for index, score in enumerate(scores):

        if index < len(weights):
            weight = weights[index]
        else:
            weight = 0.02

        total += score * weight

    return min(round(total), 100)


def calculate_category_summary(
    fields: List[Dict[str, Any]]
) -> Dict[str, Dict[str, int]]:
    """
    Group metadata fields by category.

    For each category:
        count = number of metadata fields
        score = highest individual risk score in that category
    """

    categories: Dict[str, Dict[str, int]] = {}

    for field in fields:

        category = field.get("category", "other")

        score = calculate_field_score(field)

        if category not in categories:
            categories[category] = {
                "count": 0,
                "score": 0,
            }

        categories[category]["count"] += 1

        categories[category]["score"] = max(
            categories[category]["score"],
            score,
        )

    return categories


def calculate_risk_report(
    fields: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Add an individual risk score to every metadata field
    and calculate the overall risk report.

    The original extractor fields are not modified.
    """

    scored_fields = []

    for field in fields:

        scored_field = dict(field)

        scored_field["score"] = calculate_field_score(field)

        scored_fields.append(scored_field)

    overall_score = calculate_overall_score(fields)

    return {
        "fields": scored_fields,
        "overall_score": overall_score,
        "overall_level": get_risk_level(overall_score),
        "category_summary": calculate_category_summary(fields),
    }


def calculate_initial_and_final_risk(
    fields: List[Dict[str, Any]],
    keep: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Calculate both the original risk and the risk remaining
    after the user's KEEP selections.

    `keep` contains exact metadata field keys that the user
    chose to preserve.

    Example:

        fields = [
            {"key": "GPS.GPSLatitude", ...},
            {"key": "Model", ...},
        ]

        keep = ["Model"]

    The initial risk includes both fields.

    The final risk includes only Model because GPS.GPSLatitude
    will be removed during scrubbing.
    """

    if keep is None:
        keep = []

    keep_set = set(keep)

    # Risk before any metadata is removed.
    initial_report = calculate_risk_report(fields)

    # Only metadata explicitly selected to KEEP remains.
    remaining_fields = [
        field
        for field in fields
        if field.get("key") in keep_set
    ]

    # Risk after scrubbing.
    final_report = calculate_risk_report(remaining_fields)

    return {
        "initial_score": initial_report["overall_score"],
        "initial_level": initial_report["overall_level"],

        "final_score": final_report["overall_score"],
        "final_level": final_report["overall_level"],

        "initial_category_summary": initial_report[
            "category_summary"
        ],

        "final_category_summary": final_report[
            "category_summary"
        ],

        "fields": final_report["fields"],
    }