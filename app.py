import os
import subprocess
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Allow all origins, change "*" to specific origin for production.

# Base paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMP_AUDIO_PATH = os.path.join(BASE_DIR, 'temp_audio')
FINGERPRINT_PATH = os.path.join(BASE_DIR, 'fingerprints')
AUDFPRINT_SCRIPT = os.path.join(BASE_DIR, 'audfprint', 'audfprint.py')

# Update the path to your virtual environment's Python executable
VENV_PYTHON = os.path.join(BASE_DIR, 'venv', 'Scripts', 'python.exe') if os.name == 'nt' else os.path.join(BASE_DIR, 'venv', 'bin', 'python')

# Create folders if they don't exist
os.makedirs(TEMP_AUDIO_PATH, exist_ok=True)
os.makedirs(FINGERPRINT_PATH, exist_ok=True)

@app.route('/api/')
def index():
    return 'ADX Flask Backend is Ready! usee `/api/upload` or `/api/match`.'

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        print("Received upload request.")
        
        # Get audio chunk and .adx fingerprint file from the request
        audio_chunk = request.files.get('audio_chunk')
        adx_file = request.files.get('adx_file')

        if not audio_chunk or not adx_file:
            return jsonify({"error": "Missing audio chunk or .adx file"}), 400

        # Save the audio chunk to the temp folder
        audio_chunk_path = os.path.join(TEMP_AUDIO_PATH, audio_chunk.filename)
        audio_chunk.save(audio_chunk_path)

        # Save the adx file to the fingerprints folder
        adx_path = os.path.join(FINGERPRINT_PATH, adx_file.filename)
        adx_file.save(adx_path)

        return jsonify({"message": "Files uploaded successfully"})
    except Exception as e:
        print(f"Error during file upload: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/match', methods=['POST'])
def match_audio():
    try:
        print("Received match request.")
        
        # Get the audio chunk and .adx file from the request
        data = request.get_json()
        audio_chunk_path = data.get('audio_chunk')
        adx_path = data.get('adx_file')

        if not audio_chunk_path or not adx_path:
            return jsonify({"error": "Missing audio chunk or .adx file"}), 400

        # Ensure the paths point to the correct directories
        audio_chunk_path = os.path.join(TEMP_AUDIO_PATH, os.path.basename(audio_chunk_path))
        adx_path = os.path.join(FINGERPRINT_PATH, os.path.basename(adx_path))

        # Convert the .3gp audio file to .wav for audfprint
        wav_file_path = convert_to_wav(audio_chunk_path)

        if wav_file_path:
            match_event = threading.Event()
            result = {"match_timecode": None}

            def match_with_timeout():
                result["match_timecode"] = match_audio_file(wav_file_path, adx_path)
                match_event.set()

            match_thread = threading.Thread(target=match_with_timeout)
            match_thread.start()

            match_event.wait(timeout=25)

            if result["match_timecode"] is not None:
                clear_directories()  # Clear directories after successful match
                return jsonify({"match_timecode": result["match_timecode"]})
            else:
                clear_directories()  # Clear directories after timeout or no match
                return jsonify({"error": "Unable to match the audio in the given time"}), 408
        else:
            clear_directories()  # Clear directories if conversion fails
            return jsonify({"error": "Failed to convert audio file"}), 500

    except Exception as e:
        print(f"Error during matching: {str(e)}")
        clear_directories()  # Clear directories on exception
        return jsonify({"error": str(e)}), 500

@app.route('/api/clear_files', methods=['POST'])
def clear_files():
    """Clear temp_audio and fingerprints directories."""
    try:
        clear_directories()
        return jsonify({"message": "Directories cleared successfully"})
    except Exception as e:
        print(f"Error clearing directories: {str(e)}")
        return jsonify({"error": str(e)}), 500

def convert_to_wav(audio_file):
    try:
        wav_file = os.path.join(TEMP_AUDIO_PATH, os.path.splitext(os.path.basename(audio_file))[0] + '.wav')
        command = ["ffmpeg", "-i", audio_file, "-ar", "44100", "-ac", "1", wav_file]
        subprocess.run(command, capture_output=True, check=True)
        return wav_file
    except subprocess.CalledProcessError as e:
        print(f"Error converting file: {e}")
        return None

def match_audio_file(audio_file, adx_file):
    try:
        command = [
            VENV_PYTHON, AUDFPRINT_SCRIPT,
            "match",
            "--dbase", adx_file,
            audio_file
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=os.path.join(BASE_DIR, "audfprint")
        )
        for line in result.stdout.splitlines():
            if "Matched" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "at":
                        return float(parts[i + 1])
        return None
    except Exception as e:
        print(f"Error during audio match: {str(e)}")
        return None

def clear_directories():
    try:
        for folder in [TEMP_AUDIO_PATH, FINGERPRINT_PATH]:
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
    except Exception as e:
        print(f"Error clearing directories: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
