FROM python:3.9-slim

WORKDIR /app

# Copy the app files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Expose the port
EXPOSE 8080

# Run the Flask app
CMD ["python", "app.py","gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]

