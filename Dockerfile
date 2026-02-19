FROM python:3.12-slim

WORKDIR /app

# Dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le script
COPY truckplus_fr.py .

# Entrypoint
ENTRYPOINT ["python", "truckplus_fr.py"]
