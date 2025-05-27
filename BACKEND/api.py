import os
import smtplib
from dotenv import load_dotenv
from email.message import EmailMessage
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize AI client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Email credentials from .env
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")


def get_users():
    """
    Fetch random user data for testing.
    """
    url = "https://randomuser.me/api/?results=10"
    response = requests.get(url, timeout=20)
    return response.json() if response.status_code == 200 else {"error": f"Failed to fetch users: {response.status_code}"}


def get_response(text):
    try:
        system_message = """
        You are a patient speaking with a doctor. You are experiencing health issues such as mild fever, headache, fatigue, or any other common symptoms. 
        Respond to the doctor's questions with honesty, but keep in mind that you are just a patient who may or may not know the full details of their condition.
        Avoid providing medical advice or over-explaining. Just answer based on the common symptoms and your understanding.
        """
        
        print(f"Received user input: {text}")  # Debugging Line
        chat_completion = client(messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": text}
        ])
        print(f"API Response: {chat_completion}")  # Debugging Line

        return chat_completion.choices[0].message["content"]

    except Exception as e:
        print(f"Error occurred: {e}")  # Debugging Line
        return "Sorry, I could not generate a response at the moment."




def evaluate_response(doctor_response):
    """
    AI evaluates the doctor's response, assigns a score (0-10), and provides feedback.
    """
    evaluation_prompt = f"""
    Evaluate the following doctor's response:
    "{doctor_response}"
    
    Provide:
    1. A score (0-10) based on empathy, clarity, and professionalism.
    2. Constructive feedback.

    Format:
    Score: X
    Feedback: [Your feedback here]
    """

    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": evaluation_prompt}],
        model="llama3-8b-8192"
    )

    response_text = chat_completion.choices[0].message.content
    score = int(response_text.split("Score:")[1].split("\n")[0].strip())
    feedback = response_text.split("Feedback:")[1].strip()

    return score, feedback


def send_email(to_email, score, feedback):
    """
    Sends the doctor's evaluation score and feedback via email.
    """
    try:
        msg = EmailMessage()
        msg["Subject"] = "Your AI Evaluation Score & Feedback"
        msg["From"] = EMAIL_USER
        msg["To"] = to_email
        msg.set_content(f"Your Interaction Score: {score}/10\n\nFeedback: {feedback}")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print(f"Email sent successfully to {to_email}")

    except Exception as e:
        print(f"Email Error: {e}")


@app.route("/response", methods=["POST"])
def response():
    """
    Handles doctor-patient interaction, evaluates responses, and sends feedback.
    """
    try:
        data = request.get_json()
        doctor_response = data.get("text")
        doctor_email = data.get("email")

        if not doctor_response or not doctor_email:
            return jsonify({"error": "Missing doctor response or email"}), 400

        # Get chatbot response (patient simulation)
        chatbot_response = get_response(doctor_response)

        # Evaluate doctor response
        score, feedback = evaluate_response(doctor_response)

        # Send score & feedback via email
        send_email(doctor_email, score, feedback)

        return jsonify({
            "response": chatbot_response,
            "score": score,
            "feedback": feedback
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/test_users", methods=["GET"])
def test_users():
    """
    API endpoint to fetch test users.
    """
    try:
        response = get_users()
        users = response.get("results", [])
        return jsonify(users)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
