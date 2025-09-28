import requests
import json
import os
from rich.console import Console # Optional, for pretty output
from rich.text import Text # Optional
from rich.box import MINIMAL # Optional

# --- Configuration ---
# Replace with your actual OpenShift Route URL
VLLM_API_BASE_URL = os.getenv("VLLM_API_BASE_URL", "https://llama-31-8b-instruct-oai-workshop.apps.cluster-tmgzh.tmgzh.sandbox305.opentlc.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-31-8b-instruct")

# Generation parameters
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "500"))
TOP_P = float(os.getenv("TOP_P", "0.9"))
STREAM_RESPONSE = os.getenv("STREAM_RESPONSE", "True").lower() == "true" # Set to False if you don't want streaming

# --- Optional: Rich Console Setup for better display ---
console = Console()

# --- Chat History Management ---
# Using a simple list to store messages in OpenAI chat format
chat_history = [
    {"role": "system", "content": "You are a helpful and knowledgeable AI assistant. Provide concise and accurate answers."}
]

def get_completion(user_message: str):
    """
    Sends a chat completion request to the vLLM API and returns the response.
    """
    global chat_history

    # Add user message to history
    chat_history.append({"role": "user", "content": user_message})

    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": chat_history, # Send the full chat history for context
        "temperature": TEMPERATURE,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "top_p": TOP_P,
        "stream": STREAM_RESPONSE
    }

    try:
        if STREAM_RESPONSE:
            full_response_content = ""
            with requests.post(f"{VLLM_API_BASE_URL}/chat/completions", headers=headers, json=payload, stream=True) as response:
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
                console.print("[bold green]Assistant:[/bold green]", end=" ")
                for chunk in response.iter_lines():
                    if chunk:
                        try:
                            # Decode and parse each chunk
                            decoded_chunk = chunk.decode('utf-8')
                            if decoded_chunk.startswith("data: "):
                                json_data = decoded_chunk[6:].strip()
                                if json_data == "[DONE]":
                                    break
                                data = json.loads(json_data)
                                if data.get("choices") and data["choices"][0].get("delta") and data["choices"][0]["delta"].get("content"):
                                    content_chunk = data["choices"][0]["delta"]["content"]
                                    console.print(content_chunk, end="")
                                    full_response_content += content_chunk
                        except json.JSONDecodeError:
                            # Sometimes chunks can be incomplete or non-JSON
                            pass
                console.print() # Newline after streamed content

            # Add assistant's full response to history
            chat_history.append({"role": "assistant", "content": full_response_content.strip()})
            return full_response_content.strip()

        else: # Non-streaming response
            response = requests.post(f"{VLLM_API_BASE_URL}/chat/completions", headers=headers, json=payload)
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
            data = response.json()

            if data.get("choices") and data["choices"][0].get("message") and data["choices"][0]["message"].get("content"):
                assistant_response = data["choices"][0]["message"]["content"].strip()
                chat_history.append({"role": "assistant", "content": assistant_response})
                return assistant_response
            else:
                console.print(f"[bold red]Error: Unexpected response format from model API.[/bold red]")
                console.print(f"[bold red]Full Response:[/bold red] {data}")
                return None

    except requests.exceptions.HTTPError as e:
        console.print(f"[bold red]HTTP Error: {e.response.status_code} - {e.response.text}[/bold red]")
        # Remove the last user message if there was an error
        chat_history.pop()
        return None
    except requests.exceptions.ConnectionError as e:
        console.print(f"[bold red]Connection Error: Could not connect to {VLLM_API_BASE_URL}. Is the server running and URL correct?[/bold red]")
        chat_history.pop()
        return None
    except requests.exceptions.Timeout:
        console.print("[bold red]Timeout Error: The request took too long to respond.[/bold red]")
        chat_history.pop()
        return None
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {e}[/bold red]")
        chat_history.pop()
        return None

def main():
    console.rule("[bold magenta]Simple AI Chatbot[/bold magenta]", style="dim")
    console.print(f"Connected to Model: [bold cyan]{MODEL_NAME}[/bold cyan]")
    console.print(f"API Base URL: [bold cyan]{VLLM_API_BASE_URL}[/bold cyan]")
    console.print("Type your message and press Enter. Type 'exit' or 'quit' to end the chat.")
    console.rule(style="dim")

    while True:
        try:
            user_input = console.input("[bold blue]You:[/bold blue] ")
            if user_input.lower() in ["exit", "quit"]:
                console.print("[bold yellow]Exiting chat. Goodbye![/bold yellow]")
                break

            console.print("Thinking...", style="dim")
            response = get_completion(user_input)
            if response is None:
                console.print("[bold red]There was an error getting a response. Please try again.[/bold red]")
            else:
                pass # Response already printed by get_completion for streaming

        except EOFError: # Ctrl+D
            console.print("\n[bold yellow]Exiting chat. Goodbye![/bold yellow]")
            break
        except KeyboardInterrupt: # Ctrl+C
            console.print("\n[bold yellow]Exiting chat. Goodbye![/bold yellow]")
            break

if __name__ == "__main__":
    main()
