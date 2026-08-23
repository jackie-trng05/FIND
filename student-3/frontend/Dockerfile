# Student 3 Frontend microservice (Application Management)
# Static Jinja2 renderer for the HTMX pages. Container port 3003 (host 16010).

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY templates/ templates/
COPY css/ css/

ENV PORT=3003
EXPOSE 3003

CMD ["python", "server.py"]
