FROM python:3.11-slim

WORKDIR /app

COPY shared/frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/frontend/app.py .
COPY shared/frontend/templates/ ./templates/
COPY shared/frontend/static/ ./static/
COPY shared/css/ /app/shared-css/

EXPOSE 3000

CMD ["python", "app.py"]