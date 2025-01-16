````markdown
# ADX Flask Backend

=====================

## Overview

---

The ADX Flask Backend is a RESTful API built using Flask, a lightweight Python web framework. It utilizes the Audfprint library for audio fingerprinting and matching.

## Endpoints

---

### 1. Fingerprint Audio File

- **URL**: `/fingerprint`
- **Method**: `POST`
- **Request Body**: `audio_file` (binary audio file)
- **Response**: `fingerprint` (JSON object containing the audio fingerprint)

### 2. Match Audio Fingerprint

- **URL**: `/match`
- **Method**: `POST`
- **Request Body**: `fingerprint` (JSON object containing the audio fingerprint)
- **Response**: `match` (JSON object containing the matched audio file information)

## API Documentation

---

### Fingerprint Audio File

```bash
curl -X POST \
  http://localhost:5000/fingerprint \
  -H 'Content-Type: application/octet-stream' \
  -T audio_file.wav
```
````

### Match Audio Fingerprint

```bash
curl -X POST \
  http://localhost:5000/match \
  -H 'Content-Type: application/json' \
  -d '{"fingerprint": {"hash": "abc123", "confidence": 0.9}}'
```

## Installation

---

### Requirements

- Python 3.8+
- Flask 2.0+
- Audfprint 0.3+

### Setup

1. Clone the repository: `git clone https://github.com/your-username/adx-flask-backend.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `flask run`

## Contributing

---

Contributing is allowed only from the Post Office Digital Media Inc., associated. For more information, please contact us at:

- Email: [hello@postoffice.com](mailto:hello@postoffice.com)
- Phone: +91-9840157677
- Post Office Digital Media Technologies Inc.,
- 6, Somasundharam Street, T Nagar, Chennai, TamilNadu, India
