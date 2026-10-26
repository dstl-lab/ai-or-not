"""Where things live on disk, and loading of the site configuration."""

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ConfigError(Exception):
    """A config file is missing or malformed. The message says how to fix it."""


@dataclass(frozen=True)
class Paths:
    config_dir: Path
    data_dir: Path
    mirror_dir: Path
    web_dir: Path

    @classmethod
    def default(cls):
        data_dir = Path(os.environ.get("AIORNOT_DATA_DIR", ROOT / "data"))
        return cls(
            config_dir=ROOT / "config",
            data_dir=data_dir,
            mirror_dir=ROOT / "mirror",
            web_dir=ROOT / "web",
        )

    @property
    def db_file(self):
        return self.data_dir / "study.db"

    @property
    def sheets_file(self):
        return self.data_dir / "sheets.json"


@dataclass(frozen=True)
class Site:
    id: str
    title: str
    url: str
    repo: str
    branch: str
    path: str
    entry: str
    award: str | None
    commit: str | None


@dataclass(frozen=True)
class SiteConfig:
    pool: dict[str, Site]
    study: list[Site]  # active projects available for assignment
    sites_per_session: int = 10

    @property
    def version(self):
        """Changes when the active projects, pinned commits, or session size change."""
        key = json.dumps([self.sites_per_session, [[s.id, s.commit] for s in self.study]])
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    def position(self, site_id):
        """1-based position of a study site, or None if it isn't in the study."""
        for i, site in enumerate(self.study, start=1):
            if site.id == site_id:
                return i
        return None


def read_json(path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise ConfigError(f"{path} is missing") from None
    except json.JSONDecodeError as err:
        raise ConfigError(f"{path} is not valid JSON: {err}") from None


def load_sites(paths):
    raw = read_json(paths.config_dir / "sites.json")
    count = raw.get("sites_per_session", 10)
    if type(count) is not int or not 1 <= count <= 10:
        raise ConfigError("sites.json: sites_per_session must be an integer from 1 to 10")
    pool = {}
    for entry in raw.get("pool", []):
        try:
            site = Site(**entry)
        except TypeError as err:
            raise ConfigError(f"sites.json: bad site entry {entry.get('id')!r}: {err}") from None
        if site.id in pool:
            raise ConfigError(f"sites.json: duplicate site id {site.id!r}")
        pool[site.id] = site

    study_ids = raw.get("study_sites", [])
    if not study_ids:
        raise ConfigError("sites.json: study_sites is empty")
    if len(set(study_ids)) != len(study_ids):
        raise ConfigError("sites.json: study_sites lists a site more than once")
    unknown = [sid for sid in study_ids if sid not in pool]
    if unknown:
        raise ConfigError(f"sites.json: study_sites has ids not in the pool: {unknown}")
    return SiteConfig(pool=pool, study=[pool[sid] for sid in study_ids], sites_per_session=count)
