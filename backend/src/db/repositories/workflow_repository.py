from __future__ import annotations

import json

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.db.models.workflow_node_run import WorkflowNodeRun
from src.db.models.workflow_run import WorkflowRun


class WorkflowRepository:
    """Persistence operations for workflow runs and node runs."""

    def __init__(self, db: Session):
        self.db = db

    # Runs
    def create_run(self, run_id: str, project_id: str, *, status: str = "queued") -> WorkflowRun:
        run = WorkflowRun(run_id=run_id, project_id=project_id, status=status)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def set_run_status(self, run_id: str, status: str) -> WorkflowRun:
        run = self.db.get(WorkflowRun, run_id)
        if run is None:
            raise ValueError(f"WorkflowRun not found: {run_id}")
        run.status = status
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    # Node runs
    def create_node_run(
        self,
        node_run_id: str,
        run_id: str,
        node_name: str,
        *,
        attempt: int = 1,
        status: str = "queued",
        output_payload: dict | None = None,
    ) -> WorkflowNodeRun:
        node_run = WorkflowNodeRun(
            node_run_id=node_run_id,
            run_id=run_id,
            node_name=node_name,
            attempt=attempt,
            status=status,
            output_json=json.dumps(output_payload or {}, ensure_ascii=False),
        )
        self.db.add(node_run)
        self.db.commit()
        self.db.refresh(node_run)
        return node_run

    def set_node_run_status(self, node_run_id: str, status: str) -> WorkflowNodeRun:
        node_run = self.db.get(WorkflowNodeRun, node_run_id)
        if node_run is None:
            raise ValueError(f"WorkflowNodeRun not found: {node_run_id}")
        node_run.status = status
        self.db.add(node_run)
        self.db.commit()
        self.db.refresh(node_run)
        return node_run

    def set_node_run_output(self, node_run_id: str, output_payload: dict) -> WorkflowNodeRun:
        node_run = self.db.get(WorkflowNodeRun, node_run_id)
        if node_run is None:
            raise ValueError(f"WorkflowNodeRun not found: {node_run_id}")
        node_run.output_json = json.dumps(output_payload, ensure_ascii=False)
        self.db.add(node_run)
        self.db.commit()
        self.db.refresh(node_run)
        return node_run

    def get_latest_node_output(self, project_id: str, node_name: str) -> dict | None:
        stmt: Select = (
            select(WorkflowNodeRun.output_json)
            .join(WorkflowRun, WorkflowRun.run_id == WorkflowNodeRun.run_id)
            .where(WorkflowRun.project_id == project_id)
            .where(WorkflowNodeRun.node_name == node_name)
            .order_by(WorkflowRun.created_at.desc())
            .limit(1)
        )
        row = self.db.execute(stmt).first()
        if not row:
            return None
        try:
            return json.loads(row[0] or "{}")
        except json.JSONDecodeError:
            return None
