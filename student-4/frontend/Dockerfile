FROM python:3.11-slim

WORKDIR /app

COPY student-4/frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY student-4/frontend/app.py .
COPY student-4/frontend/templates/ ./templates/
COPY student-4/frontend/css/ ./css/
COPY shared/css/ /app/shared-css/
COPY shared/frontend/static/js/ /app/shared-js/

EXPOSE 3004

CMD ["python", "app.py"]
