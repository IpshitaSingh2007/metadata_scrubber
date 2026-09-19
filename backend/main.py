import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from io import BytesIO
from backend.extractors.image_exif import extract as extract_image, strip as strip_image, FIELD_INFO as IMAGE_FIELD_INFO
from backend.extractors.pdf_metadata import extract as extract_pdf, strip as strip_pdf

PDF_RISK_MESSAGES = {
    "Title": "Reveals the document's title.",
    "Author": "This may directly identify who created the document.",
    "Subject": "Reveals the document's subject line.",
    "Creator": "Reveals what application created this document.",
    "Producer": "Reveals what software produced this PDF.",
    "CreationDate": "Reveals when this document was originally created.",
    "ModDate": "Reveals when this document was last modified.",
    "Keywords": "Reveals keywords/tags associated with this document.",
    "XMP": "Contains additional embedded metadata that may include identifying information.",
}

app = Flask(__name__)
CORS(app)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit


def detect_file_type(file_bytes):
    """Identify file type by actual content signature, not filename."""
    if file_bytes.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    elif file_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    elif file_bytes.startswith(b'%PDF'):
        return 'pdf'
    else:
        return 'unknown'


def map_fields_for_frontend(fields, file_type):
    messages = PDF_RISK_MESSAGES if file_type == 'pdf' else {}
    return [
        {
            "key": field["key"],
            "label": field["label"],
            "value": field["value"],
            "message": messages.get(field["key"], field.get("message", f"This reveals: {field['label']}")),
            "risk": field["risk"],
        }
        for field in fields
    ]


@app.route("/scrub", methods=["POST"])
def scrub():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    file_bytes = file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": f"File too large (max {MAX_FILE_SIZE // (1024*1024)}MB)"}), 413

    file_type = detect_file_type(file_bytes)
    if file_type == 'unknown':
        return jsonify({"error": "Unsupported file type"}), 400

    try:
        if file_type == 'pdf':
            result = extract_pdf(file_bytes, file.filename)
        else:
            result = extract_image(file_bytes, file.filename)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to process file: {str(e)}"}), 500

    frontend_fields = map_fields_for_frontend(result["fields"],file_type)

    return jsonify({
        "format": result.get("format", file_type),
        "fields": frontend_fields
    })


@app.route("/download", methods=["POST"])
def download():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    file_bytes = file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": f"File too large (max {MAX_FILE_SIZE // (1024*1024)}MB)"}), 413

    file_type = detect_file_type(file_bytes)
    if file_type == 'unknown':
        return jsonify({"error": "Unsupported file type"}), 400

    keep_raw = request.form.get("keep", "[]")
    try:
        keep = json.loads(keep_raw)
        if not isinstance(keep, list):
            keep = []
    except json.JSONDecodeError:
        keep = []

    try:
        if file_type == 'pdf':
            # pdf_metadata.strip() validates keep against its own FIELD_INFO internally
            cleaned_bytes = strip_pdf(file_bytes, file.filename, keep)
        else:
            valid_keys = set(IMAGE_FIELD_INFO.keys())
            keep = [k for k in keep if k in valid_keys]
            cleaned_bytes = strip_image(file_bytes, file.filename, keep=keep)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to clean file: {str(e)}"}), 500

    buffer = BytesIO(cleaned_bytes)
    buffer.seek(0)

    mimetype_map = {'jpeg': 'image/jpeg', 'png': 'image/png', 'pdf': 'application/pdf'}
    mimetype = mimetype_map.get(file_type, 'application/octet-stream')

    return send_file(
        buffer,
        mimetype=mimetype,
        as_attachment=True,
        download_name=f"cleaned_{file.filename}"
    )


if __name__ == "__main__":
    app.run(debug=True)