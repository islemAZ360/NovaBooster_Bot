FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Download playwright browsers (Chromium only to save space)
RUN playwright install chromium

COPY . .

# Run with gunicorn
CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
