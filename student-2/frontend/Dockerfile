FROM python:3.11-slim

WORKDIR /app

COPY student-2/frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY student-2/frontend/app.py .
COPY student-2/frontend/templates/ templates/
COPY student-2/frontend/css/ css/
COPY shared/css/ /app/shared-css/
COPY shared/frontend/static/js/ /app/shared-js/

ENV PORT=3002
EXPOSE 3002

CMD ["python", "app.py"]
