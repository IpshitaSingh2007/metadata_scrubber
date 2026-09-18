from typing import TypedDict, List


class MetadataField(TypedDict):
    key: str
    label: str
    value: str
    risk: str
    category: str
    sensitive: bool


class MetadataResult(TypedDict):
    format: str
    fields: List[MetadataField]