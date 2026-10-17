FROM python:3.11-slim

WORKDIR /app

COPY student-3/frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY student-3/frontend/app.py .
COPY student-3/frontend/templates/ ./templates/
COPY student-3/frontend/css/ ./css/
COPY shared/css/ /app/shared-css/
COPY shared/frontend/static/js/ /app/shared-js/

EXPOSE 3003

CMD ["python", "app.py"]
