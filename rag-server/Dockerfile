# FIND shared RAG HTTP server (default port 16070).
#
# Built from the repository root context so the corpus builder can read the repo
# evidence it indexes. rag_pipeline resolves APP_DIR to /app (the parent of
# /app/rag-server), so docs/, README.md and docker-compose.yml are copied there.
FROM python:3.11-slim

WORKDIR /app/rag-server

COPY rag-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rag-server/ .

# Repo evidence indexed into the corpus (resolved relative to APP_DIR=/app).
COPY docs/ /app/docs/
COPY README.md /app/README.md
COPY docker-compose.yml /app/docker-compose.yml

EXPOSE 16070

CMD ["python", "rag_http_server.py"]
