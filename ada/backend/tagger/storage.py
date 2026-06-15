from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from .models import ProjectRecord, new_id, utc_now_iso


def default_data_dir() -> Path:
    configured = os.environ.get("TAGGER_DATA_DIR")
    if configured:
        return Path(configured)

    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        return base / "charles-tagger"

    return Path.home() / ".charles-tagger"


class TaggerStorage:
    def __init__(self, db_path: Path | None = None):
        data_dir = db_path.parent if db_path is not None else default_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = data_dir
        self.exports_dir = data_dir / "exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or (data_dir / "tagger.sqlite3")
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    template_id TEXT,
                    filing_profile TEXT NOT NULL,
                    taxonomy_year TEXT NOT NULL,
                    taxonomy_entrypoint TEXT NOT NULL,
                    company_snapshot_json TEXT NOT NULL,
                    defaults_json TEXT NOT NULL,
                    fields_json TEXT NOT NULL,
                    facts_json TEXT NOT NULL,
                    validation_runs_json TEXT NOT NULL,
                    exports_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _row_to_project(self, row: sqlite3.Row) -> ProjectRecord:
        return ProjectRecord(
            id=row["id"],
            status=row["status"],
            template_id=row["template_id"],
            filing_profile=row["filing_profile"],
            taxonomy_year=row["taxonomy_year"],
            taxonomy_entrypoint=row["taxonomy_entrypoint"],
            company_snapshot=json.loads(row["company_snapshot_json"]),
            defaults=json.loads(row["defaults_json"]),
            fields=json.loads(row["fields_json"]),
            facts=json.loads(row["facts_json"]),
            validation_runs=json.loads(row["validation_runs_json"]),
            exports=json.loads(row["exports_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _upsert(self, project: ProjectRecord) -> ProjectRecord:
        project.updated_at = utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    id, status, template_id, filing_profile, taxonomy_year, taxonomy_entrypoint,
                    company_snapshot_json, defaults_json, fields_json, facts_json,
                    validation_runs_json, exports_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    template_id=excluded.template_id,
                    filing_profile=excluded.filing_profile,
                    taxonomy_year=excluded.taxonomy_year,
                    taxonomy_entrypoint=excluded.taxonomy_entrypoint,
                    company_snapshot_json=excluded.company_snapshot_json,
                    defaults_json=excluded.defaults_json,
                    fields_json=excluded.fields_json,
                    facts_json=excluded.facts_json,
                    validation_runs_json=excluded.validation_runs_json,
                    exports_json=excluded.exports_json,
                    updated_at=excluded.updated_at
                """,
                (
                    project.id,
                    project.status,
                    project.template_id,
                    project.filing_profile,
                    project.taxonomy_year,
                    project.taxonomy_entrypoint,
                    json.dumps(project.company_snapshot),
                    json.dumps(project.defaults),
                    json.dumps(project.fields),
                    json.dumps(project.facts),
                    json.dumps(project.validation_runs),
                    json.dumps(project.exports),
                    project.created_at,
                    project.updated_at,
                ),
            )
        return project

    def create_project(self, payload: dict[str, Any] | None = None) -> ProjectRecord:
        payload = payload or {}
        project = ProjectRecord(
            id=new_id("proj"),
            status="draft",
            template_id=payload.get("templateId"),
            filing_profile=payload.get("filingProfile", "companies-house-microentity"),
            taxonomy_year=payload.get("taxonomyYear", "2024"),
            taxonomy_entrypoint=payload.get(
                "taxonomyEntrypoint",
                "https://xbrl.frc.org.uk/FRS-102/2024-01-01/FRS-102-2024-01-01.xsd",
            ),
            defaults=payload.get("defaults", {}),
            fields=payload.get("fields", {}),
        )
        return self._upsert(project)

    def list_projects(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC, created_at DESC"
            ).fetchall()
        return [self._row_to_project(row).to_dict() for row in rows]

    def get_project(self, project_id: str) -> ProjectRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_project(row)

    def save_project(self, project: ProjectRecord) -> ProjectRecord:
        return self._upsert(project)

    def patch_defaults(self, project_id: str, defaults_patch: dict[str, Any]) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        project.taxonomy_year = str(defaults_patch.pop("taxonomyYear", project.taxonomy_year))
        project.taxonomy_entrypoint = str(
            defaults_patch.pop("taxonomyEntrypoint", project.taxonomy_entrypoint)
        )
        project.filing_profile = str(defaults_patch.pop("filingProfile", project.filing_profile))
        project.defaults.update(defaults_patch)
        project.status = "setup-complete"
        return self._upsert(project)

    def update_company_snapshot(self, project_id: str, snapshot: dict[str, Any]) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        project.company_snapshot = snapshot
        return self._upsert(project)

    def set_template(self, project_id: str, template_id: str, filing_profile: str) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        project.template_id = template_id
        project.filing_profile = filing_profile
        project.status = "template-loaded"
        return self._upsert(project)

    def patch_field(self, project_id: str, field_id: str, payload: dict[str, Any]) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        field_state = dict(project.fields.get(field_id, {}))
        field_state.update(payload)
        project.fields[field_id] = field_state
        project.status = "data-entered"
        return self._upsert(project)

    def replace_fields(self, project_id: str, fields: dict[str, Any]) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        project.fields = fields
        project.status = "data-entered"
        return self._upsert(project)

    def save_facts(self, project_id: str, facts: dict[str, Any]) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        project.facts = facts
        return self._upsert(project)

    def add_validation_run(self, project_id: str, payload: dict[str, Any]) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        project.validation_runs.append(payload)
        status = payload.get("status")
        sources = {result.get("source") for result in payload.get("results", [])}
        if status == "pass" and "arelle" in sources:
            project.status = "arelle-valid"
        elif status == "pass":
            project.status = "preflight-valid"
        else:
            project.status = "tag-review-needed"
        return self._upsert(project)

    def save_export(self, project_id: str, export_payload: dict[str, Any], content: str) -> ProjectRecord | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        export_id = export_payload["id"]
        export_path = self.exports_dir / f"{export_id}.xhtml"
        export_path.write_text(content, encoding="utf-8")
        export_payload["path"] = str(export_path)
        project.exports.append(export_payload)
        project.status = "exported"
        return self._upsert(project)

    def get_export_path(self, project_id: str, export_id: str) -> Path | None:
        project = self.get_project(project_id)
        if project is None:
            return None
        for export_payload in project.exports:
            if export_payload.get("id") == export_id:
                return Path(export_payload["path"])
        return None
