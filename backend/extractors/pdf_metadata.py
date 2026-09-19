import io
from typing import List

from pypdf import PdfReader, PdfWriter

from backend.models.metadata_schema import MetadataField, MetadataResult


FIELD_INFO = {
    "Title": {
        "label": "Document title",
        "risk": "low",
        "category": "document",
        "sensitive": False,
    },
    "Author": {
        "label": "Author",
        "risk": "high",
        "category": "identity",
        "sensitive": True,
    },
    "Subject": {
        "label": "Subject",
        "risk": "low",
        "category": "document",
        "sensitive": False,
    },
    "Creator": {
        "label": "Creator application",
        "risk": "low",
        "category": "technical",
        "sensitive": False,
    },
    "Producer": {
        "label": "PDF producer",
        "risk": "low",
        "category": "technical",
        "sensitive": False,
    },
    "CreationDate": {
        "label": "Creation date",
        "risk": "medium",
        "category": "timestamp",
        "sensitive": True,
    },
    "ModDate": {
        "label": "Modification date",
        "risk": "medium",
        "category": "timestamp",
        "sensitive": True,
    },
    "Keywords": {
        "label": "Keywords",
        "risk": "medium",
        "category": "document",
        "sensitive": True,
    },
}


def _make_field(key: str, value) -> MetadataField:
    info = FIELD_INFO[key]

    return {
        "key": key,
        "label": info["label"],
        "value": str(value),
        "risk": info["risk"],
        "category": info["category"],
        "sensitive": info["sensitive"],
    }


def _extract_document_info(reader: PdfReader) -> List[MetadataField]:
    fields = []
    metadata = reader.metadata

    if not metadata:
        return fields

    for key in FIELD_INFO:
        value = metadata.get(f"/{key}")

        if value is not None and str(value).strip():
            fields.append(_make_field(key, value))

    return fields


def _extract_xmp_fields(reader: PdfReader) -> List[MetadataField]:
    fields = []

    try:
        xmp = reader.xmp_metadata
    except Exception:
        xmp = None

    if xmp is None:
        return fields

    # XMP is treated as a single metadata field for now.
    fields.append(
        {
            "key": "XMP",
            "label": "XMP metadata",
            "value": "Present",
            "risk": "medium",
            "category": "technical",
            "sensitive": True,
        }
    )

    return fields


def extract(file_bytes: bytes, filename: str = "") -> MetadataResult:
    """
    Extract supported metadata from a PDF.

    Returns metadata using the same common schema as the image extractor.
    """

    reader = PdfReader(io.BytesIO(file_bytes), strict=False)

    fields = []

    fields.extend(_extract_document_info(reader))
    fields.extend(_extract_xmp_fields(reader))

    return {
        "format": "pdf",
        "fields": fields,
    }


def _copy_pages(reader: PdfReader, writer: PdfWriter) -> None:
    """
    Copy all pages from the original PDF into the new writer.
    """
    for page in reader.pages:
        writer.add_page(page)


def strip(
    file_bytes: bytes,
    filename: str = "",
    keep=None,
) -> bytes:
    """
    Remove supported PDF metadata.

    keep:
        List of metadata keys that should be preserved.

    Example:
        keep=["Title", "Subject"]

    An empty keep list removes supported document metadata.
    """

    if keep is None:
        keep = []

    keep = set(keep)

    reader = PdfReader(io.BytesIO(file_bytes), strict=False)

    writer = PdfWriter()

    _copy_pages(reader, writer)

    # Preserve only explicitly requested document-information fields.
    metadata_to_keep = {}

    original_metadata = reader.metadata

    if original_metadata:
        for key in FIELD_INFO:
            if key in keep:
                value = original_metadata.get(f"/{key}")

                if value is not None:
                    metadata_to_keep[f"/{key}"] = str(value)

    # pypdf's metadata setter controls the PDF document information
    # dictionary. Setting it to None removes it.
    if metadata_to_keep:
        writer.metadata = metadata_to_keep
    else:
        writer.metadata = None

    # We currently remove XMP metadata rather than preserving it.
    # This keeps the scrubber conservative until individual XMP fields
    # are supported explicitly.

    output = io.BytesIO()
    writer.write(output)

    return output.getvalue()