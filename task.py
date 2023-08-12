#!/usr/bin/env python
import logging
from typing import Any, Dict, List
from boto3utils import s3
from pystac import Item
from stac_validator import stac_validator
from stactask import Task
from stactask.exceptions import InvalidInput


s3_client = s3(requester_pays=False)


class CopyAssets(Task):
    name = "copy-assets"
    description = "Copies specified Assets from Source STAC Item(s) and copies to s3 and updates Item Assets to point to new location."
    version = "0.1.0"

    @classmethod
    def validate(cls, payload: dict[str, Any]) -> bool:
        if "assets" not in payload["process"]["tasks"][cls.name]:
            raise InvalidInput("assets that need to be copied required to be specified")
        return True

    def process(
        self, assets: List[str], drop_assets: List[str]
    ) -> List[Dict[str, Any]]:
        # process method overrides Task
        created_items = []

        payload = self._payload

        try:
            item = self.items[0]

            item_dict = item.to_dict()

            # configuration options
            config = payload.get('process', {}).get('tasks', {}).get('copy-assets', {})

            assets = config.get('assets', item_dict['assets'].keys())
            drop_assets = config.get('drop_assets', [])


            # drop specified assets
            for asset in [a for a in drop_assets if a in list(item_dict['assets'].keys())]:
                logging.debug(f'Dropping asset {asset}')
                item_dict['assets'].pop(asset)
            if type(assets) is str and assets == 'ALL':
                assets = item_dict['assets'].keys()

            item_mod = item.from_dict(item_dict)

            try:
                # copy specified assets
                _assets = [a for a in assets if a in item_dict['assets'].keys()]

                for asset in _assets:
                    item = self.download_item_assets(item_mod, assets=[asset])
                    item = self.upload_item_assets_to_s3(item, assets=[asset])

                # replace item in payload
                payload['features'][0] = item.to_dict()
            except Exception as err:
                msg = f"copy-assets: failed processing {payload['id']} ({err})"
                logging.error(msg, exc_info=True)
                raise Exception(msg) from err

        except Exception as err:
            self.logger.error(err)
            raise Exception(f"Unable to copy assets: {err}")

        stac = stac_validator.StacValidate()
        valid = stac.validate_dict(item.to_dict())

        if valid:
            created_items.append(item.to_dict())
            return created_items
        else:
            raise Exception(
                f"STAC Item validation failed. Error: {stac.message[0]['error_message']}."
            )

def handler(event: dict[str, Any], context: dict[str, Any] = {}) -> Task:
    return CopyAssets.handler(event)


if __name__ == "__main__":
    CopyAssets.cli()
