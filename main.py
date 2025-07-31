import os
import tempfile
import PyPDF2
import openai

from flask import Flask, request, jsonify
from google.cloud import storage

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BUCKET_NAME = os.environ.get("BUCKET_NAME", "linkedin-coach-uploads")
openai.api_key = os.environ.get("OPENAI_API_KEY")  # 🔐 Lägg som miljövariabel i Cloud Run

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
        ai_feedback = analyze_with_gpt(extracted_text)
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

def analyze_with_gpt(text):
    prompt = f"""
Du är en professionell LinkedIn-coach. Här är en användares LinkedIn-profiltext:

{text}

Ge en analys:
1. Vad fungerar bra?
2. Vad bör förbättras?
3. En förbättrad version av sammanfattningstexten.
"""

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Du är en hjälpsam och professionell LinkedIn-coach."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=800
    )

    return response.choices[0].message.content.strip()
