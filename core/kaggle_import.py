from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from dotenv import load_dotenv

from core.artifacts import slugify


KAGGLE_DOWNLOAD_DIR = Path("artifacts") / "kaggle_downloads"

logger = logging.getLogger(__name__)


def normalize_kaggle_dataset_ref(value: str) -> str:
    dataset_ref = value.strip()
    if dataset_ref.startswith("https://www.kaggle.com/datasets/"):
        dataset_ref = dataset_ref.removeprefix("https://www.kaggle.com/datasets/")
    elif dataset_ref.startswith("http://www.kaggle.com/datasets/"):
        dataset_ref = dataset_ref.removeprefix("http://www.kaggle.com/datasets/")
    dataset_ref = dataset_ref.strip("/")
    parts = dataset_ref.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError("Use a Kaggle dataset reference like `owner/dataset-slug`.")
    return "/".join(parts[:3])


def kaggle_download_folder(dataset_ref: str, download_root: Path | None = None) -> Path:
    root = download_root or KAGGLE_DOWNLOAD_DIR
    return root / slugify(dataset_ref.replace("/", "_"))


def kaggle_api() -> Any:
    load_dotenv()
    _apply_kaggle_api_token_env()
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError as exc:
        raise RuntimeError(
            "The `kaggle` package is not installed. Run "
            "`./.venv/Scripts/python.exe -m pip install -r requirements.txt`."
        ) from exc

    api = KaggleApi()
    try:
        api.authenticate()
    except SystemExit as exc:
        raise RuntimeError(
            "Kaggle authentication is not configured. Use `kaggle auth login`, "
            "place `kaggle.json` in your Kaggle config folder, or set "
            "`KAGGLE_USERNAME` and `KAGGLE_KEY` in `.env`."
        ) from exc
    return api


def _apply_kaggle_api_token_env() -> None:
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        return

    token = os.environ.get("KAGGLE_API_TOKEN", "").strip()
    if not token:
        return

    try:
        payload = json.loads(token)
    except json.JSONDecodeError:
        parts = token.split(":", 1)
        if len(parts) == 2:
            os.environ.setdefault("KAGGLE_USERNAME", parts[0].strip())
            os.environ.setdefault("KAGGLE_KEY", parts[1].strip())
        return

    if isinstance(payload, dict):
        username = str(payload.get("username") or "").strip()
        key = str(payload.get("key") or "").strip()
        if username and key:
            os.environ.setdefault("KAGGLE_USERNAME", username)
            os.environ.setdefault("KAGGLE_KEY", key)


def list_kaggle_files(api: Any, dataset_ref: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        response = api.dataset_list_files(
            dataset_ref,
            page_token=page_token,
            page_size=100,
        )
        if getattr(response, "error_message", None):
            raise RuntimeError(response.error_message)

        for dataset_file in getattr(response, "files", []) or []:
            files.append(
                {
                    "name": getattr(dataset_file, "name", ""),
                    "size": getattr(dataset_file, "total_bytes", None),
                    "creation_date": getattr(dataset_file, "creation_date", None),
                }
            )

        page_token = getattr(response, "next_page_token", None)
        if not page_token:
            return files


def choose_kaggle_csv_file(files: list[dict[str, Any]], requested_file: str) -> str:
    csv_files = [
        str(file_info["name"])
        for file_info in files
        if str(file_info.get("name", "")).lower().endswith(".csv")
    ]
    zipped_csv_files = [
        str(file_info["name"])
        for file_info in files
        if str(file_info.get("name", "")).lower().endswith(".csv.zip")
    ]
    candidate_files = csv_files + zipped_csv_files
    if requested_file:
        matching_file = next(
            (
                filename
                for filename in candidate_files
                if (
                    filename == requested_file
                    or Path(filename).name == requested_file
                    or filename.removesuffix(".zip") == requested_file
                    or Path(filename.removesuffix(".zip")).name == requested_file
                )
            ),
            None,
        )
        if not matching_file:
            raise ValueError(f"`{requested_file}` was not found as a CSV or zipped CSV in this Kaggle dataset.")
        return matching_file

    if not candidate_files:
        raise ValueError("This Kaggle dataset does not expose any CSV or zipped CSV files.")
    return candidate_files[0]


def normalize_kaggle_member_path(value: str) -> str:
    return value.strip().replace("\\", "/").strip("/")


def kaggle_selected_file_candidates(selected_file: str) -> list[str]:
    selected_path = normalize_kaggle_member_path(selected_file)
    unzipped_path = selected_path.removesuffix(".zip")
    candidates = [
        selected_path,
        PurePosixPath(selected_path).name,
        unzipped_path,
        PurePosixPath(unzipped_path).name,
    ]
    return [candidate for candidate in dict.fromkeys(candidates) if candidate]


def safe_kaggle_zip_destination(extract_root: Path, member_name: str) -> Path | None:
    normalized_name = member_name.replace("\\", "/")
    member_path = PurePosixPath(normalized_name)
    if (
        not normalized_name.strip()
        or member_path.is_absolute()
        or any(part in {"", ".", ".."} for part in member_path.parts)
    ):
        return None

    extract_root = extract_root.resolve()
    destination = (extract_root / Path(*member_path.parts)).resolve()
    try:
        destination.relative_to(extract_root)
    except ValueError:
        return None
    return destination


def extract_zip_files(download_dir: Path) -> list[Path]:
    extracted_files: list[Path] = []
    for zip_path in [path for path in download_dir.rglob("*.zip") if path.is_file()]:
        extract_root = zip_path.with_name(f"{zip_path.name}_extracted")
        extract_root.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    destination = safe_kaggle_zip_destination(extract_root, member.filename)
                    if destination is None:
                        logger.warning(
                            "Skipped unsafe path in Kaggle zip: zip=%s member=%s",
                            zip_path,
                            member.filename,
                        )
                        continue
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, destination.open("wb") as target:
                        shutil.copyfileobj(source, target)
                    extracted_files.append(destination)
        except zipfile.BadZipFile:
            logger.warning("Downloaded Kaggle zip could not be extracted: %s", zip_path)
    return extracted_files


def find_downloaded_kaggle_csv(download_dir: Path, selected_file: str) -> Path | None:
    extracted_files = extract_zip_files(download_dir)
    downloaded_files = [path for path in download_dir.rglob("*") if path.is_file()]
    csv_files = [path for path in downloaded_files if path.suffix.lower() == ".csv"]
    expected_names = set(kaggle_selected_file_candidates(selected_file))

    for path in downloaded_files + extracted_files:
        relative = path.relative_to(download_dir).as_posix()
        if path.suffix.lower() != ".csv":
            continue
        if path.name in expected_names or relative in expected_names:
            return path
        if any(relative.endswith(f"/{expected_name}") for expected_name in expected_names):
            return path

    if len(csv_files) == 1:
        return csv_files[0]

    if csv_files:
        requested_stem = Path(selected_file.removesuffix(".zip")).stem.lower()
        return next(
            (
                path
                for path in csv_files
                if path.stem.lower() == requested_stem
            ),
            csv_files[0],
        )

    return None


def kaggle_description_from_metadata(metadata: dict[str, Any], dataset_ref: str) -> str:
    title = str(metadata.get("title") or "").strip()
    subtitle = str(metadata.get("subtitle") or "").strip()
    description = str(metadata.get("description") or "").strip()
    licenses = metadata.get("licenses") or []
    license_names = [
        str(license_info.get("name", "")).strip()
        for license_info in licenses
        if isinstance(license_info, dict) and license_info.get("name")
    ]

    parts = [f"Kaggle dataset: {dataset_ref}"]
    if title:
        parts.append(f"Title: {title}")
    if subtitle:
        parts.append(f"Subtitle: {subtitle}")
    if description:
        parts.append(description)
    if license_names:
        parts.append(f"License: {', '.join(license_names)}")
    return "\n\n".join(parts)


def fetch_kaggle_dataset(
    dataset_ref_input: str,
    requested_file: str = "",
    download_root: Path | None = None,
) -> dict[str, Any]:
    dataset_ref = normalize_kaggle_dataset_ref(dataset_ref_input)
    api = kaggle_api()
    files = list_kaggle_files(api, dataset_ref)
    selected_file = choose_kaggle_csv_file(files, requested_file.strip())

    download_dir = kaggle_download_folder(dataset_ref, download_root=download_root)
    if download_dir.exists():
        shutil.rmtree(download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as metadata_temp_dir:
        metadata_path = Path(api.dataset_metadata(dataset_ref, metadata_temp_dir))
        kaggle_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    api.dataset_download_file(
        dataset_ref,
        selected_file,
        path=str(download_dir),
        force=True,
        quiet=True,
    )

    selected_path = find_downloaded_kaggle_csv(download_dir, selected_file)
    if selected_path is None:
        raise FileNotFoundError(f"Kaggle download completed, but `{selected_file}` was not found.")

    raw_bytes = selected_path.read_bytes()
    source_filename = f"kaggle_{dataset_ref.replace('/', '_')}_{selected_path.name}"
    return {
        "dataset_ref": dataset_ref,
        "selected_file": selected_file,
        "filename": source_filename,
        "raw_bytes": raw_bytes,
        "description": kaggle_description_from_metadata(kaggle_metadata, dataset_ref),
        "files": files,
        "download_path": selected_path,
    }
