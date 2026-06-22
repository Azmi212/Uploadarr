from flask import Flask, request, jsonify, render_template
import os
import requests
import shutil

app = Flask(__name__)

RADARR_URL = os.getenv("RADARR_URL", "http://192.168.1.146:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")
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
    chunk_index = request.form.get("chunkIndex")
    total_chunks = request.form.get("totalChunks")

    if not chunk or not filename or chunk_index is None or total_chunks is None:
        return jsonify({"error": "Données manquantes"}), 400

    chunk_index = int(chunk_index)
    total_chunks = int(total_chunks)

    file_chunk_folder = os.path.join(CHUNK_FOLDER, filename)
    os.makedirs(file_chunk_folder, exist_ok=True)

    chunk_path = os.path.join(file_chunk_folder, f"{chunk_index}")
    chunk.save(chunk_path)

    print(f"Chunk reçu : {chunk_index + 1}/{total_chunks} pour {filename}", flush=True)

    if chunk_index + 1 == total_chunks:
        final_path = os.path.join(UPLOAD_PATH, filename)

        print(f"Assemblage du fichier : {final_path}", flush=True)

        with open(final_path, "wb") as final_file:
            for i in range(total_chunks):
                part_path = os.path.join(file_chunk_folder, f"{i}")

                if not os.path.exists(part_path):
                    print(f"Chunk manquant : {part_path}", flush=True)
                    return jsonify({"error": f"Chunk manquant : {i}"}), 500

                with open(part_path, "rb") as part:
                    shutil.copyfileobj(part, final_file)

                os.remove(part_path)

        os.rmdir(file_chunk_folder)

        print(f"Upload terminé : {final_path}", flush=True)
        print(f"Notification Radarr sur : {UPLOAD_PATH}", flush=True)

        notify_radarr(UPLOAD_PATH)

        return jsonify({
            "success": True,
            "message": f"{filename} uploadé avec succès !"
        })

    return jsonify({
        "success": True,
        "message": f"Chunk {chunk_index + 1}/{total_chunks} reçu"
    })


def notify_radarr(path):
    try:
        if not RADARR_API_KEY:
            print("Erreur Radarr : RADARR_API_KEY est vide", flush=True)
            return

        headers = {
            "X-Api-Key": RADARR_API_KEY
        }

        payload = {
            "name": "DownloadedMoviesScan",
            "path": path
        }

        response = requests.post(
            f"{RADARR_URL}/api/v3/command",
            json=payload,
            headers=headers,
            timeout=10
        )

        print("Radarr status:", response.status_code, flush=True)
        print("Radarr response:", response.text, flush=True)

    except Exception as e:
        print(f"Erreur Radarr : {e}", flush=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
