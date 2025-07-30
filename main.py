from flask import Flask, request, jsonify
from google.cloud import storage
import os
import tempfile

app = Flask(__name__)

BUCKET_NAME = os.environ.get("BUCKET_NAME", "linkedin-coach-uploads")

@app.route("/", methods=["GET"])
def index():
    return "LinkedIn Coach API is running!"

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return "No file part", 400
    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    with tempfile.NamedTemporaryFile() as temp:
        file.save(temp.name)
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(file.filename)
        blob.upload_from_filename(temp.name)

    return jsonify({"message": "File uploaded successfully"}), 200
