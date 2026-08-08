"""Research session layer: a conversation view over a durable project.

The session ledger is append-only and never becomes the system of record:
plans, results, evidence, decisions and releases stay in the project store.
Agent answers are bounded summaries of the current durable snapshot; they are
marked source_bound=false and can never create or mutate scientific state.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path
from typing import Any

from pydantic import Field

from .contracts import new_id, utc_now
from .research_contracts import ResearchContract
from .research_service import ResearchProjectNotFound, ResearchProjectService
from .research_runtime import ResearchProjectRuntime


class SessionMessage(ResearchContract):
    message_id: str = Field(pattern=r"^msg-[a-f0-9]{12}$")
    session_id: str = Field(pattern=r"^session-[a-f0-9]{12}$")
    project_id: str = Field(pattern=r"^project-[A-Za-z0-9][A-Za-z0-9._-]*$")
    role: str = Field(pattern="^(user|assistant|system)$")
    text: str = Field(min_length=1, max_length=20000)
    created_at: str = Field(default_factory=utc_now)
    kind: str = Field(default="plain", pattern="^(plain|question|answer|action_suggestion|intervention|intervention_result)$")
    source_bound: bool = False
    references: list[str] = Field(default_factory=list)
    content_sha256: str = Field(default="")

    @property
    def canonical(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "text": self.text,
            "created_at": self.created_at,
            "references": self.references,
        }

    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(self.canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()


class ResearchSession(ResearchContract):
    session_id: str = Field(pattern=r"^session-[a-f0-9]{12}$")
    project_id: str = Field(pattern=r"^project-[A-Za-z0-9][A-Za-z0-9._-]*$")
    title: str = Field(min_length=1, max_length=200)
    created_at: str = Field(default_factory=utc_now)
    status: str = Field(default="open", pattern="^(open|archived)$")


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ResearchSessionStore:
    """Append-only JSONL session ledger inside one project directory."""

    def __init__(self, projects_dir: Path | str):
        self.projects_dir = Path(projects_dir).expanduser().resolve()
        self._lock = threading.RLock()

    def _project_dir(self, project_id: str) -> Path:
        if not _SAFE_COMPONENT.fullmatch(project_id):
            raise ValueError(f"unsafe project_id: {project_id!r}")
        project_dir = (self.projects_dir / project_id).resolve()
        if not project_dir.is_relative_to(self.projects_dir):
            raise ValueError("project directory escapes projects root")
        return project_dir

    def _sessions_dir(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "sessions"

    @staticmethod
    def _write_line(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    def create_session(self, project_id: str, title: str) -> ResearchSession:
        if not title.strip():
            raise ValueError("session title is required")
        session = ResearchSession(
            session_id=new_id("session"),
            project_id=project_id,
            title=title.strip()[:200],
        )
        with self._lock:
            self._write_line(self._sessions_dir(project_id) / "index.jsonl", session.model_dump(mode="json"))
        return session

    def append_message(self, project_id: str, message: SessionMessage) -> SessionMessage:
        if not message.content_sha256:
            message.content_sha256 = message.digest()
        if message.content_sha256 != message.digest():
            raise ValueError("session message digest mismatch")
        with self._lock:
            sessions_dir = self._sessions_dir(project_id)
            self._write_line(sessions_dir / f"{message.session_id}.jsonl", message.model_dump(mode="json"))
        return message

    def list_sessions(self, project_id: str) -> list[ResearchSession]:
        index_path = self._sessions_dir(project_id) / "index.jsonl"
        if not index_path.is_file():
            return []
        rows: list[ResearchSession] = []
        for line in index_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("project_id") == project_id:
                rows.append(ResearchSession.model_validate(row))
        return rows

    def read_session(self, project_id: str, session_id: str) -> ResearchSession:
        for row in self.list_sessions(project_id):
            if row.session_id == session_id:
                return row
        raise ResearchProjectNotFound(f"session {session_id} not found for project {project_id}")

    def read_messages(self, project_id: str, session_id: str) -> list[SessionMessage]:
        path = self._sessions_dir(project_id) / f"{session_id}.jsonl"
        if not path.is_file():
            return []
        messages: list[SessionMessage] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            message = SessionMessage.model_validate(row)
            if message.content_sha256 and message.content_sha256 != message.digest():
                raise ValueError(f"session message tampered: {message.message_id}")
            messages.append(message)
        return messages


class ResearchSessionService:
    """Product-facing session operations over a durable project service."""

    def __init__(self, runtime: ResearchProjectRuntime):
        self.runtime = runtime
        self.projects_service = ResearchProjectService(runtime)
        self.store = ResearchSessionStore(runtime.projects_dir)

    def create(self, project_id: str, title: str | None = None) -> dict[str, Any]:
        self.projects_service.snapshot(project_id)  # 404 if project missing
        session = self.store.create_session(project_id, title or "研究对话")
        return {"session": session.model_dump(mode="json"), "messages": []}

    def list(self, project_id: str) -> dict[str, Any]:
        self.projects_service.snapshot(project_id)
        sessions = self.store.list_sessions(project_id)
        return {
            "project_id": project_id,
            "sessions": [
                {
                    **session.model_dump(mode="json"),
                    "message_count": len(self.store.read_messages(project_id, session.session_id)),
                }
                for session in sessions
            ],
        }

    def messages(self, project_id: str, session_id: str) -> dict[str, Any]:
        self.projects_service.snapshot(project_id)
        self.store.read_session(project_id, session_id)
        return {
            "project_id": project_id,
            "session_id": session_id,
            "messages": [row.model_dump(mode="json") for row in self.store.read_messages(project_id, session_id)],
        }

    def post_message(
        self,
        project_id: str,
        session_id: str,
        text: str,
        *,
        ask_agent: bool = False,
        actor: str = "researcher",
    ) -> dict[str, Any]:
        if not text.strip():
            raise ValueError("message text is required")
        if not actor.strip():
            raise ValueError("actor is required")
        self.projects_service.snapshot(project_id)  # 404 if project missing
        self.store.read_session(project_id, session_id)
        user_message = self.store.append_message(
            project_id,
            SessionMessage(
                message_id=new_id("msg"),
                session_id=session_id,
                project_id=project_id,
                role="user",
                text=text.strip(),
                kind="question" if ask_agent else "plain",
                source_bound=False,
            ),
        )
        messages = [user_message.model_dump(mode="json")]
        if ask_agent:
            messages.append(self.answer(project_id, session_id, actor=actor))
        return {"project_id": project_id, "session_id": session_id, "messages": messages}


    def intervene(
        self,
        project_id: str,
        session_id: str,
        *,
        action: str,
        rationale: str,
        actor: str = "researcher",
        target_id: str | None = None,
        approve: bool | None = None,
        snapshot_digest: str | None = None,
    ) -> dict[str, Any]:
        """Execute one structured control-plane action and record it in the session.

        Only explicit, deterministic actions are routed here (accept_checkpoint,
        decide_repair, decide_fork). Natural-language text is carried as the
        decision rationale; the decision itself is written by
        ResearchProjectService into the durable project ledger, which remains
        the system of record. The session only records the instruction and the
        outcome view.
        """
        if not action.strip():
            raise ValueError("action is required")
        if not rationale.strip():
            raise ValueError("rationale is required")
        if not actor.strip():
            raise ValueError("actor is required")
        self.projects_service.snapshot(project_id)  # 404 if project missing
        self.store.read_session(project_id, session_id)

        if action == "accept_checkpoint":
            if not target_id:
                raise ValueError("target_id is required for accept_checkpoint")
            decided = self.projects_service.accept_checkpoint(
                project_id=project_id,
                target_id=target_id,
                actor=actor,
                rationale=rationale,
            )
        elif action == "decide_repair":
            if not target_id or not snapshot_digest or not isinstance(approve, bool):
                raise ValueError(
                    "target_id, snapshot_digest and boolean approve are required for decide_repair"
                )
            decided = self.projects_service.decide_repair(
                project_id=project_id,
                repair_request_id=target_id,
                trigger_snapshot_digest=snapshot_digest,
                approve=approve,
                actor=actor,
                rationale=rationale,
            )
        elif action == "decide_fork":
            if not target_id or not isinstance(approve, bool):
                raise ValueError("target_id and boolean approve are required for decide_fork")
            decided = self.projects_service.decide_fork(
                project_id=project_id,
                branch_id=target_id,
                approve=approve,
                actor=actor,
                rationale=rationale,
            )
        else:
            raise ValueError(f"unsupported intervention action: {action!r}")

        decision = decided["decision"]
        decision_id = str(decision.get("decision_id") or "")
        decision_action = str(decision.get("action") or "decided")
        verb = "批准" if decision_action == "accept" else "拒绝" if decision_action == "reject" else decision_action
        user_message = self.store.append_message(
            project_id,
            SessionMessage(
                message_id=new_id("msg"),
                session_id=session_id,
                project_id=project_id,
                role="user",
                text=rationale,
                kind="intervention",
                references=[f"project:{project_id}"],
                source_bound=False,
            ),
        )
        result_text = (
            f"已记录决策 {decision_id}：{verb}（{decision_action}），"
            f"目标 {', '.join(str(row) for row in decision.get('target_ids') or [])}；"
            f"由 {actor} 提交，审批已写入项目账本。"
        )
        result_message = self.store.append_message(
            project_id,
            SessionMessage(
                message_id=new_id("msg"),
                session_id=session_id,
                project_id=project_id,
                role="system",
                text=result_text,
                kind="intervention_result",
                references=[f"project:{project_id}", f"decision:{decision_id}"],
                source_bound=False,
            ),
        )
        return {
            "project_id": project_id,
            "session_id": session_id,
            "messages": [
                user_message.model_dump(mode="json"),
                result_message.model_dump(mode="json"),
            ],
            "decision": decision,
        }
    def answer(self, project_id: str, session_id: str, *, actor: str = "researcher") -> dict[str, Any]:
        """Produce a bounded, deterministic answer from the durable snapshot.

        The answer is a summary view; it is explicitly not source-bound evidence
        and never mutates project state.
        """
        snapshot = self.projects_service.snapshot(project_id)
        self.store.read_session(project_id, session_id)
        state = snapshot.get("state") or {}
        plan = snapshot.get("plan") or {}
        items = plan.get("items") or []
        status = state.get("status") or "unknown"
        checkpoint = state.get("checkpoint_kind")
        terminal_reason = state.get("terminal_reason")
        next_actions = snapshot.get("next_actions") or []
        recent_events = (snapshot.get("events") or [])[-5:]
        artifact_count = len(snapshot.get("artifacts") or [])

        item_lines = [
            f"- {item.get('item_id')} [{item.get('module')}] required={bool(item.get('required'))}"
            for item in items
        ]
        event_lines = [
            f"- #{row.get('sequence')} {row.get('event_type')}: {row.get('status')}"
            for row in recent_events
        ]
        action_lines = [
            f"- {row.get('action')} {row.get('project_id', '')}" for row in next_actions
        ]
        parts = [f"项目 {project_id} 当前状态：{status}。"]
        if checkpoint:
            parts.append(f"等待人工审批：{checkpoint}。")
        if terminal_reason:
            parts.append(f"终止原因：{terminal_reason}。")
        if item_lines:
            parts.append("执行计划：\n" + "\n".join(item_lines))
        if event_lines:
            parts.append("最近事件：\n" + "\n".join(event_lines))
        if action_lines:
            parts.append("建议的下一步：\n" + "\n".join(action_lines))
        parts.append(
            f"已登记不可变产物 {artifact_count} 个。"
            "以上为项目快照的确定性摘要（source_bound=false），"
            "不代表新的科学证据；审批/回退/修复请使用工作台对应操作。"
        )
        return self.store.append_message(
            project_id,
            SessionMessage(
                message_id=new_id("msg"),
                session_id=session_id,
                project_id=project_id,
                role="assistant",
                text="\n\n".join(parts),
                kind="answer",
                references=[f"project:{project_id}"],
                source_bound=False,
            ),
        ).model_dump(mode="json")


__all__ = [
    "ResearchSession",
    "ResearchSessionService",
    "ResearchSessionStore",
    "SessionMessage",
]