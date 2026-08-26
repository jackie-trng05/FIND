FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY services/ ./services/
COPY views/ ./views/
COPY routes/ ./routes/
COPY prompts/ ./prompts/

EXPOSE 5001

CMD ["python", "app.py"]