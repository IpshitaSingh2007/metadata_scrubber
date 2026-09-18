import json
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from io import BytesIO
from backend.extractors.image_exif import extract, strip

app = Flask(__name__)
CORS(app)

RISK_MESSAGES = {
    "GPS.Coordinates": "This reveals your exact location",
    "GPS.GPSAltitude": "Reveals the elevation",
    "GPS.GPSTimeStamp": "Reveals the exact time your location was recorded",
    "DateTimeOriginal": "Reveals the exact time the photo was taken",
    "DateTimeDigitized": "Reveals when this file was digitized.",
    "Make": "Reveals the device brand used to take this photo",
    "Model": "Reveals the exact device model used.",
    "LensModel": "Reveals technical camera/lens details.",
    "SerialNumber": "Reveals the camera's unique serial number",
    "Artist": "This file may directly contain a name.",
    "Copyright": "This file may contain identifying text.",
    "EmbeddedThumbnail": "The hidden preview image inside this file may show content you thought you removed.",
    "Software": "Reveals what software was used to edit this file.",
    "PNG.tEXt": "Contains free-text data that may include personal notes or usernames.",
    "PNG.iTXt": "Contains free-text data that may include personal notes or usernames.",
}

def summarize(fields):
    for f in fields:
        f["message"] = RISK_MESSAGES.get(f["key"], f"This reveals: {f['label']}")
    return fields

@app.route("/scrub", methods=["POST"])
def scrub():
    file = request.files["file"]
    file_bytes = file.read()
    metadata = extract(file_bytes, file.filename)
    metadata["fields"] = summarize(metadata["fields"])
    return jsonify(metadata)

@app.route("/download", methods=["POST"])
def download():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    file_bytes = file.read()

    keep_raw = request.form.get("keep", "[]")
    try:
        keep = json.loads(keep_raw)
    except json.JSONDecodeError:
        keep = []

    cleaned = strip(file_bytes, file.filename, keep=keep)
    buffer = BytesIO(cleaned)
    buffer.seek(0)
    return send_file(buffer, mimetype="image/jpeg", as_attachment=True, download_name=f"cleaned_{file.filename}")

if __name__ == "__main__":
    app.run(debug=True)