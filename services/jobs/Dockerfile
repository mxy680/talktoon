FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PORT=7871
EXPOSE 7871
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7871"]
