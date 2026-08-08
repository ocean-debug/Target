"""On-demand best-practice skill catalog (SKILL.md bundles).

The catalog follows the progressive-disclosure pattern used by OpenScience
and Wisp: the planner and capability surfaces only see id/name/description/
lanes; the full SKILL.md text is loaded explicitly when a workflow needs it.

Skills are strategy and quality references, never evidence for the current
task. They never authorize unregistered modules or free-form execution.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable

import yaml
from pydantic import BaseModel, Field

SKILL_FILENAME = "SKILL.md"
_SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


class SkillDescriptor(BaseModel):
    skill_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    version: str = Field(default="1.0.0")
    evidence_lanes: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)
    char_count: int = Field(ge=0)

    @property
    def id(self) -> str:
        return self.skill_id


class SkillHit(BaseModel):
    skill: SkillDescriptor
    score: float = Field(ge=0.0, le=1.0)
    matched_reason: str = Field(default="")


def _tokens(text: str) -> set[str]:
    lowered = (text or "").lower()
    tokens = set(re.findall(r"[a-z0-9]+", lowered))
    tokens.update(re.findall(r"[\u4e00-\u9fff]+", lowered))
    return tokens


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class SkillCatalog:
    """Deterministic, read-only catalog over a skills root directory."""

    def __init__(self, root: Path | str | None = None):
        self.root = Path(root).expanduser().resolve() if root else None
        self._skills: dict[str, SkillDescriptor] = {}
        self._texts: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        self._skills = {}
        self._texts = {}
        if self.root is None or not self.root.is_dir():
            return
        for skill_dir in sorted(self.root.iterdir()):
            if not skill_dir.is_dir():
                continue
            candidate = skill_dir.resolve()
            if not candidate.is_relative_to(self.root):
                continue
            md = skill_dir / SKILL_FILENAME
            if not md.is_file():
                continue
            raw = md.read_bytes()
            text = raw.decode("utf-8")
            parsed = _parse_frontmatter(text)
            if parsed is None:
                continue
            frontmatter, body = parsed
            skill_id = str(frontmatter.get("id") or "")
            if not _SAFE_ID.fullmatch(skill_id) or skill_id != skill_dir.name:
                continue
            name = str(frontmatter.get("name") or "").strip()
            description = str(frontmatter.get("description") or "").strip()
            if not name or not description:
                continue
            lanes = _string_list(frontmatter.get("evidence_lanes"))
            scopes = _string_list(frontmatter.get("scopes"))
            descriptor = SkillDescriptor(
                skill_id=skill_id,
                name=name,
                description=description,
                version=str(frontmatter.get("version") or "1.0.0"),
                evidence_lanes=lanes,
                scopes=scopes,
                path=f"{skill_dir.name}/{SKILL_FILENAME}",
                sha256=_sha256_bytes(raw),
                size_bytes=len(raw),
                char_count=len(body),
            )
            self._skills[skill_id] = descriptor
            self._texts[skill_id] = body

    def list_skills(self) -> list[SkillDescriptor]:
        return [self._skills[key] for key in sorted(self._skills)]

    @property
    def count(self) -> int:
        return len(self._skills)

    def get(self, skill_id: str) -> SkillDescriptor | None:
        return self._skills.get(skill_id)

    def load(self, skill_id: str) -> dict[str, Any] | None:
        descriptor = self._skills.get(skill_id)
        if descriptor is None:
            return None
        return {**descriptor.model_dump(mode="json"), "content": self._texts.get(skill_id, "")}

    def search(
        self,
        query: str = "",
        lanes: Iterable[str] | None = None,
        scopes: Iterable[str] | None = None,
        top_k: int = 5,
    ) -> list[SkillHit]:
        if top_k < 1:
            return []
        lane_set = {str(x).strip().lower() for x in lanes} if lanes is not None else None
        scope_set = {str(x).strip().lower() for x in scopes} if scopes is not None else None
        query_tokens = _tokens(query)
        scored: list[SkillHit] = []
        for descriptor in self.list_skills():
            descriptor_lanes = {x.lower() for x in descriptor.evidence_lanes}
            descriptor_scopes = {x.lower() for x in descriptor.scopes}
            if lane_set is not None and not (descriptor_lanes & lane_set):
                continue
            if scope_set is not None and not (descriptor_scopes & scope_set):
                continue
            haystack = " ".join([
                descriptor.name, descriptor.description,
                " ".join(descriptor.evidence_lanes), " ".join(descriptor.scopes),
            ])
            hay_tokens = _tokens(haystack)
            if not query_tokens:
                score = 1.0 if lane_set or scope_set else 0.0
                reason = "lane/scope filter" if (lane_set or scope_set) else "catalog listing"
            else:
                overlap = len(query_tokens & hay_tokens)
                score = overlap / max(1, len(query_tokens)) if overlap else 0.0
                reason = f"{overlap}/{len(query_tokens)} query tokens matched"
            if score > 0:
                scored.append(SkillHit(skill=descriptor, score=score, matched_reason=reason))
        scored.sort(key=lambda hit: (-hit.score, hit.skill.skill_id))
        return scored[:top_k]

    def public_summary(self) -> dict[str, Any]:
        return {
            "count": len(self._skills),
            "root_configured": bool(self.root and self.root.is_dir()),
            "skills": [
                {
                    "id": skill.skill_id,
                    "name": skill.name,
                    "description": skill.description,
                    "version": skill.version,
                    "evidence_lanes": skill.evidence_lanes,
                    "scopes": skill.scopes,
                    "sha256_short": skill.sha256[:12],
                }
                for skill in self.list_skills()
            ],
        }


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str] | None:
    match = _FRONTMATTER.match(text)
    if match is None:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    body = text[match.end():].strip()
    return data, body


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


class SkillHintBuilder:
    """Compact on-demand hint block for the constrained planner."""

    def __init__(self, catalog: SkillCatalog | None = None, top_k: int = 3):
        self.catalog = catalog
        self.top_k = max(0, min(8, top_k))

    def build(
        self,
        *,
        lanes: Iterable[str] | None = None,
        scopes: Iterable[str] | None = None,
        query: str = "",
    ) -> list[dict[str, Any]]:
        if self.catalog is None or self.top_k == 0:
            return []
        return [
            {
                "id": hit.skill.skill_id,
                "name": hit.skill.name,
                "description": hit.skill.description,
                "evidence_lanes": hit.skill.evidence_lanes,
                "path": hit.skill.path,
            }
            for hit in self.catalog.search(
                query=query, lanes=lanes, scopes=scopes, top_k=self.top_k,
            )
        ]


__all__ = [
    "SkillCatalog", "SkillDescriptor", "SkillHintBuilder", "SkillHit",
    "load_default_catalog",
]


def load_default_catalog() -> SkillCatalog:
    from .settings import PROJECT_ROOT

    return SkillCatalog(PROJECT_ROOT / "skills")
