# Student 2 Backend/API microservice (Job Posting Management)
# Flask API that renders HTMX fragments and calls Ollama. Container port 5002 (host 16008).

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY routes ./routes
COPY services ./services
COPY views ./views
COPY prompts ./prompts

EXPOSE 5002

CMD ["python", "app.py"]
