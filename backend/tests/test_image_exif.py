import os
from backend.extractors.image_exif import extract, strip

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "samples", "images")

GPS_PHOTO = os.path.join(SAMPLE_DIR, "gps_sample.jpg")
CLEAN_PHOTO = os.path.join(SAMPLE_DIR, "clean_sample.jpg")
OUTPUT_PATH = "/tmp/scrubbed_test_output.jpg"


def _load_file(path):
    with open(path, "rb") as f:
        return f.read()


def test_extract_finds_sensitive_fields():
    result = extract(_load_file(GPS_PHOTO), GPS_PHOTO)
    sensitive_keys = [f["key"] for f in result["fields"] if f["sensitive"]]

    assert "GPS.Coordinates" in sensitive_keys


def test_strip_removes_sensitive_fields():
    original = extract(_load_file(GPS_PHOTO), GPS_PHOTO)
    sensitive_before = [f["key"] for f in original["fields"] if f["sensitive"]]

    cleaned_bytes = strip(_load_file(GPS_PHOTO), GPS_PHOTO)

    with open(OUTPUT_PATH, "wb") as f:
        f.write(cleaned_bytes)

    after = extract(cleaned_bytes, OUTPUT_PATH)
    keys_after = [f["key"] for f in after["fields"]]

    for key in sensitive_before:
        assert key not in keys_after


def test_clean_file_has_no_sensitive_fields():
    result = extract(_load_file(CLEAN_PHOTO), CLEAN_PHOTO)
    sensitive_keys = [f["key"] for f in result["fields"] if f["sensitive"]]

    assert sensitive_keys == []


def test_strip_does_not_corrupt_image():
    cleaned_bytes = strip(_load_file(GPS_PHOTO), GPS_PHOTO)

    with open(OUTPUT_PATH, "wb") as f:
        f.write(cleaned_bytes)

    assert os.path.exists(OUTPUT_PATH)
    assert os.path.getsize(OUTPUT_PATH) > 0


def test_strip_can_keep_specific_fields():
    cleaned_bytes = strip(_load_file(GPS_PHOTO), GPS_PHOTO, keep=["Make", "Model"])
    after = extract(cleaned_bytes, "kept_fields_test.jpg")
    keys_after = [f["key"] for f in after["fields"]]

    assert "GPS.Coordinates" not in keys_after

def test_png_metadata_detected():
    png_path = os.path.join(SAMPLE_DIR, "png_sample.png")
    result = extract(_load_file(png_path), png_path)

    keys = [f["key"] for f in result["fields"]]
    assert any(k.startswith("PNG.") for k in keys)