from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core import kaggle_import
from core.artifacts import ArtifactStore
from core.dataset_tools import DatasetTools


class FakeKaggleApi:
    def __init__(self, file_names, download_writer):
        self.file_names = file_names
        self.download_writer = download_writer
        self.download_requests = []

    def dataset_list_files(self, dataset_ref, page_token=None, page_size=100):
        files = [
            SimpleNamespace(name=name, total_bytes=100, creation_date="2026-05-31")
            for name in self.file_names
        ]
        return SimpleNamespace(files=files, next_page_token=None, error_message=None)

    def dataset_metadata(self, dataset_ref, metadata_dir):
        metadata_path = Path(metadata_dir) / "dataset-metadata.json"
        metadata_path.write_text(
            json.dumps(
                {
                    "title": "Fake Kaggle Dataset",
                    "subtitle": "Fixture-backed import",
                    "description": "Used by importer tests.",
                    "licenses": [{"name": "CC0"}],
                }
            ),
            encoding="utf-8",
        )
        return str(metadata_path)

    def dataset_download_file(self, dataset_ref, selected_file, path, force=True, quiet=True):
        self.download_requests.append((dataset_ref, selected_file))
        self.download_writer(Path(path), selected_file)


def write_zip(download_dir: Path, selected_file: str, members: dict[str, bytes]) -> None:
    zip_path = download_dir / f"{Path(selected_file).name}.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for member_name, content in members.items():
            archive.writestr(member_name, content)


class KaggleImportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.download_root = Path(self.temp_dir.name) / "kaggle_downloads"

    def tearDown(self):
        self.temp_dir.cleanup()

    def fetch_with_fake_api(self, fake_api: FakeKaggleApi, requested_file: str = ""):
        with patch.object(kaggle_import, "kaggle_api", return_value=fake_api):
            return kaggle_import.fetch_kaggle_dataset(
                "owner/dataset",
                requested_file,
                download_root=self.download_root,
            )

    def test_fetch_extracts_csv_when_kaggle_downloads_csv_zip(self):
        fake_api = FakeKaggleApi(
            ["train.csv"],
            lambda download_dir, selected_file: write_zip(
                download_dir,
                selected_file,
                {"train.csv": b"city,sales\nParis,10\n"},
            ),
        )

        result = self.fetch_with_fake_api(fake_api)

        self.assertEqual(result["selected_file"], "train.csv")
        self.assertEqual(result["raw_bytes"], b"city,sales\nParis,10\n")
        self.assertTrue(str(result["download_path"]).endswith("train.csv"))

    def test_fetch_matches_nested_csv_inside_zip_by_kaggle_path(self):
        fake_api = FakeKaggleApi(
            ["data/train.csv"],
            lambda download_dir, selected_file: write_zip(
                download_dir,
                selected_file,
                {"data/train.csv": b"month,revenue\n2026-01,100\n"},
            ),
        )

        result = self.fetch_with_fake_api(fake_api, "data/train.csv")

        self.assertEqual(result["selected_file"], "data/train.csv")
        self.assertEqual(result["raw_bytes"], b"month,revenue\n2026-01,100\n")

    def test_fetch_normalizes_windows_style_zip_member_paths(self):
        fake_api = FakeKaggleApi(
            ["data/train.csv"],
            lambda download_dir, selected_file: write_zip(
                download_dir,
                selected_file,
                {"data\\train.csv": b"month,revenue\n2026-02,200\n"},
            ),
        )

        result = self.fetch_with_fake_api(fake_api, "data/train.csv")

        self.assertEqual(result["raw_bytes"], b"month,revenue\n2026-02,200\n")

    def test_fetch_prefers_requested_csv_when_zip_contains_multiple_csvs(self):
        fake_api = FakeKaggleApi(
            ["wanted.csv"],
            lambda download_dir, selected_file: write_zip(
                download_dir,
                selected_file,
                {
                    "other.csv": b"name,value\nwrong,0\n",
                    "nested/wanted.csv": b"name,value\nright,1\n",
                },
            ),
        )

        result = self.fetch_with_fake_api(fake_api, "wanted.csv")

        self.assertEqual(result["raw_bytes"], b"name,value\nright,1\n")

    def test_fetch_skips_unsafe_zip_members_without_writing_outside_download_root(self):
        fake_api = FakeKaggleApi(
            ["escape.csv"],
            lambda download_dir, selected_file: write_zip(
                download_dir,
                selected_file,
                {"../escape.csv": b"bad,path\n1,2\n"},
            ),
        )

        with self.assertRaises(FileNotFoundError):
            self.fetch_with_fake_api(fake_api, "escape.csv")

        self.assertFalse((self.download_root.parent / "escape.csv").exists())

    def test_choose_kaggle_csv_file_accepts_listed_csv_zip_for_requested_csv(self):
        selected = kaggle_import.choose_kaggle_csv_file(
            [{"name": "train.csv.zip", "size": 100}],
            "train.csv",
        )

        self.assertEqual(selected, "train.csv.zip")

    def test_normalizes_kaggle_dataset_urls(self):
        self.assertEqual(
            kaggle_import.normalize_kaggle_dataset_ref(
                "https://www.kaggle.com/datasets/owner/dataset-slug"
            ),
            "owner/dataset-slug",
        )

    def test_invalid_kaggle_dataset_ref_raises(self):
        with self.assertRaises(ValueError):
            kaggle_import.normalize_kaggle_dataset_ref("not-enough")

    def test_dataset_tools_can_ingest_kaggle_dataset(self):
        fake_import = {
            "dataset_ref": "owner/dataset",
            "selected_file": "sales.csv",
            "filename": "kaggle_owner_dataset_sales.csv",
            "raw_bytes": b"region,revenue\nEast,10\nWest,20\n",
            "description": "Kaggle dataset: owner/dataset",
            "files": [{"name": "sales.csv", "size": 100}],
            "download_path": self.download_root / "sales.csv",
        }

        with patch("core.dataset_tools.fetch_kaggle_dataset", return_value=fake_import):
            tools = DatasetTools(ArtifactStore(Path(self.temp_dir.name) / "artifacts"))
            result = tools.ingest_kaggle_dataset("owner/dataset", "sales.csv", "User note")

        self.assertEqual(result.metadata.source_file, "kaggle_owner_dataset_sales.csv")
        self.assertIn("Kaggle dataset: owner/dataset", result.metadata.dataset_description)
        self.assertIn("User note", result.metadata.dataset_description)
        self.assertEqual(result.suggested_questions[0].question, "What is the total revenue?")


if __name__ == "__main__":
    unittest.main()
