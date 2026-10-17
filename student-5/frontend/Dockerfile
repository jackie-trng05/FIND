FROM python:3.11-slim

WORKDIR /app

COPY student-5/frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY student-5/frontend/app.py .
COPY student-5/frontend/templates/ ./templates/
COPY shared/css/ /app/shared-css/
COPY shared/frontend/static/js/ /app/shared-js/

EXPOSE 3005

CMD ["python", "app.py"]
