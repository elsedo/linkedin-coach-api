import PyPDF2
from google.cloud import storage, aiplatform
from flask import Flask, request, jsonify
import os
import tempfile
from flask import Flask, request, jsonify
from google.cloud import storage
import os
import tempfile

from flask_cors import CORS
app = Flask(__name__)
CORS(app)

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

def extract_text_from_pdf(bucket_name, file_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    with tempfile.NamedTemporaryFile() as temp_file:
        blob.download_to_filename(temp_file.name)
        reader = PyPDF2.PdfReader(temp_file.name)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

def analyze_with_vertex_ai(text):
    aiplatform.init(project=os.environ["GOOGLE_CLOUD_PROJECT"], location="europe-north1")
    model = aiplatform.TextGenerationModel.from_pretrained("text-bison@001")

    prompt = f"""Du är en professionell LinkedIn-coach.
Här är en användares LinkedIn-profiltext:

{text}

Ge en analys:
1. Vad fungerar bra?
2. Vad bör förbättras?
3. Förbättrad version av sammanfattningstexten."""

    response = model.predict(prompt=prompt, temperature=0.7, max_output_tokens=512)
    return response.text
