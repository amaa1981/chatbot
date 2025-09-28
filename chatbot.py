import requests
import json
import os
import logging # Import logging module
from flask import Flask, request, jsonify, render_template_string

# --- Flask App Setup ---
app = Flask(__name__)

# Configure logging for Flask
app.logger.setLevel(logging.INFO) # Set desired logging level (INFO, DEBUG, ERROR)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)


# --- Configuration ---
VLLM_API_BASE_URL = os.getenv("VLLM_API_BASE_URL", "https://llama-31-8b-instruct-oai-workshop.apps.cluster-tmgzh.tmgzh.sandbox305.opentlc.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-31-8b-instruct")

# Generation parameters
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "500"))
TOP_P = float(os.getenv("TOP_P", "0.9"))
# STREAM_RESPONSE is often not used for simple Flask APIs unless you implement SSE
STREAM_RESPONSE = os.getenv("STREAM_RESPONSE", "False").lower() == "true" 

# --- Chat History Management (per session, for a simple demo) ---
# IMPORTANT: This in-memory history is NOT multi-user safe and resets on server restart.
# For a production multi-user application, you would use Flask sessions, a database (Redis, etc.)
# For this simple demo, each client's history is maintained in their browser's JS and sent with each request.

# Default system message
DEFAULT_SYSTEM_MESSAGE = {"role": "system", "content": "You are a helpful and knowledgeable AI assistant. Provide concise and accurate answers."}

def get_completion(messages: list):
    """
    Sends a chat completion request to the vLLM API and returns the response.
    Expects a list of messages in OpenAI chat format.
    """
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": messages, # Use the provided messages list
        "temperature": TEMPERATURE,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "top_p": TOP_P,
        "stream": False # Set to False as current Flask API design doesn't handle streaming back to client
    }

    try:
        app.logger.info(f"Sending request to VLLM API: {VLLM_API_BASE_URL}/chat/completions with {len(messages)} messages.")
        response = requests.post(f"{VLLM_API_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=120)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()
        app.logger.info(f"Received response from VLLM API.")

        if data.get("choices") and data["choices"][0].get("message") and data["choices"][0]["message"].get("content"):
            return data["choices"][0]["message"]["content"].strip()
        else:
            app.logger.error(f"Unexpected response format from model API: {data}")
            return "Error: Unexpected response from model."

    except requests.exceptions.HTTPError as e:
        app.logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
        return f"Error from model API: {e.response.status_code} - {e.response.text}"
    except requests.exceptions.ConnectionError as e:
        app.logger.error(f"Connection Error: Could not connect to {VLLM_API_BASE_URL}. Is the server running and URL correct? Error: {e}")
        return "Error: Could not connect to the model service. Check backend logs for more details."
    except requests.exceptions.Timeout:
        app.logger.error("Timeout Error: Model service took too long to respond.")
        return "Error: Model service timed out."
    except Exception as e:
        app.logger.error(f"An unexpected error occurred: {e}")
        return f"Error: An unexpected error occurred: {e}"

# --- HTML Template for the Frontend ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Chatbot ({{ model_name }})</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #eef2f7; color: #333; display: flex; justify-content: center; align-items: flex-start; min-height: 100vh; }
        .chat-container { width: 100%; max-width: 800px; margin: 20px; background-color: #fff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: flex; flex-direction: column; }
        h1 { color: #2c3e50; text-align: center; margin-bottom: 20px; font-size: 1.8em; }
        .chat-box { flex-grow: 1; height: 500px; overflow-y: auto; border: 1px solid #dfe6e9; padding: 15px; margin-bottom: 20px; background-color: #f7f9fc; border-radius: 8px; scroll-behavior: smooth; }
        .message { margin-bottom: 15px; display: flex; }
        .user-message { justify-content: flex-end; }
        .assistant-message { justify-content: flex-start; }
        .message span { display: inline-block; padding: 12px 18px; border-radius: 20px; max-width: 75%; line-height: 1.5; font-size: 0.95em; }
        .user-message span { background-color: #007bff; color: white; border-bottom-right-radius: 5px; }
        .assistant-message span { background-color: #e2e6ea; color: #333; border-bottom-left-radius: 5px; }
        .input-area { display: flex; }
        #user-input { flex-grow: 1; padding: 12px 15px; border: 1px solid #ced4da; border-radius: 20px; margin-right: 10px; font-size: 1em; }
        #user-input:focus { outline: none; border-color: #007bff; box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25); }
        #send-button { padding: 12px 20px; background-color: #28a745; color: white; border: none; border-radius: 20px; cursor: pointer; font-size: 1em; }
        #send-button:hover { background-color: #218838; }
        #send-button:disabled { background-color: #6c757d; cursor: not-allowed; }
        .spinner { display: none; border: 4px solid rgba(0,0,0,.1); border-left-color: #007bff; border-radius: 50%; width: 24px; height: 24px; animation: spin 1s linear infinite; vertical-align: middle; margin-left: 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="chat-container">
        <h1>AI Chatbot ({{ model_name }})</h1>
        <div class="chat-box" id="chat-box">
            </div>
        <div class="input-area">
            <input type="text" id="user-input" placeholder="Type your message...">
            <button id="send-button">Send</button>
            <div class="spinner" id="spinner"></div>
        </div>
    </div>

    <script>
        const chatBox = document.getElementById('chat-box');
        const userInput = document.getElementById('user-input');
        const sendButton = document.getElementById('send-button');
        const spinner = document.getElementById('spinner');

        // Initial system message and greeting
        let chatHistory = [{{ default_system_message | safe }}];
        addMessage('assistant', 'Hello! How can I help you today?');

        function addMessage(sender, text) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + (sender === 'user' ? 'user-message' : 'assistant-message');
            // Basic HTML escaping for display
            const safeText = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
            messageDiv.innerHTML = `<span>${safeText}</span>`;
            chatBox.appendChild(messageDiv);
            chatBox.scrollTop = chatBox.scrollHeight; // Auto-scroll to bottom
        }

        async function sendMessage() {
            const message = userInput.value.trim();
            if (message === '') return;

            addMessage('user', message);
            chatHistory.push({ "role": "user", "content": message });
            userInput.value = '';
            sendButton.disabled = true;
            spinner.style.display = 'inline-block';

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ messages: chatHistory }) // Send full history
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
                }

                const data = await response.json();
                const assistantResponse = data.response;
                addMessage('assistant', assistantResponse);
                chatHistory.push({ "role": "assistant", "content": assistantResponse });

            } catch (error) {
                console.error('Error sending message:', error);
                addMessage('assistant', 'Error: Could not get a response from the model. Check console for details.');
            } finally {
                sendButton.disabled = false;
                spinner.style.display = 'none';
            }
        }

        sendButton.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        // Focus on input when page loads
        window.onload = function() {
            userInput.focus();
        };
    </script>
</body>
</html>
"""

# --- Flask Routes ---

@app.route("/")
def index():
    """Serves the main chatbot HTML page."""
    # Pass default_system_message to JS as JSON
    return render_template_string(HTML_TEMPLATE, model_name=MODEL_NAME,
                                  default_system_message=json.dumps(DEFAULT_SYSTEM_MESSAGE))

@app.route("/api/chat", methods=["POST"])
def chat_api():
    """Handles chat messages from the frontend."""
    data = request.get_json()
    if not data or "messages" not in data:
        app.logger.error("Invalid request: 'messages' not found in request body.")
        return jsonify({"error": "Invalid request body"}), 400

    messages_from_frontend = data["messages"]
    app.logger.info(f"Received chat request with {len(messages_from_frontend)} messages.")

    # Call the model completion function
    response_content = get_completion(messages_from_frontend)

    return jsonify({"response": response_content})

# --- Main entry point for Gunicorn ---
# This is typically how Gunicorn runs a Flask app.
# No need for app.run() here when using Gunicorn.
