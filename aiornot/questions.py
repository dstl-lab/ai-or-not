"""The question set: loading, validating, and checking answers against it.

`config/questions.json` has three sections:

    background  asked once, before the first website
    questions   asked about every website (the right-hand panel)
    closing     asked once, after the last website

Six question types are supported, all closed-ended:

    boolean  two choices, stored as true/false
    single   pick one option (multiple choice)
    multi    pick any number of options (multi-select); `min_selected` / `max_selected`
             set the limits, and an option with `"exclusive": true` (e.g. "None")
             can't be combined with others
    scale    an integer from `min` to `max` (e.g. 1-5), with optional end labels
    grid     one `min`-`max` scale per row, stored as {row: number}; with `allow_na`,
             a row may be answered "na" instead
    marks    the participant clicks spots on the website itself, as many as they like;
             stored as a list of marks (see MARK_FIELDS), or "none" when they tick
             `none_label` ("Nothing looks AI-generated") instead

A `single` question may use `options_from: "<multi question id>"` instead of
`options`, in which case it only offers what the participant picked there.
`options` (and a grid's `rows`) may also be the name of a shared list in the
top-level `option_lists`, with `extra_options` appended after it.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field

from .config import ConfigError, read_json

TYPES = {"boolean", "single", "multi", "scale", "grid", "marks"}
SECTIONS = ("background", "questions", "closing")
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
NA = "na"
# Background and closing answers live in the responses table under these pseudo site ids.
SURVEY_KEYS = {"background": "_background", "closing": "_closing"}

# What the study page records about each spot a participant marks on a website.
MARK_FIELDS = {
    "id": str,          # short random id, unique within the site's marks
    "page": str,        # page within the site ("" = its first page)
    "selector": str,    # CSS path to the clicked element (the sites are frozen, so it's stable)
    "tag": str,         # element name, e.g. "rect", "h2", "p"
    "kind": str,        # plain-language type: "Chart or graphic", "Heading", "Text", ...
    "text": str,        # first words of the element's text, if any
    "x": (int, float),  # click position on the page, in CSS pixels from the top-left
    "y": (int, float),
    "box": dict,        # the element's {x, y, w, h} on the page
    "scroll_y": (int, float),
    "viewport_w": (int, float),
    "viewport_h": (int, float),
    "created_at": str,
}
MAX_MARKS = 200


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    exclusive: bool = False


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
    max_selected: int | None = None
    min: int = 1
    max: int = 5
    min_label: str | None = None
    max_label: str | None = None
    true_label: str = "Yes"
    false_label: str = "No"
    rows: tuple[Option, ...] = ()
    allow_na: bool = False
    none_label: str | None = None

    def option_values(self, questions_by_id):
        source = questions_by_id[self.options_from] if self.options_from else self
        return [o.value for o in source.options]

    def to_client(self, questions_by_id):
        data = {k: v for k, v in self.__dict__.items() if v is not None}
        if self.options_from:
            data["options"] = questions_by_id[self.options_from].options
        data["options"] = [o.__dict__ for o in data.get("options", ())]
        data["rows"] = [o.__dict__ for o in self.rows]
        return data


@dataclass(frozen=True)
class QuestionSet:
    version_label: str
    questions: list[Question]  # asked about every website
    raw_hash: str = field(repr=False)
    background: list[Question] = field(default_factory=list)
    closing: list[Question] = field(default_factory=list)

    @property
    def by_id(self):
        return {q.id: q for q in self.background + self.questions + self.closing}

    @property
    def version(self):
        """Label plus content hash, so an edited file is never mistaken for the old one."""
        return f"{self.version_label}+{self.raw_hash}"

    def section(self, name):
        return {"background": self.background, "questions": self.questions,
                "closing": self.closing}[name]

    def to_client(self, section="questions"):
        by_id = self.by_id
        return [q.to_client(by_id) for q in self.section(section)]


def parse_option(raw, qid):
    if isinstance(raw, str):
        return Option(value=raw, label=raw)
    if isinstance(raw, dict) and "value" in raw:
        return Option(value=str(raw["value"]), label=str(raw.get("label", raw["value"])),
                      exclusive=bool(raw.get("exclusive", False)))
    raise ConfigError(f"questions.json: question {qid!r} has a bad option: {raw!r}")


def parse_options(raw, qid, lists, key):
    """A list of options, or the name of a shared list in `option_lists`."""
    if isinstance(raw, str):
        if raw not in lists:
            raise ConfigError(f"questions.json: {qid!r}: {key} names unknown list {raw!r}")
        raw = lists[raw]
    if not isinstance(raw, list):
        raise ConfigError(f"questions.json: {qid!r}: {key} must be a list or a list name")
    return tuple(parse_option(o, qid) for o in raw)


def parse_question(item, lists, seen):
    qid = item.get("id")
    if not isinstance(qid, str) or not ID_PATTERN.match(qid):
        raise ConfigError(f"questions.json: id {qid!r} must be lowercase letters, digits and _")
    if qid in seen:
        raise ConfigError(f"questions.json: duplicate question id {qid!r}")
    if item.get("type") not in TYPES:
        raise ConfigError(
            f"questions.json: question {qid!r} has type {item.get('type')!r}; "
            f"use one of {sorted(TYPES)}"
        )
    allowed = set(Question.__dataclass_fields__) | {"extra_options"}
    unknown = set(item) - allowed
    if unknown:
        raise ConfigError(f"questions.json: question {qid!r} has unknown keys {sorted(unknown)}")
    fields = {k: v for k, v in item.items() if k in Question.__dataclass_fields__}
    fields["options"] = (parse_options(item.get("options", []), qid, lists, "options")
                         + parse_options(item.get("extra_options", []), qid, lists, "extra_options"))
    fields["rows"] = parse_options(item.get("rows", []), qid, lists, "rows")
    return Question(**fields)


def validate_question(q, section_seen):
    qid = q.id
    if q.type in {"single", "multi"}:
        if q.options_from:
            source = section_seen.get(q.options_from)
            if q.type != "single" or source is None or source.type != "multi":
                raise ConfigError(
                    f"questions.json: {qid!r}: options_from must name an earlier multi "
                    "question in the same section"
                )
        elif not q.options:
            raise ConfigError(f"questions.json: question {qid!r} needs options")
        values = [o.value for o in q.options]
        if len(set(values)) != len(values):
            raise ConfigError(f"questions.json: question {qid!r} repeats an option value")
    if q.type == "multi" and q.max_selected is not None and not (
            isinstance(q.max_selected, int) and q.min_selected <= q.max_selected):
        raise ConfigError(f"questions.json: {qid!r}: max_selected must be >= min_selected")
    if q.type in {"scale", "grid"} and not (
            isinstance(q.min, int) and isinstance(q.max, int) and q.min < q.max):
        raise ConfigError(f"questions.json: {q.type} {qid!r} needs integer min < max")
    if q.type == "grid":
        values = [r.value for r in q.rows]
        if not values or len(set(values)) != len(values):
            raise ConfigError(f"questions.json: grid {qid!r} needs rows with distinct values")


def load_questions(paths):
    path = paths.config_dir / "questions.json"
    raw = read_json(path)
    raw_hash = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()[:8]
    lists = raw.get("option_lists", {})
    seen = {}
    sections = {}
    for name in SECTIONS:
        section_seen = {}
        for item in raw.get(name, []):
            q = parse_question(item, lists, seen)
            validate_question(q, section_seen)
            seen[q.id] = section_seen[q.id] = q
        sections[name] = list(section_seen.values())

    if not sections["questions"]:
        raise ConfigError("questions.json: no per-website questions defined")
    return QuestionSet(
        version_label=str(raw.get("version", "unversioned")),
        questions=sections["questions"],
        background=sections["background"],
        closing=sections["closing"],
        raw_hash=raw_hash,
    )


class AnswerError(ValueError):
    pass


def is_blank(value):
    return value is None or value == [] or value == "" or value == {}


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def check_answer(question, value, questions_by_id):
    """Raise AnswerError if `value` isn't a well-formed answer to `question`."""
    t = question.type
    if t == "boolean":
        ok = isinstance(value, bool)
    elif t == "scale":
        ok = is_int(value) and question.min <= value <= question.max
    elif t == "single":
        ok = isinstance(value, str) and value in question.option_values(questions_by_id)
    elif t == "grid":
        rows = {r.value for r in question.rows}
        ok = isinstance(value, dict) and all(
            k in rows and ((is_int(v) and question.min <= v <= question.max)
                           or (question.allow_na and v == NA))
            for k, v in value.items()
        )
    elif t == "marks":
        ok = (value == NONE_MARKED and question.none_label is not None) or valid_marks(value)
    else:  # multi
        allowed = set(question.option_values(questions_by_id))
        exclusive = {o.value for o in question.options if o.exclusive}
        ok = (
            isinstance(value, list)
            and all(isinstance(v, str) and v in allowed for v in value)
            and len(set(value)) == len(value)
            and (question.max_selected is None or len(value) <= question.max_selected)
            and not (len(value) > 1 and exclusive & set(value))
        )
    if not ok:
        raise AnswerError(f"invalid answer for {question.id!r}: {value!r}")


NONE_MARKED = "none"


def valid_marks(value):
    if not isinstance(value, list) or not 0 < len(value) <= MAX_MARKS:
        return False
    for mark in value:
        if not isinstance(mark, dict) or set(mark) - set(MARK_FIELDS):
            return False
        if not all(isinstance(mark.get(k), str) and mark[k] for k in ("id", "selector")):
            return False
        for key, kind in MARK_FIELDS.items():
            v = mark.get(key)
            if v is None:
                continue
            if isinstance(v, bool) or not isinstance(v, kind):
                return False
            if isinstance(v, str) and len(v) > 2000:
                return False
        box = mark.get("box")
        if box is not None and not all(
                is_int(box.get(k)) or isinstance(box.get(k), float) for k in ("x", "y", "w", "h")):
            return False
    return len({m["id"] for m in value}) == len(value)


def missing_answers(questions, answers):
    """Ids of required questions (from the list given) that are unanswered or no longer valid."""
    missing = []
    for q in questions:
        value = answers.get(q.id)
        if is_blank(value):
            if q.required:
                missing.append(q.id)
            continue
        if q.type == "multi" and len(value) < q.min_selected:
            missing.append(q.id)
        elif q.type == "grid" and any(r.value not in value for r in q.rows):
            missing.append(q.id)
        elif q.options_from and value not in answers.get(q.options_from, []):
            # The participant un-ticked the option this answer pointed at.
            missing.append(q.id)
    return missing
