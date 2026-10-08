from pathlib import Path

dockerfile = Path("demo-portal/managed-tools/netris-prometheus-exporter/Dockerfile")
content = dockerfile.read_text()
content = content.replace("COPY config.py netris_client.py sim_client.py record.py enricher.py exporter.py ./", "COPY app/config.py app/netris_client.py app/sim_client.py app/record.py app/enricher.py app/exporter.py ./")
dockerfile.write_text(content)
print("done")
