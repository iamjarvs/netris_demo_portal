FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py netris_client.py sim_client.py record.py enricher.py exporter.py ./

EXPOSE 9101

CMD ["python", "app/exporter.py"]
