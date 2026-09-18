# Metadata Scrubber

A tool that extracts potentially sensitive metadata from image files, displays it to the user, and creates a cleaned copy with selected metadata removed.

## Current Scope

The current implementation focuses on **image metadata**, especially EXIF data in JPEG/JPG images and text metadata in PNG files.

The project is designed to be extended later to support other file formats such as PDF and DOCX.

## How It Works

1. User uploads an image.
2. The backend extracts supported metadata fields.
3. The metadata is displayed to the user along with its risk level.
4. All supported metadata fields are selected for removal by default.
5. The user can uncheck individual fields they want to keep.
6. The frontend sends the keys of the fields to keep to the backend.
7. The backend creates a scrubbed copy of the image.
8. The user can download the cleaned image.

### Checkbox Behaviour

The checkbox represents **whether the metadata should be removed**:

* ☑ Checked → **Remove** this metadata
* ☐ Unchecked → **Keep** this metadata

For example:

```text
☑ GPS.GPSLatitude
☑ GPS.GPSLongitude
☐ Model
☑ Software
☐ Artist
```

The frontend would send:

```python
keep = ["Model", "Artist"]
```

Only those fields are preserved in the scrubbed image.

## Metadata Currently Supported

### Location

| Metadata           | Description                            | Risk |
| ------------------ | -------------------------------------- | ---- |
| `GPS.GPSLatitude`  | GPS latitude of the recorded location  | High |
| `GPS.GPSLongitude` | GPS longitude of the recorded location | High |
| `GPS.GPSAltitude`  | Elevation at the recorded location     | Low  |
| `GPSTimeStamp`     | UTC time associated with the GPS fix   | Low  |

Latitude and longitude are intentionally kept as **separate fields** so the user can choose whether to keep or remove them independently.

### Timestamp

| Metadata            | Description                                 | Risk   |
| ------------------- | ------------------------------------------- | ------ |
| `DateTimeOriginal`  | Date and time the photo was taken           | Medium |
| `DateTimeDigitized` | Date and time the image was digitized/saved | Low    |

### Device

| Metadata       | Description                        | Risk   |
| -------------- | ---------------------------------- | ------ |
| `Make`         | Camera/device manufacturer         | Medium |
| `Model`        | Camera/device model                | Medium |
| `LensModel`    | Lens information                   | Low    |
| `SerialNumber` | Unique camera/device serial number | High   |

### Identity

| Metadata            | Description                                                                              | Risk   |
| ------------------- | ---------------------------------------------------------------------------------------- | ------ |
| `Artist`            | Free-text photographer/creator field                                                     | High   |
| `Copyright`         | Copyright/identifying text                                                               | High   |
| `EmbeddedThumbnail` | Embedded preview image that may contain information from an earlier version of the image | Medium |

The embedded thumbnail is checked by comparing the embedded thumbnail image against the main image rather than simply checking whether a metadata tag exists.

### Technical

| Metadata   | Description                            | Risk   |
| ---------- | -------------------------------------- | ------ |
| `Software` | Software used to create/edit the image | Low    |
| `PNG.tEXt` | PNG free-text metadata                 | Medium |
| `PNG.iTXt` | PNG international text metadata        | Medium |

## Risk Levels

Metadata fields are classified into three risk levels:

* **High** — potentially exposes highly sensitive or identifying information.
* **Medium** — may reveal useful identifying, contextual, or personal information.
* **Low** — generally less sensitive technical or contextual information.

High-risk fields are always marked as sensitive regardless of their current value.

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
│   │   ├── pdf_metadata.py
│   │   └── docx_metadata.py
│   │
│   ├── models/
│   │   └── metadata_schema.py
│   │
│   ├── tests/
│   │   ├── test_image_exif.py
│   │   ├── test_pdf_metadata.py
│   │   └── test_docx_metadata.py
│   │
│   ├── requirements.txt
│   └── main.py
│
├── api/
│   ├── routes/
│   │   ├── upload.py
│   │   ├── scrub.py
│   │   └── batch.py
│   │
│   ├── services/
│   │   └── risk_summary.py
│   │
│   ├── app.py
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadZone.jsx
│   │   │   ├── DownloadButton.jsx
│   │   │   ├── MetadataDiffView.jsx
│   │   │   └── RiskReportCard.jsx
│   │   │
│   │   ├── mock/
│   │   │   └── fakeMetadata.json
│   │   │
│   │   ├── api/
│   │   │   └── client.js
│   │   │
│   │   ├── App.jsx
│   │   └── index.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
├── samples/
│   ├── images/
│   │   └── sample_with_gps.jpg
│   ├── pdfs/
│   │   └── sample_with_author.pdf
│   └── docs/
│       └── sample_with_tracked_changes.docx
│
└── docs/
    ├── demo_script.md
    ├── metadata_field_reference.md
    └── architecture.md
```

## Backend Interface

The image extractor returns metadata using the following structure:

```python
{
    "format": "jpeg",
    "fields": [
        {
            "key": "GPS.GPSLatitude",
            "label": "GPS latitude",
            "value": "12.9698 N",
            "risk": "high",
            "category": "location",
            "sensitive": True
        }
    ]
}
```

Each metadata field contains:

* `key` — unique identifier used by the frontend and scrubber.
* `label` — human-readable field name.
* `value` — extracted metadata value.
* `risk` — `high`, `medium`, or `low`.
* `category` — metadata category.
* `sensitive` — whether the field is considered sensitive.

If a metadata field is not present in the uploaded file, it is omitted rather than returned as `null`.

## Scrubbing Interface

The backend scrubber accepts the original file bytes, filename, and a list of metadata keys that should be preserved:

```python
def strip(file_bytes, filename, keep=None):
    ...
```

Example:

```python
keep = [
    "Model",
    "Artist"
]
```

The resulting image will retain those selected fields while removing the supported metadata fields that were not selected.

An empty `keep` list means that all supported metadata is removed.

## Installation

### Backend

Navigate to the backend directory:

```bash
cd backend
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

The image metadata implementation requires:

```text
Pillow
numpy
```

### API

The API has its own requirements file:

```bash
cd api
pip install -r requirements.txt
```

### Frontend

Navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

## Development Notes

The metadata extraction and scrubbing logic is kept in the backend extractor rather than duplicated in the frontend.

The frontend should work with metadata using the field's exact `key`. This allows the same metadata identifier to be used when displaying fields, tracking checkbox selections, and sending the `keep` list to the backend.

For example:

```python
{
    "key": "GPS.GPSLatitude",
    ...
}
```

should remain exactly:

```text
GPS.GPSLatitude
```

throughout the extraction, UI, and scrubbing flow.

## Limitations

The current implementation focuses on the metadata fields defined in the project specification.

It does not guarantee removal of every possible piece of metadata from every image format or application-generated file.

Different image editors, cameras, and software may store metadata in different ways. The scrubber therefore targets the supported metadata fields explicitly defined by this project.

PDF and DOCX metadata extraction/scrubbing are planned extensions and are not part of the current image implementation.

## Future Extensions

Potential future work includes:

* PDF metadata extraction and scrubbing
* DOCX metadata extraction and scrubbing
* Batch file processing
* Additional image metadata formats
* More detailed risk analysis
* Additional metadata detection
* Improved preservation of selected metadata
* Expanded automated tests

## Team Workflow

The project uses separate Git branches for individual work.

The `main` branch contains the shared project code.

Feature branches can be used for isolated development before changes are merged into `main`.

Example:

```bash
git checkout -b person-a-exif
```

After completing a feature:

```bash
git add .
git commit -m "Implement image EXIF extraction and scrubbing"
git push origin person-a-exif
```

The changes can then be reviewed and merged into `main`.

## License

This project is developed as part of a hackathon project.


