"""The per-site question set: loading, validating, and checking answers against it.

Four question types are supported, all closed-ended:

    boolean  two choices, stored as true/false
    single   pick one option (multiple choice)
    multi    pick any number of options (multi-select); `min_selected` sets a floor
    scale    an integer from `min` to `max` (e.g. 1-5), with optional end labels

A `single` question may use `options_from: "<multi question id>"` instead of
`options`, in which case it only offers what the participant picked there.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field

from .config import ConfigError, read_json

TYPES = {"boolean", "single", "multi", "scale"}
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
    required: bool = True
    help: str | None = None
    options: tuple[Option, ...] = ()
    options_from: str | None = None
    min_selected: int = 1
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


def parse_option(raw, qid):
    if isinstance(raw, str):
        return Option(value=raw, label=raw)
    if isinstance(raw, dict) and "value" in raw:
        return Option(value=str(raw["value"]), label=str(raw.get("label", raw["value"])))
    raise ConfigError(f"questions.json: question {qid!r} has a bad option: {raw!r}")


def load_questions(paths):
    path = paths.config_dir / "questions.json"
    raw = read_json(path)
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

        if q.type in {"single", "multi"}:
            if q.options_from:
                source = seen.get(q.options_from)
                if q.type != "single" or source is None or source.type != "multi":
                    raise ConfigError(
                        f"questions.json: {qid!r}: options_from must name an earlier multi question"
                    )
            elif not q.options:
                raise ConfigError(f"questions.json: question {qid!r} needs options")
            values = [o.value for o in q.options]
            if len(set(values)) != len(values):
                raise ConfigError(f"questions.json: question {qid!r} repeats an option value")
        if q.type == "scale" and not (isinstance(q.min, int) and isinstance(q.max, int) and q.min < q.max):
            raise ConfigError(f"questions.json: scale {qid!r} needs integer min < max")
        seen[qid] = q
        questions.append(q)

    if not questions:
        raise ConfigError("questions.json: no questions defined")
    return QuestionSet(
        version_label=str(raw.get("version", "unversioned")),
        questions=questions,
        raw_hash=raw_hash,
    )


class AnswerError(ValueError):
    pass


def is_blank(value):
    return value is None or value == [] or value == ""


def check_answer(question, value, questions_by_id):
    """Raise AnswerError if `value` isn't a well-formed answer to `question`."""
    t = question.type
    if t == "boolean":
        ok = isinstance(value, bool)
    elif t == "scale":
        ok = isinstance(value, int) and not isinstance(value, bool) and question.min <= value <= question.max
    elif t == "single":
        ok = isinstance(value, str) and value in question.option_values(questions_by_id)
    else:  # multi
        allowed = set(question.option_values(questions_by_id))
        ok = (
            isinstance(value, list)
            and all(isinstance(v, str) and v in allowed for v in value)
            and len(set(value)) == len(value)
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
            if q.required:
                missing.append(q.id)
            continue
        if q.type == "multi" and len(value) < q.min_selected:
            missing.append(q.id)
        elif q.options_from and value not in answers.get(q.options_from, []):
            # The participant un-ticked the option this answer pointed at.
            missing.append(q.id)
    return missing
