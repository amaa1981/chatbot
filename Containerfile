# Use a Red Hat Universal Base Image (UBI) for Python
FROM registry.access.redhat.com/ubi8/python-39:latest

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the chatbot script
COPY chatbot.py .

# Set environment variables for the chatbot (these will be overridden by OpenShift Deployment)
ENV VLLM_API_BASE_URL="https://llama-31-8b-instruct-oai-workshop.apps.cluster-tmgzh.tmgzh.sandbox305.opentlc.com/v1" \
    MODEL_NAME="llama-31-8b-instruct" \
    MAX_OUTPUT_TOKENS="500" \
    TEMPERATURE="0.7" \
    TOP_P="0.9" \
    STREAM_RESPONSE="True"

# Command to run the chatbot when the container starts
CMD ["python3", "chatbot.py"]
