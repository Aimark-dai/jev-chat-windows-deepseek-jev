"""把 TypeSafe JEV 的结构化字段转换成简短、可核对的界面文案。"""

from __future__ import annotations

from math import isfinite


CHOICE_LABELS = {
    "true_intent": {
        "confirm_you_care": "希望确认你在意",
        "vent_anger": "表达不满或受伤",
        "request_action": "希望你采取行动",
        "seek_explanation": "希望了解原因",
        "casual_chat": "轻松交流",
        "close_topic": "平和结束话题",
    },
    "best_action": {
        "check_history": "先核对聊天记录",
        "apologize": "为已知问题道歉",
        "give_commitment": "给出具体承诺",
        "explain": "说明事实与原因",
        "acknowledge": "回应并表达理解",
        "say_less": "简短回应或留白",
        "make_plan": "商量具体安排",
    },
    "she_needs": {
        "apology": "真诚道歉",
        "action": "具体行动或安排",
        "explanation": "清楚的解释",
        "care": "关注与在意",
        "nothing": "可能无需补充回应",
    },
}


def finite_number(value, lowest=0.0, highest=1.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if isfinite(value) and lowest <= value <= highest else None


def _percent(value):
    value = finite_number(value)
    return None if value is None else f"{value * 100:.0f}%"


def choice_label(name: str, item: dict | None) -> str:
    choice = (item or {}).get("choice")
    return CHOICE_LABELS.get(name, {}).get(choice, "暂未判断")


def choice_summary(name: str, item: dict | None) -> str:
    text = choice_label(name, item)
    confidence = _percent((item or {}).get("confidence"))
    return f"{text} · 把握 {confidence}" if confidence else text


def choice_distribution(name: str, item: dict | None, limit: int = 2) -> str:
    probabilities = (item or {}).get("probabilities")
    if not isinstance(probabilities, dict):
        return ""
    valid = []
    for key, value in probabilities.items():
        probability = finite_number(value)
        if probability is not None and key in CHOICE_LABELS.get(name, {}):
            valid.append((probability, key))
    valid.sort(reverse=True)
    if not valid:
        return ""
    values = [f"{CHOICE_LABELS[name][key]} {probability * 100:.0f}%"
              for probability, key in valid[:max(1, limit)]]
    prefix = "意图概率" if name == "true_intent" else "选项概率"
    return prefix + "：" + " · ".join(values)


def danger_summary(item: dict | None) -> str:
    item = item or {}
    score = finite_number(item.get("score"), highest=9)
    if score is None:
        return "危险度待判断"
    score_text = f"{score:.1f}".rstrip("0").rstrip(".")
    text = f"危险 {score_text}/9"
    confidence = _percent(item.get("confidence"))
    return f"{text} · 把握 {confidence}" if confidence else text


def high_risk_probability(item: dict | None):
    probabilities = (item or {}).get("probabilities")
    if not isinstance(probabilities, dict):
        return None
    total = 0.0
    found = False
    for key, value in probabilities.items():
        try:
            level = int(key)
        except (TypeError, ValueError):
            continue
        probability = finite_number(value)
        if level >= 6 and probability is not None:
            total += probability
            found = True
    return min(total, 1.0) if found else None


def probability_summary(answers: dict) -> str:
    values = []
    for name, label in (
        ("literal_question", "字面理解"),
        ("should_reply_now", "实质内容"),
        ("tension_resolved", "紧张缓解"),
    ):
        probability = _percent((answers.get(name) or {}).get("noul"))
        if probability:
            values.append(f"{label} {probability}")
    high_risk = high_risk_probability(answers.get("danger_level"))
    if high_risk is not None:
        values.append(f"高风险 {high_risk * 100:.0f}%")
    return " · ".join(values)
