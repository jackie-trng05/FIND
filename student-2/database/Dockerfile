# Student 2 Database microservice (Job Posting Management)
# SQLite-backed Flask REST API. Container port 6002 (host 16009).

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY init_db.py .
COPY app.py .

# Create and seed the database at build time.
RUN python init_db.py

EXPOSE 6002

CMD ["python", "app.py"]
