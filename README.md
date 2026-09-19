# Metadata Scrubber

A tool that extracts potentially sensitive metadata from files, shows the user what's exposed with a plain-English risk explanation, and creates a cleaned copy with selected metadata removed.

## Current Scope

The implementation currently supports:
- **Image metadata** — EXIF data in JPEG/JPG images, text metadata (tEXt/iTXt) in PNG files
- **PDF metadata** — document info dictionary fields (Title, Author, Subject, Creator, Producer, dates, Keywords) and XMP metadata detection

DOCX support remains a planned future extension.

## How It Works

1. User uploads a file (image or PDF).
2. The backend detects the actual file type from its content (not just the filename extension), then routes it to the correct extractor.
3. Supported metadata fields are extracted and returned with a risk level and plain-English explanation for each.
4. All supported metadata fields are selected for removal by default.
5. The user can uncheck individual fields they want to keep, or choose a quick preset (e.g. Legal, Social Media, Resume) that pre-selects sensible defaults for the field types.
6. The frontend sends the keys of the fields to **keep** to the backend.
7. The backend creates a scrubbed copy of the file, preserving only the selected fields.
8. The user can preview a before/after comparison and download the cleaned file.

### Checkbox Behaviour

The checkbox represents **whether the metadata should be removed**:

* ☑ Checked → **Remove** this metadata
* ☐ Unchecked → **Keep** this metadata

The frontend sends the inverse — the list of keys to **keep**:

```python
keep = ["Model", "Artist"]
```

Only those fields are preserved in the scrubbed file. An empty `keep` list removes all supported metadata.

## Metadata Currently Supported

### Images

#### Location

| Metadata            | Description                                  | Risk |
| -------------------- | --------------------------------------------- | ---- |
| `GPS.Coordinates`     | Combined GPS latitude/longitude of the file   | High |
| `GPS.GPSAltitude`     | Elevation at the recorded location            | Low  |
| `GPS.GPSTimeStamp`    | UTC time associated with the GPS fix          | Low  |

#### Timestamp

| Metadata            | Description                                 | Risk   |
| ------------------- | -------------------------------------------- | ------ |
| `DateTimeOriginal`  | Date and time the photo was taken            | Medium |
| `DateTimeDigitized` | Date and time the image was digitized/saved  | Low    |

#### Device

| Metadata       | Description                        | Risk   |
| -------------- | ------------------------------------ | ------ |
| `Make`         | Camera/device manufacturer          | Medium |
| `Model`        | Camera/device model                 | Medium |
| `LensModel`    | Lens information                    | Low    |
| `SerialNumber` | Unique camera/device serial number  | High   |

#### Identity

| Metadata            | Description                                                                              | Risk   |
| ------------------- | ------------------------------------------------------------------------------------------ | ------ |
| `Artist`            | Free-text photographer/creator field                                                      | High   |
| `Copyright`         | Copyright/identifying text                                                                | High   |
| `EmbeddedThumbnail` | Embedded preview image that may still show content from an earlier, edited/cropped version | Medium |

#### Technical

| Metadata   | Description                             | Risk   |
| ---------- | ------------------------------------------ | ------ |
| `Software` | Software used to create/edit the image    | Low    |
| `PNG.tEXt` | PNG free-text metadata                    | Medium |
| `PNG.iTXt` | PNG international text metadata           | Medium |

### PDFs

| Metadata       | Description                              | Risk   |
| -------------- | ------------------------------------------- | ------ |
| `Title`        | Document title                            | Low    |
| `Author`       | Document author                            | High   |
| `Subject`      | Document subject line                      | Low    |
| `Creator`      | Application that created the document      | Low    |
| `Producer`     | Software that produced the PDF             | Low    |
| `CreationDate` | When the document was originally created   | Medium |
| `ModDate`      | When the document was last modified        | Medium |
| `Keywords`     | Keywords/tags associated with the document | Medium |
| `XMP`          | Presence of embedded XMP metadata          | Medium |

XMP is currently detected and removed as a single field rather than broken into individual sub-fields.

## Risk Levels

Metadata fields are classified into three risk levels:

* **High** — potentially exposes highly sensitive or identifying information.
* **Medium** — may reveal useful identifying, contextual, or personal information.
* **Low** — generally less sensitive technical or contextual information.

High-risk fields are always marked as sensitive regardless of their current value.

**In progress:** in addition to per-field risk levels, an overall file-level risk score is being developed to summarize a file's total exposure in a single number/label, aggregated from all detected fields.

## Project Structure

```text
metadata-scrubber/
├── README.md
├── .gitignore
├── .env.example
│
├── backend/
│   ├── extractors/
│   │   ├── image_exif.py
│   │   └── pdf_metadata.py
│   │
│   ├── models/
│   │   └── metadata_schema.py
│   │
│   ├── tests/
│   │   └── test_image_exif.py
│   │
│   ├── requirements.txt
│   └── main.py
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
├── samples/
│   ├── images/
│   └── pdfs/
│
└── docs/
    └── metadata_field_reference.md
```

Note: the original `api/` folder (separate Flask app) was merged into `backend/main.py` early in development, since the project scope narrowed to a single combined API layer.

## Backend Interface

Both extractors return metadata using the same shared structure:

```python
{
    "format": "jpeg",  # or "pdf"
    "fields": [
        {
            "key": "GPS.Coordinates",
            "label": "GPS coordinates",
            "value": "12.9698 N, 79.1559 E",
            "risk": "high",
            "category": "location",
            "sensitive": True
        }
    ]
}
```

The API layer (`backend/main.py`) adds a `message` field with a plain-English risk explanation before returning results to the frontend, and trims the response to only the fields the frontend needs (`key`, `label`, `value`, `message`, `risk`).

If a metadata field is not present in the uploaded file, it is omitted rather than returned as `null`.

## API Endpoints

### `POST /scrub`

Accepts a file upload, detects its type (by content signature, not filename), extracts metadata using the appropriate extractor, and returns the field list with risk messages.

### `POST /download`

Accepts the original file plus a `keep` field (a JSON-stringified array of field keys to preserve), strips all other supported metadata, and returns the cleaned file as a download with the correct content type.

## Scrubbing Interface

```python
def strip(file_bytes, filename, keep=None):
    ...
```

Example:

```python
keep = ["Model", "Artist"]
```

The resulting file retains those selected fields while removing the supported metadata fields that were not selected. An empty `keep` list removes all supported metadata.

## File Type Detection

Uploaded files are identified by their actual content signature (magic bytes) rather than filename extension, so a mislabeled or renamed file is still routed correctly:

| Format | Signature                     |
| ------ | -------------------------------- |
| JPEG   | `FF D8 FF`                       |
| PNG    | `89 50 4E 47 0D 0A 1A 0A`         |
| PDF    | `%PDF`                            |

## Frontend Features

- Drag-and-drop or click-to-browse file upload (images and PDFs)
- Dashboard view summarizing detected metadata
- Plain-English explanations of what each sensitive field reveals
- Before/after comparison of the file's metadata
- File preview
- Quick presets (Legal, Social Media, Resume/Portfolio, Custom) that pre-select which fields to strip based on common use cases
- Per-field manual override via checkboxes
- Download of the cleaned file

## Installation

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Run from the **repository root** (not from inside `backend/`), since the app is run as a package:

```bash
python -m backend.main
```

The backend requires:
```text
Flask
flask-cors
Pillow
piexif
exifread
pypdf
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Development Notes

Metadata extraction and scrubbing logic is kept entirely in the backend extractors, never duplicated in the API layer or frontend.

The frontend works with metadata using the field's exact `key`, used consistently for display, checkbox tracking, and the `keep` list sent to the backend.

## Limitations

The current implementation targets the metadata fields explicitly defined by this project. It does not guarantee removal of every possible piece of metadata from every file format or application-generated file — different software may store metadata in nonstandard or additional ways.

DOCX metadata extraction/scrubbing is a planned extension and not yet implemented.

## Future Extensions

* DOCX metadata extraction and scrubbing
* Batch file processing
* File-level aggregate risk scoring (in progress)
* Expanded automated tests

## Team Workflow

The project uses separate Git branches for individual work, merged into `main`.

```bash
git checkout -b your-feature-branch
git add .
git commit -m "Describe your change"
git push origin your-feature-branch
```

## License

This project is developed as part of a hackathon project.