from flask import Flask, request, jsonify, render_template
import os
import requests

app = Flask(__name__)

RADARR_URL = os.getenv("RADARR_URL", "http://192.168.1.146:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")
MOVIES_PATH = os.getenv("MOVIES_PATH", "/movies")
TV_PATH = os.getenv("TV_PATH", "/tv")
UPLOAD_PATH = os.getenv("UPLOAD_PATH", "/downloads")

CHUNK_FOLDER = "/tmp/chunks"
os.makedirs(CHUNK_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload/chunk", methods=["POST"])
def upload_chunk():
    chunk = request.files.get("chunk")
    filename = request.form.get("filename")
    chunk_index = int(request.form.get("chunkIndex"))
    total_chunks = int(request.form.get("totalChunks"))

    if not chunk or not filename:
        return jsonify({"error": "Données manquantes"}), 400

    file_chunk_folder = os.path.join(CHUNK_FOLDER, filename)
    os.makedirs(file_chunk_folder, exist_ok=True)

    chunk_path = os.path.join(file_chunk_folder, f"{chunk_index}")
    chunk.save(chunk_path)

    if chunk_index + 1 == total_chunks:
        final_path = os.path.join(UPLOAD_PATH, filename)
        with open(final_path, "wb") as final_file:
            for i in range(total_chunks):
                part_path = os.path.join(file_chunk_folder, f"{i}")
                with open(part_path, "rb") as part:
                    final_file.write(part.read())
                os.remove(part_path)
        os.rmdir(file_chunk_folder)

        notify_radarr(UPLOAD_PATH)

        return jsonify({"success": True, "message": f"{filename} uploadé avec succès !"})

    return jsonify({"success": True, "message": f"Chunk {chunk_index + 1}/{total_chunks} reçu"})

from flask import Flask, request, jsonify, render_template
import os
import requests

app = Flask(__name__)

RADARR_URL = os.getenv("RADARR_URL", "http://192.168.1.146:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")
MOVIES_PATH = os.getenv("MOVIES_PATH", "/movies")
TV_PATH = os.getenv("TV_PATH", "/tv")
UPLOAD_PATH = os.getenv("UPLOAD_PATH", "/downloads")

CHUNK_FOLDER = "/tmp/chunks"
os.makedirs(CHUNK_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload/chunk", methods=["POST"])
def upload_chunk():
    chunk = request.files.get("chunk")
    filename = request.form.get("filename")
    chunk_index = int(request.form.get("chunkIndex"))
    total_chunks = int(request.form.get("totalChunks"))

    if not chunk or not filename:
        return jsonify({"error": "Données manquantes"}), 400

    file_chunk_folder = os.path.join(CHUNK_FOLDER, filename)
    os.makedirs(file_chunk_folder, exist_ok=True)

    chunk_path = os.path.join(file_chunk_folder, f"{chunk_index}")
    chunk.save(chunk_path)

    if chunk_index + 1 == total_chunks:
        final_path = os.path.join(UPLOAD_PATH, filename)
        with open(final_path, "wb") as final_file:
            for i in range(total_chunks):
                part_path = os.path.join(file_chunk_folder, f"{i}")
                with open(part_path, "rb") as part:
                    final_file.write(part.read())
                os.remove(part_path)
        os.rmdir(file_chunk_folder)

        notify_radarr(UPLOAD_PATH)

        return jsonify({"success": True, "message": f"{filename} uploadé avec succès !"})

    return jsonify({"success": True, "message": f"Chunk {chunk_index + 1}/{total_chunks} reçu"})

def notify_radarr(path):
    try:
        headers = {"X-Api-Key": RADARR_API_KEY}
        payload = {
            "name": "DownloadedMoviesScan",
            "path": path
        }

        response = requests.post(
            f"{RADARR_URL}/api/v3/command",
            json=payload,
            headers=headers
        )

        print("Radarr status:", response.status_code)
        print("Radarr response:", response.text)

    except Exception as e:
        print(f"Erreur Radarr : {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
