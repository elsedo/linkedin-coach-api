import os
import openai
import stripe
from flask import Flask, request, jsonify, redirect, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

openai.api_key = os.environ.get("OPENAI_API_KEY")
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")


@app.before_request
def block_mobile():
    ua = request.user_agent.string.lower()
    if 'mobile' in ua and request.endpoint in ["linkedin_info", "upload_page"]:
        return render_template("mobile_blocked.html")
@app.route("/")
def index(): return render_template("index.html")

@app.route("/linkedin-coach")
def linkedin_info(): return render_template("linkedin_coach.html")

@app.route("/linkedin-coach/upload")
def upload_page(): return render_template("upload.html")

@app.route("/linkedin-coach/result")
def result_page(): return render_template("result.html", result="(din AI-text)")

# === ROUTE 2: Skapa Stripe Checkout-session ===
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": os.environ.get("STRIPE_PRICE_ID"),  # t.ex. price_123abc
                "quantity": 1,
            }],
            mode="payment",
            success_url="https://YOUR_CLOUD_RUN_URL/success",
            cancel_url="https://YOUR_CLOUD_RUN_URL/cancel",
        )
        return redirect(session.url, code=303)
    except Exception as e:
        return jsonify(error=str(e)), 403

# === ROUTE 3: Efter lyckad betalning ===
@app.route("/success")
def success():
    return """
    <h2>Tack för ditt köp!</h2>
    <p>Nu kan du ladda upp din LinkedIn-profil som PDF för AI-analys.</p>
    <form action="/upload" method="POST" enctype="multipart/form-data">
        <input type="file" name="file">
        <button type="submit">Analysera</button>
    </form>
    """

# === ROUTE 4: Avbruten betalning ===
@app.route("/cancel")
def cancel():
    return "<h2>Köpet avbröts</h2><a href='/'>Försök igen</a>"

# === ROUTE 5: Ladda upp PDF och analysera med GPT ===
@app.route("/upload", methods=["POST"])
def upload_pdf():
    try:
        file = request.files["file"]
        content = file.read()

        import PyPDF2
        from io import BytesIO
        reader = PyPDF2.PdfReader(BytesIO(content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        prompt = f"""
Du är en professionell LinkedIn-coach. Här är användarens LinkedIn-profiltext:

{text}

Ge en analys:
1. Vad fungerar bra?
2. Vad bör förbättras?
3. Förslag på förbättrad sammanfattning.
        """

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # Eller gpt-4 om du har access
            messages=[
                {"role": "system", "content": "Du är en hjälpsam AI-coach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )

        return f"<h3>AI-feedback:</h3><pre>{response.choices[0].message.content.strip()}</pre>"

    except Exception as e:
        return f"<p>Fel: {str(e)}</p>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
