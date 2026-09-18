from io import BytesIO
import struct

from PIL import Image, ExifTags


# ============================================================
# Metadata field definitions
# Source of truth: research team's metadata field reference
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


# Pillow EXIF tag IDs
EXIF_TAG_IDS = {
    name: tag_id
    for tag_id, name in ExifTags.TAGS.items()
}


GPS_TAG_IDS = {
    name: tag_id
    for tag_id, name in ExifTags.GPSTAGS.items()
}


# ============================================================
# Helpers
# ============================================================

def _open_image(file_bytes):
    """Open image bytes with Pillow."""
    return Image.open(BytesIO(file_bytes))


def _make_field(key, value):
    """Create a metadata field using the agreed API contract."""
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


def _rational_to_float(value):
    """Convert Pillow's rational EXIF values to float."""
    try:
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        try:
            return value.numerator / value.denominator
        except (AttributeError, ZeroDivisionError):
            return None


def _convert_gps_coordinate(values, reference):
    """
    Convert GPS degrees/minutes/seconds into decimal degrees.
    """
    if not values:
        return None

    try:
        degrees = _rational_to_float(values[0])
        minutes = _rational_to_float(values[1])
        seconds = _rational_to_float(values[2])

        if degrees is None or minutes is None or seconds is None:
            return None

        decimal = degrees + minutes / 60 + seconds / 3600

        if reference in ("S", "W"):
            decimal *= -1

        return round(decimal, 6)

    except (IndexError, TypeError):
        return None


def _format_gps_coordinate(latitude, longitude):
    """Return a readable GPS value."""
    if latitude is None or longitude is None:
        return None

    return f"{latitude}, {longitude}"


def _format_gps_timestamp(value):
    """
    GPS timestamp is normally [hour, minute, second].
    """
    if not value:
        return None

    try:
        parts = []

        for item in value:
            number = _rational_to_float(item)

            if number is None:
                return None

            parts.append(int(number))

        if len(parts) >= 3:
            return f"{parts[0]:02d}:{parts[1]:02d}:{parts[2]:02d} UTC"

    except (TypeError, ValueError):
        pass

    return str(value)


def _has_meaningful_value(value):
    """
    Don't report empty EXIF strings.

    The research requirement says absent/empty fields should not
    appear in the output.
    """
    if value is None:
        return False

    if isinstance(value, str) and not value.strip():
        return False

    return True


# ============================================================
# EXIF extraction
# ============================================================

def _extract_exif(image):
    """
    Extract the EXIF fields required by the research/API teams.
    """

    exif = image.getexif()

    if not exif:
        return []

    fields = []

    # --------------------------------------------------------
    # GPS
    # --------------------------------------------------------

    gps_info = exif.get_ifd(ExifTags.IFD.GPSInfo)

    latitude = None
    longitude = None

    if gps_info:

        latitude_values = gps_info.get(
            GPS_TAG_IDS.get("GPSLatitude")
        )

        latitude_ref = gps_info.get(
            GPS_TAG_IDS.get("GPSLatitudeRef")
        )

        longitude_values = gps_info.get(
            GPS_TAG_IDS.get("GPSLongitude")
        )

        longitude_ref = gps_info.get(
            GPS_TAG_IDS.get("GPSLongitudeRef")
        )

        if isinstance(latitude_ref, bytes):
            latitude_ref = latitude_ref.decode(
                "ascii",
                errors="ignore"
            )

        if isinstance(longitude_ref, bytes):
            longitude_ref = longitude_ref.decode(
                "ascii",
                errors="ignore"
            )

        if latitude_values and latitude_ref:
            latitude = _convert_gps_coordinate(
                latitude_values,
                latitude_ref
            )

        if longitude_values and longitude_ref:
            longitude = _convert_gps_coordinate(
                longitude_values,
                longitude_ref
            )

    # Research team specifically wants latitude + longitude
    # combined into ONE finding.
    if latitude is not None and longitude is not None:
        fields.append(
            _make_field(
                "GPS.Coordinates",
                _format_gps_coordinate(latitude, longitude)
            )
        )

    # GPS altitude
    altitude = None

    if gps_info:
        altitude_value = gps_info.get(
            GPS_TAG_IDS.get("GPSAltitude")
        )

        if altitude_value is not None:
            altitude = _rational_to_float(altitude_value)

    if altitude is not None:
        altitude_ref = gps_info.get(
            GPS_TAG_IDS.get("GPSAltitudeRef")
        )

        # GPSAltitudeRef = 1 means below sea level.
        if altitude_ref == 1:
            altitude = -abs(altitude)

        fields.append(
            _make_field(
                "GPS.GPSAltitude",
                f"{round(altitude, 2)} m"
            )
        )

    # GPS timestamp
    if gps_info:
        gps_timestamp = gps_info.get(
            GPS_TAG_IDS.get("GPSTimeStamp")
        )

        if gps_timestamp:
            formatted_time = _format_gps_timestamp(
                gps_timestamp
            )

            if formatted_time:
                fields.append(
                    _make_field(
                        "GPS.GPSTimeStamp",
                        formatted_time
                    )
                )

    # --------------------------------------------------------
    # Normal EXIF fields
    # --------------------------------------------------------

    tag_to_key = {
        "DateTimeOriginal": "DateTimeOriginal",
        "DateTimeDigitized": "DateTimeDigitized",
        "Make": "Make",
        "Model": "Model",
        "LensModel": "LensModel",
        "SerialNumber": "SerialNumber",
        "Artist": "Artist",
        "Copyright": "Copyright",
        "Software": "Software",
    }

    for exif_name, field_key in tag_to_key.items():

        tag_id = EXIF_TAG_IDS.get(exif_name)

        if tag_id is None:
            continue

        value = exif.get(tag_id)

        if not _has_meaningful_value(value):
            continue

        # Convert bytes to readable text where necessary.
        if isinstance(value, bytes):
            value = value.decode(
                "utf-8",
                errors="replace"
            ).strip()

            if not value:
                continue

        fields.append(
            _make_field(
                field_key,
                value
            )
        )

    return fields


# ============================================================
# Embedded thumbnail
# ============================================================

def _get_thumbnail(image):
    """
    Return the embedded EXIF thumbnail as a Pillow Image,
    or None if there isn't one.
    """

    try:
        exif = image.getexif()

        if not exif:
            return None

        thumbnail = exif.get_thumbnail()

        if thumbnail is None:
            return None

        return Image.open(
            BytesIO(thumbnail)
        ).convert("RGB")

    except Exception:
        return None


def _thumbnail_matches_main_image(image, thumbnail):
    """
    Compare the embedded thumbnail with the main image.

    The thumbnail is normally a resized version of the main image,
    so we resize the main image to the thumbnail dimensions and
    compare the pixels.

    This deliberately checks image content rather than merely
    checking whether a thumbnail tag exists.
    """

    if thumbnail is None:
        return False

    try:
        main = image.convert("RGB")

        # Prevent huge images from causing unnecessary work.
        max_dimension = 512

        scale = min(
            1.0,
            max_dimension / max(main.size)
        )

        if scale < 1:
            new_size = (
                max(1, int(main.width * scale)),
                max(1, int(main.height * scale)),
            )

            main = main.resize(
                new_size,
                Image.Resampling.LANCZOS
            )

        # Compare aspect ratios first.
        main_ratio = main.width / main.height
        thumb_ratio = thumbnail.width / thumbnail.height

        if abs(main_ratio - thumb_ratio) > 0.05:
            return False

        # Resize main image to thumbnail size.
        resized_main = main.resize(
            thumbnail.size,
            Image.Resampling.LANCZOS
        )

        # Calculate average pixel difference.
        import numpy as np

        main_array = np.asarray(
            resized_main,
            dtype=np.int16
        )

        thumb_array = np.asarray(
            thumbnail,
            dtype=np.int16
        )

        difference = np.mean(
            np.abs(main_array - thumb_array)
        )

        # JPEG thumbnails can differ slightly due to compression.
        return difference < 35

    except Exception:
        return False


def _extract_thumbnail_field(image):
    """
    Check for an embedded thumbnail and verify its relationship
    to the main image.
    """

    thumbnail = _get_thumbnail(image)

    if thumbnail is None:
        return None

    matches_main_image = _thumbnail_matches_main_image(
        image,
        thumbnail
    )

    if matches_main_image:
        value = (
            "present (preview matches the main image)"
        )
    else:
        value = (
            "present (may contain content different "
            "from the visible image)"
        )

    return _make_field(
        "EmbeddedThumbnail",
        value
    )


# ============================================================
# PNG text metadata
# ============================================================

def _read_png_text_chunks(file_bytes):
    """
    Read PNG tEXt and iTXt chunks.

    Returns:
        {
            "PNG.tEXt": [...],
            "PNG.iTXt": [...]
        }
    """

    result = {
        "PNG.tEXt": [],
        "PNG.iTXt": [],
    }

    # PNG signature
    if not file_bytes.startswith(
        b"\x89PNG\r\n\x1a\n"
    ):
        return result

    position = 8

    while position + 8 <= len(file_bytes):

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

            data = file_bytes[
                data_start:data_end
            ]

            # --------------------------------------------
            # tEXt
            # --------------------------------------------

            if chunk_type == b"tEXt":

                parts = data.split(
                    b"\x00",
                    1
                )

                if len(parts) == 2:

                    keyword = parts[0].decode(
                        "latin-1",
                        errors="replace"
                    )

                    text = parts[1].decode(
                        "latin-1",
                        errors="replace"
                    )

                    result["PNG.tEXt"].append(
                        f"{keyword}: {text}"
                    )

            # --------------------------------------------
            # iTXt
            # --------------------------------------------

            elif chunk_type == b"iTXt":

                # iTXt structure:
                #
                # keyword\0
                # compression_flag
                # compression_method
                # language_tag\0
                # translated_keyword\0
                # text

                first_null = data.find(b"\x00")

                if first_null != -1:

                    keyword = data[
                        :first_null
                    ].decode(
                        "utf-8",
                        errors="replace"
                    )

                    remaining = data[
                        first_null + 1:
                    ]

                    if len(remaining) >= 2:

                        compression_flag = remaining[0]

                        # compression method
                        # currently not needed
                        remaining = remaining[2:]

                        second_null = remaining.find(
                            b"\x00"
                        )

                        if second_null != -1:

                            language = remaining[
                                :second_null
                            ]

                            remaining = remaining[
                                second_null + 1:
                            ]

                            third_null = remaining.find(
                                b"\x00"
                            )

                            if third_null != -1:

                                translated_keyword = (
                                    remaining[
                                        :third_null
                                    ]
                                )

                                text_data = (
                                    remaining[
                                        third_null + 1:
                                    ]
                                )

                                # Uncompressed iTXt can be
                                # decoded directly.
                                if compression_flag == 0:

                                    text = text_data.decode(
                                        "utf-8",
                                        errors="replace"
                                    )

                                    result[
                                        "PNG.iTXt"
                                    ].append(
                                        f"{keyword}: {text}"
                                    )

        except Exception:
            pass

        # Move to next chunk:
        # length + type + data + CRC
        position = data_end + 4

    return result


def _extract_png_metadata(file_bytes):
    """Extract PNG tEXt and iTXt findings."""

    fields = []

    text_chunks = _read_png_text_chunks(
        file_bytes
    )

    if text_chunks["PNG.tEXt"]:
        fields.append(
            _make_field(
                "PNG.tEXt",
                " | ".join(
                    text_chunks["PNG.tEXt"]
                )
            )
        )

    if text_chunks["PNG.iTXt"]:
        fields.append(
            _make_field(
                "PNG.iTXt",
                " | ".join(
                    text_chunks["PNG.iTXt"]
                )
            )
        )

    return fields


# ============================================================
# PUBLIC: extract
# ============================================================

def extract(file_bytes, filename):
    """
    Extract supported image metadata.

    Args:
        file_bytes: raw image bytes
        filename: original filename

    Returns:
        {
            "format": "jpeg" | "png",
            "fields": [...]
        }
    """

    image = _open_image(file_bytes)

    image_format = (
        image.format.lower()
        if image.format
        else ""
    )

    if image_format == "jpg":
        image_format = "jpeg"

    fields = []

    # EXIF fields
    fields.extend(
        _extract_exif(image)
    )

    # Embedded thumbnail
    thumbnail_field = _extract_thumbnail_field(
        image
    )

    if thumbnail_field:
        fields.append(thumbnail_field)

    # PNG-specific metadata
    if image_format == "png":
        fields.extend(
            _extract_png_metadata(
                file_bytes
            )
        )

    return {
        "format": image_format,
        "fields": fields,
    }


# ============================================================
# STRIPPING
# ============================================================

def _build_clean_exif(original_exif, keep):
    """
    Build a new EXIF object containing ONLY explicitly
    requested fields.
    """

    clean_exif = Image.Exif()

    # --------------------------------------------------------
    # Normal EXIF fields
    # --------------------------------------------------------

    normal_keys = [
        "DateTimeOriginal",
        "DateTimeDigitized",
        "Make",
        "Model",
        "LensModel",
        "SerialNumber",
        "Artist",
        "Copyright",
        "Software",
    ]

    for key in normal_keys:

        if key not in keep:
            continue

        tag_id = EXIF_TAG_IDS.get(key)

        if tag_id is None:
            continue

        value = original_exif.get(tag_id)

        if value is not None:
            clean_exif[tag_id] = value

    # --------------------------------------------------------
    # GPS
    # --------------------------------------------------------

    gps_keep_keys = {
        "GPS.GPSAltitude",
        "GPS.GPSTimeStamp",
    }

    keep_coordinates = (
        "GPS.Coordinates" in keep
    )

    keep_any_gps = (
        keep_coordinates
        or bool(
            gps_keep_keys.intersection(keep)
        )
    )

    if keep_any_gps:

        try:
            original_gps = original_exif.get_ifd(
                ExifTags.IFD.GPSInfo
            )

            if original_gps:

                clean_gps = {}

                # Coordinates
                if keep_coordinates:

                    for gps_name in [
                        "GPSLatitude",
                        "GPSLatitudeRef",
                        "GPSLongitude",
                        "GPSLongitudeRef",
                    ]:

                        tag_id = GPS_TAG_IDS.get(
                            gps_name
                        )

                        if (
                            tag_id is not None
                            and tag_id in original_gps
                        ):
                            clean_gps[tag_id] = (
                                original_gps[tag_id]
                            )

                # Altitude
                if "GPS.GPSAltitude" in keep:

                    for gps_name in [
                        "GPSAltitude",
                        "GPSAltitudeRef",
                    ]:

                        tag_id = GPS_TAG_IDS.get(
                            gps_name
                        )

                        if (
                            tag_id is not None
                            and tag_id in original_gps
                        ):
                            clean_gps[tag_id] = (
                                original_gps[tag_id]
                            )

                # GPS timestamp
                if "GPS.GPSTimeStamp" in keep:

                    tag_id = GPS_TAG_IDS.get(
                        "GPSTimeStamp"
                    )

                    if (
                        tag_id is not None
                        and tag_id in original_gps
                    ):
                        clean_gps[tag_id] = (
                            original_gps[tag_id]
                        )

                if clean_gps:
                    clean_exif[
                        ExifTags.IFD.GPSInfo
                    ] = clean_gps

        except Exception:
            pass

    return clean_exif


def _build_clean_png_info(file_bytes, keep):
    """
    Rebuild PNG textual metadata containing only explicitly
    selected tEXt/iTXt fields.
    """

    from PIL.PngImagePlugin import PngInfo

    png_info = PngInfo()

    chunks = _read_png_text_chunks(
        file_bytes
    )

    if "PNG.tEXt" in keep:

        for entry in chunks["PNG.tEXt"]:

            if ": " in entry:
                keyword, text = entry.split(
                    ": ",
                    1
                )

                png_info.add_text(
                    keyword,
                    text
                )

    if "PNG.iTXt" in keep:

        for entry in chunks["PNG.iTXt"]:

            if ": " in entry:
                keyword, text = entry.split(
                    ": ",
                    1
                )

                png_info.add_itxt(
                    keyword,
                    text
                )

    return png_info


# ============================================================
# PUBLIC: strip
# ============================================================

def strip(file_bytes, filename, keep=None):
    """
    Remove image metadata while preserving ONLY fields listed
    in `keep`.

    Examples:

        strip(data, "photo.jpg")

            -> removes all supported metadata

        strip(
            data,
            "photo.jpg",
            ["Make", "Model"]
        )

            -> keeps only Make + Model

    The returned value is raw image bytes.
    """

    if keep is None:
        keep = []

    keep = set(keep)

    image = _open_image(file_bytes)

    image_format = (
        image.format.lower()
        if image.format
        else ""
    )

    if image_format == "jpg":
        image_format = "jpeg"

    output = BytesIO()

    original_exif = image.getexif()

    clean_exif = _build_clean_exif(
        original_exif,
        keep
    )

    # ========================================================
    # JPEG
    # ========================================================

    if image_format == "jpeg":

        save_kwargs = {
            "format": "JPEG",
            "exif": clean_exif.tobytes(),
            "quality": 95,
        }

        # Embedded thumbnail is only retained if explicitly
        # requested.
        #
        # If we cannot safely preserve it, it is omitted.
        #
        # This is safer than accidentally keeping a hidden
        # thumbnail.
        if "EmbeddedThumbnail" in keep:

            try:
                thumbnail = _get_thumbnail(image)

                if thumbnail is not None:
                    clean_exif.set_thumbnail(
                        BytesIO(
                            _image_to_jpeg_bytes(
                                thumbnail
                            )
                        ).getvalue()
                    )

                    save_kwargs["exif"] = (
                        clean_exif.tobytes()
                    )

            except Exception:
                pass

        image.convert("RGB").save(
            output,
            **save_kwargs
        )

    # ========================================================
    # PNG
    # ========================================================

    elif image_format == "png":

        png_info = _build_clean_png_info(
            file_bytes,
            keep
        )

        save_kwargs = {
            "format": "PNG",
            "pnginfo": png_info,
        }

        exif_bytes = clean_exif.tobytes()

        if exif_bytes:
            save_kwargs["exif"] = exif_bytes

        image.save(
            output,
            **save_kwargs
        )

    else:
        raise ValueError(
            f"Unsupported image format: {image_format}"
        )

    return output.getvalue()


def _image_to_jpeg_bytes(image):
    """Convert a Pillow image into JPEG bytes."""
    output = BytesIO()

    image.convert("RGB").save(
        output,
        format="JPEG",
        quality=95
    )

    return output.getvalue()