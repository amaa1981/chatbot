# Use a Red Hat Universal Base Image (UBI) for Python
FROM registry.access.redhat.com/ubi8/python-39:latest

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
RUN pip install --no-cache-dir -r Flask requests gunicorn

# Copy the chatbot script
COPY chatbot.py .

# Set default environment variables (will be overridden by OpenShift Deployment)
ENV VLLM_API_BASE_URL="https://llama-31-8b-instruct-oai-workshop.apps.cluster-tmgzh.tmgzh.sandbox305.opentlc.com/v1" \
    MODEL_NAME="llama-31-8b-instruct" \
    MAX_OUTPUT_TOKENS="500" \
    TEMPERATURE="0.7" \
    TOP_P="0.9" \
    STREAM_RESPONSE="False" \
    FLASK_APP="chatbot.py" 

# Expose the port Gunicorn will listen on
EXPOSE 8080

# Command to run the application using Gunicorn
# 'chatbot:app' means the 'app' Flask instance from 'chatbot.py'
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "chatbot:app"]
