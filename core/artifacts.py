from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ARTIFACT_ROOT = Path("artifacts")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "dataset"


def dataset_id_for(metadata: dict[str, Any]) -> str:
    stem = slugify(str(metadata.get("source_file") or "dataset"))
    digest = str(metadata.get("file_sha256") or "")[:12] or "nohash"
    return f"{stem}_{digest}"


class ArtifactStore:
    def __init__(self, root: Path | str = ARTIFACT_ROOT):
        self.root = Path(root)

    def ensure(self) -> None:
        for folder in [
            "datasets",
            "metadata",
            "sessions",
            "turns",
            "analysis_outputs",
            "plans",
            "charts",
            "memory",
            "traces",
            "notebooks",
            "logs",
        ]:
            (self.root / folder).mkdir(parents=True, exist_ok=True)

    def path_for(self, artifact_type: str, artifact_id: str, suffix: str = ".json") -> Path:
        self.ensure()
        folder = self.root / artifact_type
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{artifact_id}{suffix}"

    def write_json(self, artifact_type: str, artifact_id: str, payload: Any) -> Path:
        path = self.path_for(artifact_type, artifact_id)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def read_json(self, artifact_type: str, artifact_id: str) -> Any:
        return json.loads(self.path_for(artifact_type, artifact_id).read_text(encoding="utf-8"))

    def write_bytes(
        self,
        artifact_type: str,
        artifact_id: str,
        payload: bytes,
        suffix: str = ".bin",
    ) -> Path:
        path = self.path_for(artifact_type, artifact_id, suffix=suffix)
        path.write_bytes(payload)
        return path

    def read_bytes(self, artifact_type: str, artifact_id: str, suffix: str = ".bin") -> bytes:
        return self.path_for(artifact_type, artifact_id, suffix=suffix).read_bytes()
