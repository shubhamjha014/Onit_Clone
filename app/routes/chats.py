from flask import Blueprint, request, jsonify
from app.services.auth_service import login_required

bp = Blueprint("chat", __name__, url_prefix="/api/chat")

@bp.route("/", methods=["POST"])
@login_required
def process_message():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data["message"].strip().lower()

    # Starter Skeleton Logic
    if user_message in ["hi", "hello", "hey", "greetings"]:
        bot_response = "Hello! 👋 I am your Legal Management AI. How can I help you today?"
    elif "help" in user_message:
        bot_response = "I can help you navigate matters, invoices, and tasks. What are you looking for?"
    else:
        bot_response = "I'm still learning! I only understand simple greetings like 'hi' or 'hello' right now."

    return jsonify({"response": bot_response})