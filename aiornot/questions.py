"""The per-site question set: loading, validating, and checking answers against it.

Six question types are supported:

    boolean  two choices, stored as true/false
    single   pick one option (multiple choice)
    multi    pick any number of options (multi-select); `min_selected` sets a floor
    scale    an integer from `min` to `max` (e.g. 1-5), with optional end labels
    text     a length-limited text response
    annotation  webpage locations with short explanatory notes

A `single` question may use `options_from: "<multi question id>"` instead of
`options`, in which case it only offers what the participant picked there.
"""

import hashlib
import json
import math
import re
from dataclasses import dataclass, field

from .config import ConfigError, read_json

TYPES = {"boolean", "single", "multi", "scale", "text", "annotation"}
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class Option:
    value: str
    label: str


@dataclass(frozen=True)
class Question:
    id: str
    type: str
    prompt: str
    phase: str = "review"
    required: bool = True
    required_unless: dict | None = None
    help: str | None = None
    options: tuple[Option, ...] = ()
    options_from: str | None = None
    min_selected: int = 1
    max_selected: int | None = None
    max_length: int = 1000
    max_annotations: int = 3
    min: int = 1
    max: int = 5
    min_label: str | None = None
    max_label: str | None = None
    true_label: str = "Yes"
    false_label: str = "No"

    def option_values(self, questions_by_id):
        source = questions_by_id[self.options_from] if self.options_from else self
        return [o.value for o in source.options]

    def to_client(self, questions_by_id):
        data = {k: v for k, v in self.__dict__.items() if v is not None}
        if self.options_from:
            data["options"] = questions_by_id[self.options_from].options
        data["options"] = [o.__dict__ for o in data.get("options", ())]
        return data


@dataclass(frozen=True)
class QuestionSet:
    version_label: str
    questions: list[Question]
    raw_hash: str = field(repr=False)

    @property
    def by_id(self):
        return {q.id: q for q in self.questions}

    @property
    def version(self):
        """Label plus content hash, so an edited file is never mistaken for the old one."""
        return f"{self.version_label}+{self.raw_hash}"

    def to_client(self):
        by_id = self.by_id
        return [q.to_client(by_id) for q in self.questions]

    def for_phase(self, phase):
        return QuestionSet(self.version_label, [q for q in self.questions if q.phase == phase], self.raw_hash)


def parse_option(raw, qid):
    if isinstance(raw, str):
        return Option(value=raw, label=raw)
    if isinstance(raw, dict) and "value" in raw:
        return Option(value=str(raw["value"]), label=str(raw.get("label", raw["value"])))
    raise ConfigError(f"questions.json: question {qid!r} has a bad option: {raw!r}")


def load_questions(paths):
    path = paths.config_dir / "questions.json"
    raw = read_json(path)
    return parse_questions(raw)


def parse_questions(raw):
    raw_hash = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()[:8]
    questions = []
    seen = {}
    for item in raw.get("questions", []):
        qid = item.get("id")
        if not isinstance(qid, str) or not ID_PATTERN.match(qid):
            raise ConfigError(
                f"questions.json: id {qid!r} must be lowercase letters, digits and _"
            )
        if qid in seen:
            raise ConfigError(f"questions.json: duplicate question id {qid!r}")
        if item.get("type") not in TYPES:
            raise ConfigError(
                f"questions.json: question {qid!r} has type {item.get('type')!r}; "
                f"use one of {sorted(TYPES)}"
            )
        fields = {k: v for k, v in item.items() if k in Question.__dataclass_fields__}
        fields["options"] = tuple(parse_option(o, qid) for o in item.get("options", []))
        unknown = set(item) - set(Question.__dataclass_fields__)
        if unknown:
            raise ConfigError(f"questions.json: question {qid!r} has unknown keys {sorted(unknown)}")
        q = Question(**fields)
        if q.phase not in {"review", "followup"}:
            raise ConfigError(f"questions.json: {qid!r} has an unknown phase")
        if q.type == "text" and (type(q.max_length) is not int or not 1 <= q.max_length <= 10000):
            raise ConfigError(f"questions.json: text {qid!r} needs max_length from 1 to 10000")
        if q.type == "annotation" and (type(q.max_annotations) is not int or not 1 <= q.max_annotations <= 10):
            raise ConfigError(f"questions.json: annotation {qid!r} needs max_annotations from 1 to 10")

        if q.type in {"single", "multi"}:
            if q.options_from:
                source = seen.get(q.options_from)
                if q.type != "single" or source is None or source.type != "multi":
                    raise ConfigError(
                        f"questions.json: {qid!r}: options_from must name an earlier multi question"
                    )
                if source.phase != q.phase:
                    raise ConfigError(f"questions.json: {qid!r} and its options source must share a phase")
            elif not q.options:
                raise ConfigError(f"questions.json: question {qid!r} needs options")
            values = [o.value for o in q.options]
            if len(set(values)) != len(values):
                raise ConfigError(f"questions.json: question {qid!r} repeats an option value")
            if q.type == "multi" and (
                type(q.min_selected) is not int or q.min_selected < 0 or
                (q.max_selected is not None and
                 (type(q.max_selected) is not int or not q.min_selected <= q.max_selected <= len(q.options)))
            ):
                raise ConfigError(f"questions.json: {qid!r} has invalid selection limits")
        if q.type == "scale" and not (isinstance(q.min, int) and isinstance(q.max, int) and q.min < q.max):
            raise ConfigError(f"questions.json: scale {qid!r} needs integer min < max")
        seen[qid] = q
        questions.append(q)

    if not questions:
        raise ConfigError("questions.json: no questions defined")
    for q in questions:
        condition = q.required_unless
        if condition is not None:
            if not isinstance(condition, dict) or set(condition) != {"question_id", "value"}:
                raise ConfigError(f"questions.json: {q.id!r} has invalid required_unless")
            source = seen.get(condition["question_id"])
            if source is None or source.id == q.id or source.type not in {"single", "boolean"}:
                raise ConfigError(f"questions.json: {q.id!r} needs a different choice question in required_unless")
            try:
                check_answer(source, condition["value"], seen)
            except AnswerError:
                raise ConfigError(f"questions.json: {q.id!r} has invalid required_unless value") from None
    return QuestionSet(
        version_label=str(raw.get("version", "unversioned")),
        questions=questions,
        raw_hash=raw_hash,
    )


class AnswerError(ValueError):
    pass


def is_blank(value):
    return value is None or value == [] or (isinstance(value, str) and not value.strip())


def valid_annotation(item):
    if not isinstance(item, dict) or set(item) - {"region"} != {
        "id", "page_path", "selector", "quote", "rect", "viewport", "note"
    }:
        return False
    for key, limit in {"id": 64, "page_path": 2000, "selector": 1000, "quote": 300, "note": 500}.items():
        if not isinstance(item[key], str) or len(item[key]) > limit:
            return False
    if not item["id"].strip() or not item["note"].strip():
        return False
    if not item["page_path"].startswith("/sites/") or "\\" in item["page_path"] or "\x00" in item["page_path"]:
        return False
    geometry_fields = [("rect", {"x", "y", "width", "height"}),
                       ("viewport", {"width", "height"})]
    if "region" in item:
        geometry_fields.append(("region", {"x", "y", "width", "height"}))
    for field, keys in geometry_fields:
        geometry = item[field]
        if not isinstance(geometry, dict) or set(geometry) != keys:
            return False
        if any(type(value) not in (int, float) or not -1e7 <= value <= 1e7 or not math.isfinite(value)
               for value in geometry.values()):
            return False
        if geometry["width"] <= 0 or geometry["height"] <= 0:
            return False
    if "region" in item:
        region = item["region"]
        if any(region[axis] < 0 or region[axis] + region[size] > 1 + 1e-6
               for axis, size in (("x", "width"), ("y", "height"))):
            return False
    return True


def check_answer(question, value, questions_by_id):
    """Raise AnswerError if `value` isn't a well-formed answer to `question`."""
    t = question.type
    if t == "boolean":
        ok = isinstance(value, bool)
    elif t == "scale":
        ok = isinstance(value, int) and not isinstance(value, bool) and question.min <= value <= question.max
    elif t == "single":
        ok = isinstance(value, str) and value in question.option_values(questions_by_id)
    elif t == "text":
        ok = isinstance(value, str) and len(value) <= question.max_length
    elif t == "annotation":
        ok = (
            isinstance(value, list) and len(value) <= question.max_annotations
            and all(valid_annotation(item) for item in value)
            and len({item["id"] for item in value}) == len(value)
        )
    else:  # multi
        allowed = set(question.option_values(questions_by_id))
        ok = (
            isinstance(value, list)
            and all(isinstance(v, str) and v in allowed for v in value)
            and len(set(value)) == len(value)
            and (question.max_selected is None or len(value) <= question.max_selected)
        )
    if not ok:
        raise AnswerError(f"invalid answer for {question.id!r}: {value!r}")


def missing_answers(question_set, answers):
    """Ids of required questions that are unanswered (or no longer valid) for one site."""
    by_id = question_set.by_id
    missing = []
    for q in question_set.questions:
        value = answers.get(q.id)
        if is_blank(value):
            condition = q.required_unless
            waived = condition is not None and answers.get(condition["question_id"]) == condition["value"]
            if q.required and not waived:
                missing.append(q.id)
            continue
        if q.type == "multi" and len(value) < q.min_selected:
            missing.append(q.id)
        elif q.options_from and value not in answers.get(q.options_from, []):
            # The participant un-ticked the option this answer pointed at.
            missing.append(q.id)
    return missing
