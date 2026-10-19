# FIND shared multi-agent HTTP server (default port 16080).
#
# Self-contained build context: the server only calls the student database
# services and the LLM endpoint over the network, and reads no repo files.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py coordinator.py workflow_runner.py ./
COPY agents/ ./agents/
COPY prompts/ ./prompts/

EXPOSE 16080

CMD ["python", "app.py"]
