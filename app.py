import os
import subprocess
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

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

@app.route('/')
def index():
    return 'ADX-Backend is read to recieve Audio chunks and fingerprints. Up and Ready!'

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        print("Received upload request.")
        
        # Get audio chunk and .adx fingerprint file from the request
        audio_chunk = request.files.get('audio_chunk')
        adx_file = request.files.get('adx_file')

        if not audio_chunk or not adx_file:
            print("Error: Missing audio chunk or .adx file.")
            return jsonify({"error": "Missing audio chunk or .adx file"}), 400

        # Save the audio chunk to the temp folder
        audio_chunk_path = os.path.join(TEMP_AUDIO_PATH, audio_chunk.filename)
        audio_chunk.save(audio_chunk_path)
        print(f"Audio chunk saved to {audio_chunk_path}")

        # Save the adx file to the fingerprints folder
        adx_path = os.path.join(FINGERPRINT_PATH, adx_file.filename)
        adx_file.save(adx_path)
        print(f".adx file saved to {adx_path}")

        # Return a success message
        return jsonify({"message": "Files uploaded successfully"})
    except Exception as e:
        print(f"Error during file upload: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/match', methods=['POST'])
def match_audio():
    try:
        print("Received match request.")
        
        # Get the audio chunk and .adx file from the request
        data = request.get_json()
        audio_chunk_path = data.get('audio_chunk')
        adx_path = data.get('adx_file')

        if not audio_chunk_path or not adx_path:
            print("Error: Missing audio chunk or .adx file.")
            return jsonify({"error": "Missing audio chunk or .adx file"}), 400

        print(f"Matching audio chunk {audio_chunk_path} with .adx file {adx_path}.")

        # Ensure the paths point to the correct directories
        audio_chunk_path = os.path.join(TEMP_AUDIO_PATH, os.path.basename(audio_chunk_path))
        adx_path = os.path.join(FINGERPRINT_PATH, os.path.basename(adx_path))

        print(f"Corrected audio chunk path: {audio_chunk_path}")
        print(f"Corrected .adx path: {adx_path}")

        # Convert the .3gp audio file to .wav for audfprint
        wav_file_path = convert_to_wav(audio_chunk_path)

        if wav_file_path:
            print(f"Audio converted to {wav_file_path}")
            # Run matching in a separate thread with a timeout
            match_event = threading.Event()
            result = {"match_timecode": None}

            def match_with_timeout():
                result["match_timecode"] = match_audio_file(wav_file_path, adx_path)
                match_event.set()

            match_thread = threading.Thread(target=match_with_timeout)
            match_thread.start()

            # Wait for the match to complete or timeout
            match_event.wait(timeout=25)

            if result["match_timecode"] is not None:
                print(f"Match found at {result['match_timecode']} seconds.")
                clear_directories()  # Clear directories after successful match
                return jsonify({"match_timecode": result["match_timecode"]})
            else:
                print("Matching timed out or no match found.")
                clear_directories()  # Clear directories after timeout or no match
                return jsonify({"error": "Unable to match the audio in the given time"}), 408
        else:
            print("Failed to convert audio file.")
            clear_directories()  # Clear directories if conversion fails
            return jsonify({"error": "Failed to convert audio file"}), 500

    except Exception as e:
        print(f"Error during matching: {str(e)}")
        clear_directories()  # Clear directories on exception
        return jsonify({"error": str(e)}), 500

@app.route('/clear_files', methods=['POST'])
def clear_files():
    """Clear temp_audio and fingerprints directories."""
    try:
        clear_directories()
        print("Cleared temp_audio and fingerprints directories via /clear_files.")
        return jsonify({"message": "Directories cleared successfully"})
    except Exception as e:
        print(f"Error clearing directories: {str(e)}")
        return jsonify({"error": str(e)}), 500

def convert_to_wav(audio_file):
    try:
        # Define the path for the converted wav file in the same folder as the original audio chunk
        wav_file = os.path.join(TEMP_AUDIO_PATH, os.path.splitext(os.path.basename(audio_file))[0] + '.wav')

        # Convert the .3gp file to .wav using ffmpeg
        command = ["ffmpeg", "-i", audio_file, "-ar", "44100", "-ac", "1", wav_file]
        print(f"Running command: {' '.join(command)}")  # Debug log
        subprocess.run(command, capture_output=True, check=True)
        print(f"Converted audio chunk to {wav_file}")
        return wav_file
    except subprocess.CalledProcessError as e:
        print(f"Error converting file: {e}")
        return None

def match_audio_file(audio_file, adx_file):
    try:
        print(f"Matching {audio_file} with {adx_file} using audfprint...")

        # Ensure audfprint is run from its directory to avoid path issues
        command = [
            VENV_PYTHON, AUDFPRINT_SCRIPT,
            "match",
            "--dbase", adx_file,
            audio_file
        ]
        print(f"Running command: {' '.join(command)}")  # Debug log
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=os.path.join(BASE_DIR, "audfprint")  # Set working directory to audfprint
        )
        output = result.stdout
        error_output = result.stderr

        print("Audfprint output:", output)
        print("Audfprint errors:", error_output)

        # Parse audfprint output
        for line in output.splitlines():
            if "Matched" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "at":
                        matched_timecode = float(parts[i + 1])
                        print(f"Matched timecode: {matched_timecode}")
                        return matched_timecode

        print("No match found in the output.")
        return None
    except Exception as e:
        print(f"Error during audio match: {str(e)}")
        return None

def clear_directories():
    """Clear the temp_audio and fingerprints directories."""
    try:
        for folder in [TEMP_AUDIO_PATH, FINGERPRINT_PATH]:
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
        print("Cleared temp_audio and fingerprints directories.")
    except Exception as e:
        print(f"Error clearing directories: {str(e)}")

if __name__ == "__main__":
    print("Starting Flask server on port 5000...")
    app.run(debug=True, host='0.0.0.0', port=5000)
    