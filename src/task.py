#!/usr/bin/env python
from jsonschema import Draft202012Validator, validate as jsonschema_validate
from typing import Any, Dict, List
from pystac import Item
from stac_validator import stac_validator
from stactask import Task, DownloadConfig
from stactask.exceptions import FailedValidation


class CopyAssets(Task):
    name = 'copy-assets'
    description = 'STAC Task to copy STAC Item Assets to S3 and return an updated Item'
    version = '0.0.8'
    task_options_schema = {
        '$schema': Draft202012Validator.META_SCHEMA['$id'],

        'type': 'object',
        'required': ['assets'],
        'properties': {
            'assets': {
                'oneOf': [
                    {
                        'type': 'array',
                        'minItems': 1,
                        'items': {'type': 'string'}
                    },
                    {
                        'type': 'string',
                        'enum': ['all', 'ALL']
                    },
                ]
            },
            'drop_assets': {
                'type': 'array',
                'items': {'type': 'string'}
            }
        }
    }

    def validate(self) -> bool:
        try:
            jsonschema_validate(self.task_options, schema=self.task_options_schema)
            return True
        except Exception as err:
            raise FailedValidation(err)

    def process(
        self,
        assets: List[str] | str,
        drop_assets: List[str] | None = None
    ) -> List[Dict[str, Any]]:
        """Copies a subset of an Item's Assets to S3 and returns an updated Item.

        Assets specified by 'drop_assets' are removed from the item first.
        Assets specified by 'assets' are copied to S3 and added to the new item.
        Any non-dropped/non-copied assets are persisted to the new item with old hrefs.

        Args:
            assets (list[str] | str): List of assets to copy to S3. Can be 'all' to
                                      specify all assets.
            drop_assets (list[str]): Optional. List of assets that will NOT be copied
                                     and NOT persisted to the new Item.

        Returns:
            list[dict]: List containing the single STAC Item dict that contains the
                        updated assets.
        """
        try:
            item_new_dict = self.items[0].to_dict()

            for drop_asset in drop_assets or []:
                item_new_dict['assets'].pop(drop_asset, None)

            if isinstance(assets, str) and assets.lower() == 'all':
                # Copy all non-dropped assets
                copy_assets = list(item_new_dict['assets'].keys())
                nocopy_assets = []
            else:
                # Copy all (valid) non-dropped assets specified in the payload
                copy_assets = [a for a in item_new_dict['assets'] if a in assets]
                nocopy_assets = [a for a in item_new_dict['assets'] if a not in assets]

            # Download then upload
            item_new = Item.from_dict(item_new_dict)
            item_new = self.download_item_assets(
                item_new, config=DownloadConfig(exclude=nocopy_assets)
            )
            item_new.make_asset_hrefs_absolute()
            item_new = self.upload_item_assets_to_s3(
                item_new, assets=copy_assets
            )
            item_new_dict = item_new.to_dict()

            # Replace payload item
            self._payload['features'][0] = item_new_dict

        except Exception as err:
            msg = f'copy-assets: failed processing {self._payload['id']} ({err})'
            self.logger.error(msg, exc_info=True)
            raise Exception(msg) from err

        stac = stac_validator.StacValidate()
        if not stac.validate_dict(item_new_dict):
            raise Exception(
                f'STAC Item validation failed. '
                f'Error: {stac.message[0]['error_message']}.'
            )

        return [item_new_dict]


def handler(event: dict[str, Any], context: dict[str, Any] = {}) -> Task:
    return CopyAssets.handler(event)


def cli() -> None:
    CopyAssets.cli()


if __name__ == '__main__':
    cli()
