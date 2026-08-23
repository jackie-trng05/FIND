# Student 3 Database microservice (Application Management)
# SQLite-backed Flask REST API. Container port 6003 (host 16012).

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY init_db.py .
COPY app.py .

# Create and seed the database at build time.
RUN python init_db.py

EXPOSE 6003

CMD ["python", "app.py"]
