import json
import pytest

from pathlib import Path
from pystac import Item

from src.task import CopyAssets
from src.task import handler as copy_assets_handler

TEST_DIR = Path(__file__).parent
FIXTURE_DIR = TEST_DIR.joinpath("fixtures")
BASE_PAYLOAD_FPATH = FIXTURE_DIR / "base_payload.json"
ASSETS_DIR = FIXTURE_DIR.joinpath("assets")

OLD_ASSET_BASE_HREF = "https://naipeuwest.blob.core.windows.net/naip/v002/tx/2020/tx_060cm_2020/26097/"
NEW_ASSET_BASE_HREF = "s3://earthsearch-data/naip/tx_m_2609719_se_14_060_20201217/"


def make_payload(assets_json_fpath):
    with open(BASE_PAYLOAD_FPATH, 'r') as f:
        payload = json.load(f)
    with open(assets_json_fpath, 'r') as f:
        assets = json.load(f)
    payload['features'][0]['assets'] = assets
    return payload

TEST_DATA = [
    (
        # test assets="all" behavior
        {"assets": "all"},
        make_payload(ASSETS_DIR / "copy_image_copy_thumbnail.json")
    ),
    (
        # test assets copy/nocopy behavior
        {"assets": ["image"]},
        make_payload(ASSETS_DIR / "copy_image_nocopy_thumbnail.json")
    ),
    (
        # test drop_assets applied before assets="all"
        {"assets": "all", "drop_assets": ["image"]},
        make_payload(ASSETS_DIR / "drop_image_copy_thumbnail.json")
    ),
    (
        # test drop_assets drops everything
        {"assets": "all", "drop_assets": ["image", "thumbnail"]},
        make_payload(ASSETS_DIR / "drop_image_drop_thumbnail.json")
    ),
    (
        # test assets and drop_assets both ignore invalid keys
        {"assets": ["invalid-key"], "drop_assets": ["another-invalid-key"]},
        make_payload(ASSETS_DIR / "nocopy_image_nocopy_thumbnail.json")
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


@pytest.mark.parametrize("task_params,expected_payload", TEST_DATA)
def test_copy_assets(base_payload, task_params, expected_payload):
    expected_payload["process"][0]["tasks"]["copy-assets"] = task_params
    base_payload["process"][0]["tasks"]["copy-assets"] = task_params
    actual_payload = copy_assets_handler(base_payload, context={})
    assert actual_payload == expected_payload