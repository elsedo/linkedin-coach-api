import os
import tempfile
import PyPDF2

from flask import Flask, request, jsonify
from google.cloud import storage
from google.cloud import aiplatform_v1

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

    # Extrahera text
    extracted_text = extract_text_from_pdf(BUCKET_NAME, file.filename)

    # AI-analys
    try:
        ai_feedback = analyze_with_vertex_ai(extracted_text)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "message": "Filen laddades upp och analyserades!",
        "feedback": ai_feedback
    }), 200


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
from google.cloud import aiplatform_v1

def analyze_with_vertex_ai(text):
    project = "plexiform-notch-465816-v5"
    location = "us-central1"
    model = "text-bison"

    endpoint = f"projects/{project}/locations/{location}/publishers/google/models/{model}"
    client = aiplatform_v1.PredictionServiceClient()

    instance = {
        "prompt": f"""
Du är en professionell LinkedIn-coach.
Här är en användares LinkedIn-profiltext:

{text}

Ge en analys:
1. Vad fungerar bra?
2. Vad bör förbättras?
3. Förbättrad version av sammanfattningstexten.
"""
    }

    parameters = {
        "temperature": 0.7,
        "maxOutputTokens": 512
    }

    response = client.predict(
        endpoint=endpoint,
        instances=[instance],        # ✅ Skickas som lista
        parameters=parameters        # ✅ Dict med valfria inställningar
    )

    return response.predictions[0]['content']
