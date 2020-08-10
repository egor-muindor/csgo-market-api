from typing import List, TypedDict

__all__ = ['ImportItemType', 'MassInfoListType']


class ImportItemType(TypedDict):
    """Import item type class"""
    class_id: int
    instance_id: int


MassInfoListType = List[ImportItemType]
