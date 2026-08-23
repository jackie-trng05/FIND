# Student 3 Backend/API microservice (Application Management)
# Flask API that renders HTMX fragments, calls Ollama for AI screening,
# and proxies data operations to the student-3 database service.
# Container port 5003 (host 16011).

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY routes ./routes
COPY services ./services
COPY views ./views
COPY prompts ./prompts

EXPOSE 5003

CMD ["python", "app.py"]
