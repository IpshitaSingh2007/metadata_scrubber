def extract(file_bytes, filename):
    return {
        "format": "jpeg",
        "fields": [
            {"key": "GPS.Coordinates", "label": "GPS coordinates", "value": "12.9698 N, 79.1559 E", "risk": "high", "category": "location"},
            {"key": "GPS.GPSAltitude", "label": "GPS altitude", "value": "212m", "risk": "low", "category": "location"},
            {"key": "GPS.GPSTimeStamp", "label": "GPS timestamp", "value": "10:32:01 UTC", "risk": "low", "category": "location"},
            {"key": "DateTimeOriginal", "label": "Date/time photo taken", "value": "2026:09:18 10:32:01", "risk": "medium", "category": "timestamp"},
            {"key": "DateTimeDigitized", "label": "Date/time digitized", "value": "2026:09:18 10:35:12", "risk": "low", "category": "timestamp"},
            {"key": "Make", "label": "Camera manufacturer", "value": "Apple", "risk": "medium", "category": "device"},
            {"key": "Model", "label": "Camera model", "value": "iPhone 14 Pro", "risk": "medium", "category": "device"},
            {"key": "LensModel", "label": "Lens model", "value": "iPhone 14 Pro back triple camera", "risk": "low", "category": "device"},
            {"key": "SerialNumber", "label": "Camera serial number", "value": "C02XG2AAJGH5", "risk": "high", "category": "device"},
            {"key": "Artist", "label": "Photographer name", "value": "Jane Doe", "risk": "high", "category": "identity"},
            {"key": "Copyright", "label": "Copyright holder", "value": "Jane Doe Photography", "risk": "high", "category": "identity"},
            {"key": "EmbeddedThumbnail", "label": "Embedded thumbnail image", "value": "present (may show uncropped original)", "risk": "medium", "category": "identity"},
            {"key": "Software", "label": "Editing software used", "value": "Adobe Lightroom 13.0", "risk": "low", "category": "technical"},
            {"key": "PNG.tEXt", "label": "PNG text metadata", "value": "Comment: edited on device XYZ", "risk": "medium", "category": "technical"},
            {"key": "PNG.iTXt", "label": "PNG international text metadata", "value": "Author: jdoe_2019", "risk": "medium", "category": "technical"}
        ]
    }

def strip(file_bytes, filename, keep=[]):
    return file_bytes