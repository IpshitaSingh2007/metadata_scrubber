# Metadata Scrubber

A tool that extracts potentially sensitive metadata from files, shows the user what's exposed with a plain-English risk explanation and an overall risk score, and creates a cleaned copy with selected metadata removed.

## Current Scope

The implementation currently supports:
- **Image metadata** — EXIF data in JPEG/JPG images, text metadata (tEXt/iTXt) in PNG files
- **PDF metadata** — document info dictionary fields (Title, Author, Subject, Creator, Producer, dates, Keywords) and XMP metadata detection
- **File-level risk scoring** — an overall 0–100 score and risk level for each scanned file, shown in the frontend

DOCX support remains a planned future extension.

## How It Works

1. User uploads a file (JPG, PNG or PDF). The frontend rejects other file types before upload.
2. The backend detects the actual file type from its content (not just the filename extension), then routes it to the correct extractor.
3. Supported metadata fields are extracted and returned with a risk level and plain-English explanation for each, plus an overall file risk score.
4. All supported metadata fields are selected for removal by default (the **Legal** preset).
5. The user can uncheck individual fields they want to keep, or choose a quick preset (Legal, Social Media, Resume/Portfolio) that pre-selects sensible defaults. Editing a checkbox by hand switches the preset to **Custom**.
6. The frontend sends the keys of the fields to **keep** to the backend.
7. The backend creates a scrubbed copy of the file, preserving only the selected fields.
8. The user downloads the cleaned file (`cleaned_<original name>`).

### Checkbox Behaviour

The checkbox represents **whether the metadata should be removed**:

* ☑ Checked → **Remove** this metadata
* ☐ Unchecked → **Keep** this metadata (shown with a green "preserved" tag)

The frontend sends the inverse — the list of keys to **keep**:

```python
keep = ["Model", "Artist"]
```

Only those fields are preserved in the scrubbed file. An empty `keep` list removes all supported metadata.

### Presets

| Preset | Removes | Keeps |
| --- | --- | --- |
| **Legal (Remove Everything)** | Every detected field | Nothing |
| **Social Media** | Location and device/camera fields, plus **any high-risk field** (e.g. PDF `Author`, image `Artist`/`Copyright`) | Timestamps, software, and low/medium-risk fields |
| **Resume / Portfolio** | Location fields, plus **any high-risk field** | Camera specs, software, timestamps |
| **Custom Selection** | Whatever the user ticks | Everything else |

The Social Media and Resume presets always strip high-risk fields, so identifying fields such as `Author`, `Artist`, `Copyright` and `SerialNumber` are not silently preserved.

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

### Per-field risk

Each metadata field is classified into one of three risk levels:

* **High** — potentially exposes highly sensitive or identifying information.
* **Medium** — may reveal useful identifying, contextual, or personal information.
* **Low** — generally less sensitive technical or contextual information.

High-risk fields are always marked as sensitive regardless of their current value.

### Overall file risk score

Each `/scrub` response includes a file-level summary aggregated from all detected fields:

* `overall_score` — a number from 0 to 100
* `overall_level` — `LOW`, `MEDIUM`, `HIGH` or `CRITICAL`

The frontend shows these in the **Risk Score** panel (gauge, level tag, and a list of the kinds of personal information found). Levels are colour-coded: Low (green), Medium (amber), High (red), Critical (dark red).

If a response doesn't include `overall_score`, the frontend falls back to estimating a score from the per-field risks (High = 25, Medium = 12, Low = 5 points each, capped at 100; 70+ is High, 35+ is Medium).

<!-- TODO: document the backend's exact scoring formula and level thresholds here. -->

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

The API layer (`backend/main.py`) adds a `message` field with a plain-English risk explanation to each field, trims each field to only what the frontend needs (`key`, `label`, `value`, `message`, `risk`), and adds the file-level `overall_score` and `overall_level`.

If a metadata field is not present in the uploaded file, it is omitted rather than returned as `null`.

## API Endpoints

The frontend calls the API at `http://127.0.0.1:5000` (set by `API_BASE` at the top of `frontend/src/App.jsx`).

### `POST /scrub`

Accepts a file upload (`multipart/form-data`, field `file`), detects its type (by content signature, not filename), extracts metadata using the appropriate extractor, and returns the field list with risk messages and the overall risk score.

```json
{
  "overall_score": 100,
  "overall_level": "CRITICAL",
  "fields": [
    {
      "key": "Author",
      "label": "Author",
      "value": "Jane Doe",
      "message": "Author or ownership details are included.",
      "risk": "high"
    }
  ]
}
```

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

The frontend also does a quick check before upload and only accepts `.jpg`, `.jpeg`, `.png` and `.pdf` files. The backend's content-based check remains the source of truth.

## Frontend Features

- Drag-and-drop or click-to-browse file upload for JPG, PNG and PDF, with a clear message for unsupported file types
- **Risk Score panel** with a gauge, overall risk level, and a plain-English list of the kinds of personal information found (location, device, timestamps, author, software)
- Per-field risk badges and explanations of what each field reveals
- Quick presets (Legal, Social Media, Resume/Portfolio, Custom) that pre-select which fields to strip based on common use cases
- Per-field manual override via checkboxes, with "preserved" tags on fields that will be kept
- Live summary of how many fields will be removed and kept
- Download of the cleaned file
- Responsive layout: the risk panel sits beside the scrubber on desktop and moves below it on tablet and mobile

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

Make sure the backend is running on port 5000 first. If you change the port, update `API_BASE` in `frontend/src/App.jsx`.

## Manual Testing Checklist

1. Click **browse files** (not drag and drop) and confirm PDFs appear in the file picker.
2. Upload a PDF (e.g. `JRC_Report.pdf`) and scrub it. The Risk Score gauge, level and risk list should appear.
3. Switch to **Social Media**. `Author` should be checked for removal, while Title, Subject, Creator and Producer stay preserved.
4. Upload a JPG or PNG and confirm GPS and device fields are removed under Social Media.
5. Download the cleaned file, open it, and confirm the removed fields are gone.
6. Try dropping an unsupported file (e.g. `.gif`) and confirm you get an "Unsupported file type" message.

## Development Notes

Metadata extraction and scrubbing logic is kept entirely in the backend extractors, never duplicated in the API layer or frontend.

The frontend works with metadata using the field's exact `key`, used consistently for display, checkbox tracking, and the `keep` list sent to the backend.

The frontend prefers the backend's `overall_score` and `overall_level` for the Risk Score panel and only estimates its own score when they are missing.

## Limitations

The current implementation targets the metadata fields explicitly defined by this project. It does not guarantee removal of every possible piece of metadata from every file format or application-generated file — different software may store metadata in nonstandard or additional ways.

The frontend groups fields into categories (location, device, author, and so on) by matching keywords in each field's key and label, because `category` is not part of the trimmed `/scrub` response. This drives the presets and the risk list, so unusual field names can land in "other", and some fields are grouped by their first matching keyword (for example, `GPS.GPSTimeStamp` is treated as a timestamp rather than a location field). Including `category` in the API response would make this exact.

Only JPG, PNG and PDF files are supported. DOCX metadata extraction/scrubbing is a planned extension and not yet implemented.

## Future Extensions

* DOCX metadata extraction and scrubbing
* Batch file processing
* Before/after metadata comparison and file preview
* Include `category` in the `/scrub` response so the frontend doesn't need to infer it
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
