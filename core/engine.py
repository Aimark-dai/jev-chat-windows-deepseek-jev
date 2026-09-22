# -*- coding: utf-8 -*-
"""整条链的唯一入口：DeepSeek 起草 → 可选 DeepSeek/TypeSafe JEV 判断排序。

平台无关。SSE 消费者、悬浮窗、命令行 demo 都只调 analyze()。
"""
from __future__ import annotations

try:
    from .draft import draft_candidates
    from .jev_client import ask as deepseek_ask
    from .questions import JUDGE_QUESTIONS, build_rank_question, build_review_questions, build_state
    from .typesafe_client import ask as typesafe_ask
except ImportError:
    from draft import draft_candidates
    from jev_client import ask as deepseek_ask
    from questions import JUDGE_QUESTIONS, build_rank_question, build_review_questions, build_state
    from typesafe_client import ask as typesafe_ask

_REPLY_IDX = {"reply_a": 0, "reply_b": 1, "reply_c": 2}


def _quality_passed(answers: dict) -> bool:
    return (answers.get("candidate_quality") or {}).get("choice") == "pass"


def _sum_usage(results: list[dict]) -> dict:
    usage = {"typesafe_calls": len(results)}
    for result in results:
        for key, value in (result.get("usage") or {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage[key] = usage.get(key, 0) + value
    return usage


def _review_state(state: dict, candidates: list[str]) -> dict:
    keys = tuple(_REPLY_IDX)
    return {
        **state,
        "candidate_replies": [
            {"id": keys[index], "text": text}
            for index, text in enumerate(candidates)
        ],
    }


def analyze(messages: list, relationship: str, model: str | None = None,
            timeout: float = 30, context: int = 10, provider: str = "deepseek",
            reply_to: str | None = None, style: str = "", thinking: bool = False,
            judge_provider: str = "deepseek") -> dict:
    """messages: [(from, text)] from ∈ {her, me}，最新一条在最后；
    群聊里可以带第三项 name（说这句话的人），单聊不带。
    context: 起草和判断各看最近多少条消息（用户设置里的「参考上下文」）。
    provider: 起草固定为 deepseek。
    judge_provider: deepseek 或 typesafe；后者直连 TypeSafe 官方 JEV。
    reply_to: 群聊里指定回复给谁；None = 正常回复。
    style: 用户自己描述的说话风格，只影响起草。
    thinking: 起草时是否开思考模式，只影响起草，默认关。
    model=None 用该来源的默认模型。

    返回 {candidates, best_index, best_reply, scores, answers, usage, reply_to}。
    scores 是每条候选的胜出概率（0~1），取自 best_reply.probabilities，取不到记 0.0。
    只有对方最新说话时才有意义调它——是不是该触发由调用方判断（看 latest_from）。
    """
    state = build_state(messages, relationship, keep=context, reply_to=reply_to)
    regenerated = False
    quality_passed = True

    if judge_provider == "typesafe":
        calls = []
        pre_result = typesafe_ask(state, JUDGE_QUESTIONS, timeout=timeout)
        calls.append(pre_result)
        pre_answers = pre_result.get("answers") or {}
        candidates = draft_candidates(
            messages, relationship, provider=provider, model=model, timeout=timeout,
            keep=context, reply_to=reply_to, style=style, thinking=thinking,
            jev_analysis=pre_answers,
        )
        if not candidates:
            raise ValueError("DeepSeek 未生成可用候选")
        review_result = typesafe_ask(
            _review_state(state, candidates), build_review_questions(candidates), timeout=timeout
        )
        calls.append(review_result)
        review_answers = review_result.get("answers") or {}
        if not _quality_passed(review_answers):
            rejected_candidates = candidates
            candidates = draft_candidates(
                messages, relationship, provider=provider, model=model, timeout=timeout,
                keep=context, reply_to=reply_to, style=style, thinking=thinking,
                jev_analysis=pre_answers, revision_feedback=review_answers,
                rejected_candidates=rejected_candidates,
            )
            if not candidates:
                raise ValueError("DeepSeek 重写后仍未生成可用候选")
            regenerated = True
            review_result = typesafe_ask(
                _review_state(state, candidates), build_review_questions(candidates), timeout=timeout
            )
            calls.append(review_result)
            review_answers = review_result.get("answers") or {}
        quality_passed = _quality_passed(review_answers)
        answers = {**pre_answers, **review_answers}
        usage = _sum_usage(calls)
    else:
        candidates = draft_candidates(
            messages, relationship, provider=provider, model=model, timeout=timeout,
            keep=context, reply_to=reply_to, style=style, thinking=thinking,
        )
        if not candidates:
            raise ValueError("DeepSeek 未生成可用候选")
        questions = dict(JUDGE_QUESTIONS)
        if len(candidates) >= 2:
            questions.update(build_rank_question(candidates))
        result = deepseek_ask(state, questions, timeout=timeout)
        answers = result.get("answers") or {}
        usage = result.get("usage") or {}
    best_key = (answers.get("best_reply") or {}).get("choice")
    best_index = _REPLY_IDX.get(best_key, 0)  # 解析不出就退第一条
    if best_index >= len(candidates):
        best_index = 0

    probabilities = (answers.get("best_reply") or {}).get("probabilities") or {}
    scores = [0.0, 0.0, 0.0]
    for key, idx in _REPLY_IDX.items():
        try:
            scores[idx] = float(probabilities.get(key, 0.0))
        except (TypeError, ValueError):
            scores[idx] = 0.0  # 脏数据一律按 0 处理

    return {
        "candidates": candidates,
        "best_index": best_index,
        "best_reply": candidates[best_index],
        "scores": scores,
        "answers": answers,
        "usage": usage,
        "reply_to": reply_to,
        "judge_provider": "typesafe" if judge_provider == "typesafe" else "deepseek",
        "quality_passed": quality_passed,
        "regenerated": regenerated,
    }
