import io
import struct
from fractions import Fraction
from typing import List, Optional

import numpy as np
from PIL import Image, ExifTags
from PIL.PngImagePlugin import PngInfo


# ============================================================
# FIELD INFORMATION
# ============================================================

FIELD_INFO = {
   "GPS.Coordinates": {
    "label": "GPS coordinates",
    "risk": "high",
    "category": "location",
    "sensitive": True,
    "message": "This reveals your exact location",
},
    "GPS.GPSAltitude": {
    "label": "GPS altitude",
    "risk": "low",
    "category": "location",
    "sensitive": False,
    "message": "Reveals the elevation",
},
    "GPS.GPSTimeStamp": {
        "label": "GPS timestamp",
        "risk": "low",
        "category": "location",
        "sensitive": False,
        "message": "Reveals the time of the GPS fix",
    },
    "DateTimeOriginal": {
        "label": "Date/time photo taken",
        "risk": "medium",
        "category": "timestamp",
        "sensitive": False,
        "message": "Reveals when the photo was taken",
    },
    "DateTimeDigitized": {
        "label": "Date/time digitized",
        "risk": "low",
        "category": "timestamp",
        "sensitive": False,
        "message": "Reveals when the photo was digitized",
    },
    "Make": {
        "label": "Camera manufacturer",
        "risk": "medium",
        "category": "device",
        "sensitive": False,
        "message": "Reveals the camera manufacturer",
    },
    "Model": {
        "label": "Camera model",
        "risk": "medium",
        "category": "device",
        "sensitive": False,
        "message": "Reveals the camera model",
    },
    "LensModel": {
        "label": "Lens model",
        "risk": "low",
        "category": "device",
        "sensitive": False,
        "message": "Reveals the lens model",
    },
    "SerialNumber": {
        "label": "Camera serial number",
        "risk": "high",
        "category": "device",
        "sensitive": True,
        "message": "Reveals the camera serial number",
    },
    "Software": {
        "label": "Editing software used",
        "risk": "low",
        "category": "technical",
        "sensitive": False,
    },
    "Artist": {
        "label": "Photographer name",
        "risk": "high",
        "category": "identity",
        "sensitive": True,
        "message": "Reveals the photographer's name",
    },
    "Copyright": {
        "label": "Copyright holder",
        "risk": "high",
        "category": "identity",
        "sensitive": True,
        "message": "Reveals the copyright holder",
    },
    "EmbeddedThumbnail": {
        "label": "Embedded thumbnail image",
        "risk": "medium",
        "category": "identity",
        "sensitive": False,
        "message": "Reveals the embedded thumbnail image",
    },
    "Software": {
        "label": "Editing software used",
        "risk": "low",
        "category": "technical",
        "sensitive": False,
        "message": "Reveals the editing software used",
    },
    "PNG.tEXt": {
        "label": "PNG text metadata",
        "risk": "medium",
        "category": "technical",
        "sensitive": False,
        "message": "Reveals the PNG text metadata",
    },
    "PNG.iTXt": {
        "label": "PNG international text metadata",
        "risk": "medium",
        "category": "technical",
        "sensitive": False,
        "message": "Reveals the PNG international text metadata",
    },
}


# ============================================================
# EXIF TAG IDS
# ============================================================

EXIF_TAGS = {
    name: tag_id
    for tag_id, name in ExifTags.TAGS.items()
}

GPS_TAGS = {
    name: tag_id
    for tag_id, name in ExifTags.GPSTAGS.items()
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def _open_image(file_bytes: bytes, filename: str = "") -> Image.Image:
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()
        return image
    except Exception as exc:
        raise ValueError(f"Unable to open image '{filename}'") from exc


def _make_field(key: str, value) -> dict:
    if key not in FIELD_INFO:
        return None

    if value is None:
        return None

    value = str(value)

    if not value.strip():
        return None

    info = FIELD_INFO[key]

    return {
        "key": key,
        "label": info["label"],
        "value": value,
        "risk": info["risk"],
        "category": info["category"],
        "sensitive": info["sensitive"],
        "message": info["message"],
    }


def _rational_to_float(value) -> float:
    if isinstance(value, Fraction):
        return float(value)

    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        if value.denominator != 0:
            return float(value.numerator) / float(value.denominator)

    if isinstance(value, tuple) and len(value) == 2:
        if value[1] != 0:
            return float(value[0]) / float(value[1])

    return float(value)


def _convert_gps_coordinate(values) -> float:
    """
    Convert EXIF GPS degrees/minutes/seconds into decimal degrees.
    """

    degrees = _rational_to_float(values[0])
    minutes = _rational_to_float(values[1])
    seconds = _rational_to_float(values[2])

    return degrees + (minutes / 60.0) + (seconds / 3600.0)


def _format_gps_coordinate(values, reference) -> str:
    decimal = _convert_gps_coordinate(values)

    reference = str(reference).upper()

    return f"{abs(decimal):.6f} {reference}"


def _format_gps_timestamp(values) -> str:
    """
    EXIF GPSTimeStamp is stored as:
        [hour, minute, second]
    """

    if not values or len(values) < 3:
        return str(values)

    hour = int(_rational_to_float(values[0]))
    minute = int(_rational_to_float(values[1]))
    second = _rational_to_float(values[2])

    return f"{hour:02d}:{minute:02d}:{second:02.0f} UTC"


# ============================================================
# THUMBNAIL
# ============================================================

def _get_thumbnail(exif):
    try:
        thumbnail = exif.get_thumbnail()

        if thumbnail:
            return thumbnail
    except Exception:
        pass

    return None


def _thumbnail_matches_main_image(
    thumbnail_bytes: bytes,
    image: Image.Image
) -> bool:
    """
    Compare the embedded thumbnail to a resized version of the
    main image.

    This is a practical comparison rather than a forensic guarantee.
    """

    try:
        thumbnail = Image.open(io.BytesIO(thumbnail_bytes)).convert("RGB")

        main = image.convert("RGB").resize(
            thumbnail.size,
            Image.Resampling.LANCZOS
        )

        thumb_array = np.asarray(thumbnail, dtype=np.float32)
        main_array = np.asarray(main, dtype=np.float32)

        difference = np.mean(
            np.abs(thumb_array - main_array)
        )

        # A low difference means the thumbnail represents the
        # current main image closely.
        return difference < 15.0

    except Exception:
        return False


def _extract_thumbnail_field(image: Image.Image):
    exif = image.getexif()
    thumbnail = _get_thumbnail(exif)

    if not thumbnail:
        return None

    # The important part is that we compare the thumbnail image
    # against the main image rather than merely checking whether
    # the EXIF thumbnail tag exists.
    matches = _thumbnail_matches_main_image(
        thumbnail,
        image
    )

    if matches:
        return _make_field(
            "EmbeddedThumbnail",
            "present"
        )

    return _make_field(
        "EmbeddedThumbnail",
        "present (may show uncropped original)"
    )


# ============================================================
# EXIF EXTRACTION
# ============================================================

def _extract_exif(image: Image.Image) -> List[dict]:
    fields = []

    exif = image.getexif()

    if not exif:
        return fields

    # --------------------------------------------------------
    # GPS
    # --------------------------------------------------------

    gps_data = {}

    try:
        gps_data = exif.get_ifd(ExifTags.IFD.GPSInfo)
    except Exception:
        gps_data = {}

    if gps_data:
        # GPS latitude
        latitude = gps_data.get(GPS_TAGS.get("GPSLatitude"))
        latitude_ref = gps_data.get(GPS_TAGS.get("GPSLatitudeRef"))

        if latitude is not None and latitude_ref is not None:
            fields.append(
                _make_field(
                    "GPS.GPSLatitude",
                    _format_gps_coordinate(
                        latitude,
                        latitude_ref
                    )
                )
            )

        # GPS longitude
        longitude = gps_data.get(GPS_TAGS.get("GPSLongitude"))
        longitude_ref = gps_data.get(GPS_TAGS.get("GPSLongitudeRef"))

        if longitude is not None and longitude_ref is not None:
            fields.append(
                _make_field(
                    "GPS.GPSLongitude",
                    _format_gps_coordinate(
                        longitude,
                        longitude_ref
                    )
                )
            )

        # GPS altitude
        altitude = gps_data.get(GPS_TAGS.get("GPSAltitude"))

        if altitude is not None:
            altitude_value = _rational_to_float(altitude)

            altitude_ref = gps_data.get(
                GPS_TAGS.get("GPSAltitudeRef")
            )

            if altitude_ref == 1:
                altitude_value = -altitude_value

            fields.append(
                _make_field(
                    "GPS.GPSAltitude",
                    f"{altitude_value:.2f} m"
                )
            )

        # GPS timestamp
        gps_time = gps_data.get(
            GPS_TAGS.get("GPSTimeStamp")
        )

        if gps_time is not None:
            fields.append(
                _make_field(
                    "GPS.GPSTimeStamp",
                    _format_gps_timestamp(gps_time)
                )
            )

    # --------------------------------------------------------
    # Normal EXIF fields
    # --------------------------------------------------------

    supported_exif = {
        "DateTimeOriginal",
        "DateTimeDigitized",
        "Make",
        "Model",
        "LensModel",
        "SerialNumber",
        "Software",
        "Artist",
        "Copyright",
    }

    for tag_id, value in exif.items():
        tag_name = ExifTags.TAGS.get(tag_id)

        if tag_name not in supported_exif:
            continue

        field = _make_field(
            tag_name,
            value
        )

        if field:
            fields.append(field)

    # --------------------------------------------------------
    # Embedded thumbnail
    # --------------------------------------------------------

    thumbnail_field = _extract_thumbnail_field(image)

    if thumbnail_field:
        fields.append(thumbnail_field)

    return fields


# ============================================================
# PNG METADATA
# ============================================================

def _read_png_text_chunks(file_bytes: bytes):
    """
    Read PNG tEXt and iTXt chunks directly from the PNG file.

    Returns:
        {
            "tEXt": [...],
            "iTXt": [...]
        }
    """

    result = {
        "tEXt": [],
        "iTXt": [],
    }

    if not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return result

    position = 8

    while position + 12 <= len(file_bytes):
        try:
            length = struct.unpack(
                ">I",
                file_bytes[position:position + 4]
            )[0]

            chunk_type = file_bytes[
                position + 4:position + 8
            ]

            data_start = position + 8
            data_end = data_start + length

            if data_end + 4 > len(file_bytes):
                break

            data = file_bytes[data_start:data_end]

            if chunk_type == b"tEXt":
                parts = data.split(b"\x00", 1)

                if len(parts) == 2:
                    keyword = parts[0].decode(
                        "latin-1",
                        errors="replace"
                    )

                    text = parts[1].decode(
                        "latin-1",
                        errors="replace"
                    )

                    result["tEXt"].append(
                        (keyword, text)
                    )

            elif chunk_type == b"iTXt":
                # keyword
                null_pos = data.find(b"\x00")

                if null_pos == -1:
                    position = data_end + 4
                    continue

                keyword = data[:null_pos].decode(
                    "latin-1",
                    errors="replace"
                )

                remainder = data[null_pos + 1:]

                if len(remainder) < 2:
                    position = data_end + 4
                    continue

                compression_flag = remainder[0]
                compression_method = remainder[1]

                remainder = remainder[2:]

                # language tag
                null_pos = remainder.find(b"\x00")

                if null_pos == -1:
                    position = data_end + 4
                    continue

                remainder = remainder[null_pos + 1:]

                # translated keyword
                null_pos = remainder.find(b"\x00")

                if null_pos == -1:
                    position = data_end + 4
                    continue

                remainder = remainder[null_pos + 1:]

                # We only decode uncompressed iTXt.
                if compression_flag == 0:
                    text = remainder.decode(
                        "utf-8",
                        errors="replace"
                    )

                    result["iTXt"].append(
                        (keyword, text)
                    )

        except Exception:
            pass

        position = data_end + 4

        if chunk_type == b"IEND":
            break

    return result


def _extract_png_metadata(file_bytes: bytes) -> List[dict]:
    fields = []

    chunks = _read_png_text_chunks(file_bytes)

    if chunks["tEXt"]:
        values = []

        for keyword, text in chunks["tEXt"]:
            values.append(
                f"{keyword}: {text}"
            )

        fields.append(
            _make_field(
                "PNG.tEXt",
                "; ".join(values)
            )
        )

    if chunks["iTXt"]:
        values = []

        for keyword, text in chunks["iTXt"]:
            values.append(
                f"{keyword}: {text}"
            )

        fields.append(
            _make_field(
                "PNG.iTXt",
                "; ".join(values)
            )
        )

    return fields


# ============================================================
# PUBLIC EXTRACT FUNCTION
# ============================================================

def extract(file_bytes: bytes, filename: str = "") -> dict:
    """
    Extract supported metadata from an image.

    Returns:
        {
            "format": "jpeg",
            "fields": [...]
        }
    """

    image = _open_image(
        file_bytes,
        filename
    )

    image_format = (image.format or "").lower()

    fields = []

    # EXIF exists primarily in JPEG/TIFF-style images.
    if image_format in ("jpeg", "jpg", "tiff", "webp"):
        fields.extend(
            _extract_exif(image)
        )

    # PNG text metadata
    if image_format == "png":
        fields.extend(
            _extract_png_metadata(file_bytes)
        )

    return {
        "format": image_format,
        "fields": [
            field
            for field in fields
            if field is not None
        ],
    }


# ============================================================
# STRIPPING HELPERS
# ============================================================

def _build_clean_exif(
    image: Image.Image,
    keep: set
):
    """
    Create a new EXIF object containing only the fields
    explicitly requested in `keep`.

    Example:
        keep = {"Make", "Model"}

    preserves Make and Model and removes the other supported
    metadata.
    """

    original_exif = image.getexif()
    clean_exif = Image.Exif()

    if not original_exif:
        return clean_exif

    # --------------------------------------------------------
    # Normal EXIF fields
    # --------------------------------------------------------

    supported_fields = {
        "DateTimeOriginal",
        "DateTimeDigitized",
        "Make",
        "Model",
        "LensModel",
        "SerialNumber",
        "Software",
        "Artist",
        "Copyright",
    }

    for tag_id, value in original_exif.items():
        tag_name = ExifTags.TAGS.get(tag_id)

        if tag_name in supported_fields:
            if tag_name in keep:
                clean_exif[tag_id] = value

    # --------------------------------------------------------
    # GPS fields
    # --------------------------------------------------------

    try:
        original_gps = original_exif.get_ifd(
            ExifTags.IFD.GPSInfo
        )
    except Exception:
        original_gps = {}

    if original_gps:
        clean_gps = {}

        # Latitude
        if "GPS.GPSLatitude" in keep:
            latitude_id = GPS_TAGS.get("GPSLatitude")
            latitude_ref_id = GPS_TAGS.get("GPSLatitudeRef")

            if latitude_id in original_gps:
                clean_gps[latitude_id] = original_gps[latitude_id]

            if latitude_ref_id in original_gps:
                clean_gps[latitude_ref_id] = original_gps[
                    latitude_ref_id
                ]

        # Longitude
        if "GPS.GPSLongitude" in keep:
            longitude_id = GPS_TAGS.get("GPSLongitude")
            longitude_ref_id = GPS_TAGS.get("GPSLongitudeRef")

            if longitude_id in original_gps:
                clean_gps[longitude_id] = original_gps[
                    longitude_id
                ]

            if longitude_ref_id in original_gps:
                clean_gps[longitude_ref_id] = original_gps[
                    longitude_ref_id
                ]

        # Altitude
        if "GPS.GPSAltitude" in keep:
            altitude_id = GPS_TAGS.get("GPSAltitude")
            altitude_ref_id = GPS_TAGS.get("GPSAltitudeRef")

            if altitude_id in original_gps:
                clean_gps[altitude_id] = original_gps[
                    altitude_id
                ]

            if altitude_ref_id in original_gps:
                clean_gps[altitude_ref_id] = original_gps[
                    altitude_ref_id
                ]

        # GPS timestamp
        if "GPS.GPSTimeStamp" in keep:
            timestamp_id = GPS_TAGS.get("GPSTimeStamp")

            if timestamp_id in original_gps:
                clean_gps[timestamp_id] = original_gps[
                    timestamp_id
                ]

        if clean_gps:
            clean_exif[ExifTags.IFD.GPSInfo] = clean_gps

    # --------------------------------------------------------
    # Embedded thumbnail
    # --------------------------------------------------------

    if "EmbeddedThumbnail" in keep:
        thumbnail = _get_thumbnail(original_exif)

        if thumbnail:
            try:
                clean_exif.set_thumbnail(thumbnail)
            except Exception:
                pass

    return clean_exif


def _build_clean_png_info(
    file_bytes: bytes,
    keep: set
):
    """
    Build PNG text metadata that should be preserved.
    """

    png_info = PngInfo()

    chunks = _read_png_text_chunks(file_bytes)

    if "PNG.tEXt" in keep:
        for keyword, text in chunks["tEXt"]:
            png_info.add_text(
                keyword,
                text
            )

    if "PNG.iTXt" in keep:
        for keyword, text in chunks["iTXt"]:
            png_info.add_itxt(
                keyword,
                text
            )

    return png_info


def _image_to_jpeg_bytes(
    image: Image.Image,
    clean_exif
) -> bytes:
    """
    Save an image as JPEG with the selected EXIF metadata.
    """

    output = io.BytesIO()

    # JPEG cannot store RGBA/P mode directly.
    if image.mode not in ("RGB", "L", "CMYK"):
        image = image.convert("RGB")

    image.save(
        output,
        format="JPEG",
        exif=clean_exif.tobytes(),
        quality=95
    )

    return output.getvalue()


# ============================================================
# PUBLIC STRIP FUNCTION
# ============================================================

def strip(
    file_bytes: bytes,
    filename: str = "",
    keep: Optional[List[str]] = None
) -> bytes:
    """
    Remove supported metadata from an image.

    `keep` contains the metadata keys that the user chose to KEEP.

    Example:

        keep = ["Make", "Model"]

    means:
        Make  -> keep
        Model -> keep
        everything else supported -> remove

    An empty keep list removes all supported metadata.
    """

    if keep is None:
        keep = []

    keep = set(keep)

    image = _open_image(
        file_bytes,
        filename
    )

    image_format = (image.format or "").upper()

    # --------------------------------------------------------
    # JPEG
    # --------------------------------------------------------

    if image_format in ("JPEG", "JPG"):

        clean_exif = _build_clean_exif(
            image,
            keep
        )

        return _image_to_jpeg_bytes(
            image,
            clean_exif
        )

    # --------------------------------------------------------
    # PNG
    # --------------------------------------------------------

    if image_format == "PNG":

        output = io.BytesIO()

        png_info = _build_clean_png_info(
            file_bytes,
            keep
        )

        image.save(
            output,
            format="PNG",
            pnginfo=png_info
        )

        return output.getvalue()

    # --------------------------------------------------------
    # Other formats
    # --------------------------------------------------------

    raise ValueError(
        f"Unsupported image format for stripping: {image_format}"
    )