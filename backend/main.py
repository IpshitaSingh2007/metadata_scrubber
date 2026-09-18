import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from io import BytesIO
from backend.extractors.image_exif import extract, strip, FIELD_INFO

app = Flask(__name__)
CORS(app)

# ============================================================
# CONFIGURATION
# ============================================================

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit

# ============================================================
# HELPERS
# ============================================================

def map_fields_for_frontend(fields):
    """
    Convert the field shape from extract() to what the frontend expects.

    extract() gives us:
        {
            "key": "GPS.GPSTimeStamp",
            "label": "GPS timestamp",
            "value": "14:27:07 UTC",
            "risk": "low",
            "category": "location",
            "sensitive": False,
            "message": "Reveals the time of the GPS fix",
        }

    Frontend needs BOTH value (the raw data) and message (the explanation),
    shown as separate columns.
    """
    return [
        {
            "key": field["key"],
            "label": field["label"],
            "value": field["value"],
            "message": field["message"],
            "risk": field["risk"],
        }
        for field in fields
    ]


# ============================================================
# ROUTES
# ============================================================

@app.route("/scrub", methods=["POST"])
def scrub():
    # Validate file presence
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    # Read file
    file_bytes = file.read()
    
    # Enforce size limit
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": f"File too large (max {MAX_FILE_SIZE // (1024*1024)}MB)"}), 413
    
    # Extract metadata
    try:
        result = extract(file_bytes, file.filename)
    except ValueError as e:
        # Handle unsupported file types gracefully
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        # Catch-all for unexpected errors
        return jsonify({"error": f"Failed to process file: {str(e)}"}), 500
    
    # Map to frontend format
    frontend_fields = map_fields_for_frontend(result["fields"])
    
    return jsonify({
        "format": result.get("format", "unknown"),
        "fields": frontend_fields
    })


@app.route("/download", methods=["POST"])
def download():
    # Validate file presence
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    file_bytes = file.read()
    
    # Enforce size limit
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": f"File too large (max {MAX_FILE_SIZE // (1024*1024)}MB)"}), 413
    
    # Parse and validate "keep" parameter
    keep_raw = request.form.get("keep", "[]")
    try:
        keep = json.loads(keep_raw)
        if not isinstance(keep, list):
            keep = []
    except json.JSONDecodeError:
        keep = []
    
    # Validate keep keys against known fields
    valid_keys = set(FIELD_INFO.keys())
    keep = [k for k in keep if k in valid_keys]  # Filter out invalid keys
    
    # Strip metadata
    try:
        cleaned_bytes = strip(file_bytes, file.filename, keep=keep)
    except ValueError as e:
        # Handle unsupported formats
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to clean file: {str(e)}"}), 500
    
    # Prepare download
    buffer = BytesIO(cleaned_bytes)
    buffer.seek(0)
    
    # Determine output mimetype based on original format
    mimetype = "image/jpeg"  # Default
    if file.filename.lower().endswith(".png"):
        mimetype = "image/png"
    
    return send_file(
        buffer,
        mimetype=mimetype,
        as_attachment=True,
        download_name=f"cleaned_{file.filename}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)