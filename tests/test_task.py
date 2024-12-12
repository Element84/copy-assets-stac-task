import json
import pytest

from pathlib import Path
from pystac import Item

from src.task import CopyAssets
from src.task import handler as copy_assets_handler

TEST_DIR = Path(__file__).parent
FIXTURE_DIR = TEST_DIR.joinpath("fixtures")
BASE_PAYLOAD_FPATH = FIXTURE_DIR / "base_payload.json"
ITEMS_DIR = FIXTURE_DIR.joinpath("items")

OLD_ASSET_BASE_HREF = "https://naipeuwest.blob.core.windows.net/naip/v002/tx/2020/tx_060cm_2020/26097/"
NEW_ASSET_BASE_HREF = "s3://earthsearch-data/naip/tx_m_2609719_se_14_060_20201217/"

TEST_DATA = [
    (
        # test assets="all" behavior
        {"assets": "all"},
        ITEMS_DIR / "expected_item_copy_image_copy_thumbnail.json"
    ),
    (
        # test assets copy/nocopy behavior
        {"assets": ["image"]},
        ITEMS_DIR / "expected_item_copy_image_nocopy_thumbnail.json"
    ),
    (
        # test drop_assets applied before assets="all"
        {"assets": "all", "drop_assets": ["image"]},
        ITEMS_DIR / "expected_item_drop_image_copy_thumbnail.json"
    ),
    (
        # test drop_assets drops everything
        {"assets": "all", "drop_assets": ["image", "thumbnail"]},
        ITEMS_DIR / "expected_item_drop_image_drop_thumbnail.json"
    ),
    (
        # test assets and drop_assets both ignore invalid keys
        {"assets": ["invalid-key"], "drop_assets": ["another-invalid-key"]},
        ITEMS_DIR / "expected_item_nocopy_image_nocopy_thumbnail.json"
    ),
]


@pytest.fixture(autouse=True)
def base_payload():
    with open(BASE_PAYLOAD_FPATH, 'r') as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def _mock_task_download_item_assets(monkeypatch) -> None:
    def mock_download(cls: CopyAssets, item: Item) -> Item:
        return item

    monkeypatch.setattr(
        'src.task.CopyAssets.download_item_assets',
        mock_download,
    )


@pytest.fixture(autouse=True)
def _mock_task_upload_item_assets_to_s3(monkeypatch) -> None:
    def mock_upload(cls: CopyAssets, item: dict) -> Item:
        for _, asset in item.assets.items():
            asset.href = asset.href.replace(
                OLD_ASSET_BASE_HREF,
                NEW_ASSET_BASE_HREF
            )
        return item

    monkeypatch.setattr(
        'src.task.CopyAssets.upload_item_assets_to_s3',
        mock_upload,
    )


@pytest.mark.parametrize("task_params,fpath_to_expected_output_as_json", TEST_DATA)
def test_copy_assets(base_payload, task_params, fpath_to_expected_output_as_json):
    with open(fpath_to_expected_output_as_json, 'r') as f:
        expected = json.load(f)

    base_payload["process"][0]["tasks"]["copy-assets"] = task_params
    actual = copy_assets_handler(base_payload, context={})

    assert actual == expected