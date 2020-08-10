__all__ = ['Item']


class Item:
    def __init__(self, class_id: int, instance_id: int, market_name: str, market_hash_name: str, hash: str,
                 description: list = None, tags: list = None, our_market_instance_id: int = None):
        self.class_id = class_id
        self.instance_id = instance_id
        self.market_name = market_name
        self.market_hash_name = market_hash_name
        self.hash = hash
        self.description = description
        self.tags = tags
        self.our_market_instance_id = our_market_instance_id

    @staticmethod
    def new_from_response_item_info(response: dict):
        item_data = {
            'class_id': int(response['classid']),
            'instance_id': int(response['instanceid']),
            'market_name': response['market_name'],
            'market_hash_name': response['market_hash_name'],
            'description': response['description'],
            'tags': response['tags'],
            'our_market_instance_id':
                response['our_market_instanceid'] if
                response['our_market_instanceid'] != 'null' else None,
            'hash': response['hash']
        }

        return Item(**item_data)

    @staticmethod
    def new_from_mass_info(response: dict):
        item_data = {
            'class_id': int(response['classid']),
            'instance_id': int(response['instanceid']),
            'market_name': response['info']['market_name'],
            'market_hash_name': response['info']['market_hash_name'],
            'our_market_instance_id':
                response['info']['our_market_instanceid'] if
                response['info']['our_market_instanceid'] != 'null' else None,
            'hash': response['info']['hash']
        }

        return Item(**item_data)
