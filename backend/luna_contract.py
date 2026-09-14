"""Bounded representation normalization. Never repair or synthesize question fields."""
import json
import logging
import re

from pydantic import ValidationError
from schemas import GeneratedQuestion

logger = logging.getLogger("uvicorn.error")
SAFE_KEYS = {"questions", "choices", "message", "content", "role", "finish_reason",
             "index", "id", "object", "created", "model", "usage", "system_fingerprint",
             "question_text", "options", "correct_answer", "explanation", "rag_source",
             "A", "B", "C", "D"}


class ProviderError(RuntimeError):
    """Only safe messages may cross the API boundary."""
    status_code = 503


class ResponseContractError(ProviderError):
    status_code = 502


def structural_log(event, value=None, **facts):
    # Unknown keys/validation locations can themselves contain private content.
    info = {"type": type(value).__name__ if type(value) in (dict, list, str, int, type(None)) else "other"}
    if isinstance(value, dict):
        info.update(keys=sorted(k for k in value if k in SAFE_KEYS),
                    unknown_key_count=sum(k not in SAFE_KEYS for k in value))
    elif isinstance(value, (str, list)):
        info["count"] = len(value)
    logger.warning("Luna %s %s", event, json.dumps(info | facts))


def invalid(value, reason, *, parse=False, paths=None):
    structural_log("response_contract_invalid", value, category="unparseable" if parse else "schema",
                   reason=reason, paths=paths or [])
    message = ("Luna returned non-JSON or unparseable output. Ask L&D to check the sanitized backend diagnostic."
               if parse else "Luna returned invalid question data. Ask L&D to check the sanitized schema diagnostic.")
    raise ResponseContractError(message)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("Non-standard JSON constant")


def unwrap_choices(value):
    """Azure ChatCompletions envelope: exactly one completed text choice."""
    choices = value.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        invalid(value, "expected_one_choice")
    choice = choices[0]
    message = choice.get("message")
    if (choice.get("finish_reason") not in (None, "stop") or not isinstance(message, dict)
            or message.get("role") not in (None, "assistant")
            or message.get("tool_calls") or message.get("refusal")
            or not isinstance(message.get("content"), str)):
        invalid(value, "expected_completed_text_message")
    return message["content"]


def normalize(raw):
    value = raw
    for _ in range(6):
        if isinstance(value, str):
            if len(value) > 2_000_000:
                invalid(value, "response_too_large", parse=True)
            text = value.strip()
            # No arbitrary substring search: only these fixed, non-semantic prefixes.
            for prefix in ("Here is the JSON:", "Here are the questions:", "JSON:"):
                if text.startswith(prefix):
                    text = text[len(prefix):].strip()
                    break
            if text.startswith("```"):
                match = re.fullmatch(r"```(?:json)?\s*\n([\s\S]*?)\n```", text)
                if not match:
                    invalid(value, "invalid_code_fence", parse=True)
                text = match[1].strip()
            try:
                value = json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
            except (ValueError, RecursionError):
                invalid(value, "invalid_json", parse=True)
        elif isinstance(value, dict):
            if set(value) == {"questions"}:
                value = value["questions"]
            elif "choices" in value and set(value) <= {
                    "choices", "id", "object", "created", "model", "usage", "system_fingerprint"}:
                value = unwrap_choices(value)
            else:
                invalid(value, "unsupported_or_ambiguous_envelope")
        elif isinstance(value, list):
            return value
        else:
            invalid(value, "expected_question_array")
    invalid(value, "wrapper_depth_exceeded")


def parse_questions(raw, expected_count):
    data = normalize(raw)
    if len(data) != expected_count:
        invalid(data, "question_count_mismatch")
    result = []
    for index, item in enumerate(data):
        if not isinstance(item, dict) or set(item) - set(GeneratedQuestion.model_fields):
            invalid(item, "noncanonical_question_fields", paths=[[index]])
        try:
            question = GeneratedQuestion.model_validate(item, strict=True)
            if not question.question_text.strip() or not question.explanation.strip():
                invalid(item, "blank_required_text", paths=[[index]])
            result.append(question)
        except ValidationError as error:
            paths = [[index] + [p if isinstance(p, int) or p in SAFE_KEYS else "unknown_field"
                               for p in e["loc"]] for e in error.errors(include_input=False, include_context=False)]
            invalid(item, "canonical_schema_validation", paths=paths[:20])
    return result
