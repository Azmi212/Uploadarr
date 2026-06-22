from flask import Flask, request, jsonify, render_template
import os
import re
import shutil
import requests
from pathlib import Path

app = Flask(__name__)

RADARR_URL = os.getenv("RADARR_URL", "http://192.168.1.146:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")
UPLOAD_PATH = os.getenv("UPLOAD_PATH", "/downloads")
MOVIES_PATH = os.getenv("MOVIES_PATH", "/movies")
RADARR_ROOT_FOLDER = os.getenv("RADARR_ROOT_FOLDER", "/movies")
RADARR_QUALITY_PROFILE_ID = os.getenv("RADARR_QUALITY_PROFILE_ID", "")

CHUNK_FOLDER = "/tmp/chunks"
os.makedirs(CHUNK_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_PATH, exist_ok=True)


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

    safe_filename = os.path.basename(filename)
    file_chunk_folder = os.path.join(CHUNK_FOLDER, safe_filename)
    os.makedirs(file_chunk_folder, exist_ok=True)

    chunk_path = os.path.join(file_chunk_folder, f"{chunk_index}")
    chunk.save(chunk_path)

    print(f"Chunk reçu : {chunk_index + 1}/{total_chunks} pour {safe_filename}", flush=True)

    if chunk_index + 1 == total_chunks:
        final_path = os.path.join(UPLOAD_PATH, safe_filename)

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

        cleaned_title = clean_movie_name(safe_filename)
        results = search_radarr(cleaned_title)

        return jsonify({
            "success": True,
            "message": f"{safe_filename} uploadé avec succès !",
            "filename": safe_filename,
            "path": final_path,
            "detectedTitle": cleaned_title,
            "results": results
        })

    return jsonify({
        "success": True,
        "message": f"Chunk {chunk_index + 1}/{total_chunks} reçu"
    })


@app.route("/import", methods=["POST"])
def import_movie():
    data = request.get_json()

    filename = data.get("filename")
    movie = data.get("movie")

    if not filename or not movie:
        return jsonify({"error": "Données d'import manquantes"}), 400

    source_path = os.path.join(UPLOAD_PATH, os.path.basename(filename))

    if not os.path.exists(source_path):
        return jsonify({"error": f"Fichier introuvable : {source_path}"}), 404

    try:
        radarr_movie = ensure_movie_exists(movie)

        movie_title = radarr_movie["title"]
        movie_year = radarr_movie["year"]
        movie_id = radarr_movie["id"]

        extension = Path(filename).suffix
        folder_name = f"{movie_title} ({movie_year})"
        target_folder = os.path.join(MOVIES_PATH, folder_name)
        target_filename = f"{movie_title} ({movie_year}){extension}"
        target_path = os.path.join(target_folder, target_filename)

        os.makedirs(target_folder, exist_ok=True)

        print(f"Déplacement : {source_path} → {target_path}", flush=True)
        shutil.move(source_path, target_path)

        rescan_movie(movie_id)

        return jsonify({
            "success": True,
            "message": f"Film importé : {target_filename}",
            "targetPath": target_path
        })

    except Exception as e:
        print(f"Erreur import : {e}", flush=True)
        return jsonify({"error": str(e)}), 500


def clean_movie_name(filename):
    name = Path(filename).stem

    name = name.replace(".", " ")
    name = name.replace("_", " ")
    name = name.replace("-", " ")

    patterns_to_remove = [
        r"\b720p\b",
        r"\b1080p\b",
        r"\b2160p\b",
        r"\b4k\b",
        r"\buhd\b",
        r"\bbluray\b",
        r"\bblu ray\b",
        r"\bwebrip\b",
        r"\bwebdl\b",
        r"\bweb dl\b",
        r"\bhdrip\b",
        r"\bdvdrip\b",
        r"\bfrench\b",
        r"\btruefrench\b",
        r"\bvf\b",
        r"\bvostfr\b",
        r"\bmulti\b",
        r"\bx264\b",
        r"\bx265\b",
        r"\bh264\b",
        r"\bh265\b",
        r"\bhevc\b",
        r"\baac\b",
        r"\bdts\b",
        r"\byts\b",
        r"\brarbg\b",
        r"\beztv\b",
    ]

    for pattern in patterns_to_remove:
        name = re.sub(pattern, " ", name, flags=re.IGNORECASE)

    name = re.sub(r"\s+", " ", name)
    name = name.strip()

    print(f"Titre nettoyé : {name}", flush=True)

    return name


def radarr_headers():
    if not RADARR_API_KEY:
        raise Exception("RADARR_API_KEY est vide")

    return {
        "X-Api-Key": RADARR_API_KEY
    }


def search_radarr(term):
    print(f"Recherche Radarr : {term}", flush=True)

    response = requests.get(
        f"{RADARR_URL}/api/v3/movie/lookup",
        params={"term": term},
        headers=radarr_headers(),
        timeout=15
    )

    print("Radarr lookup status:", response.status_code, flush=True)

    if response.status_code != 200:
        print("Radarr lookup response:", response.text, flush=True)
        return []

    movies = response.json()

    results = []

    for movie in movies[:8]:
        results.append({
            "title": movie.get("title"),
            "originalTitle": movie.get("originalTitle"),
            "year": movie.get("year"),
            "tmdbId": movie.get("tmdbId"),
            "titleSlug": movie.get("titleSlug"),
            "overview": movie.get("overview"),
            "images": movie.get("images", []),
            "remotePoster": movie.get("remotePoster"),
        })

    print(f"{len(results)} résultat(s) trouvé(s)", flush=True)

    return results


def get_existing_movie_by_tmdb(tmdb_id):
    response = requests.get(
        f"{RADARR_URL}/api/v3/movie",
        headers=radarr_headers(),
        timeout=15
    )

    if response.status_code != 200:
        raise Exception(f"Impossible de récupérer les films Radarr : {response.text}")

    movies = response.json()

    for movie in movies:
        if movie.get("tmdbId") == tmdb_id:
            print(f"Film déjà présent dans Radarr : {movie.get('title')}", flush=True)
            return movie

    return None


def get_quality_profile_id():
    if RADARR_QUALITY_PROFILE_ID:
        return int(RADARR_QUALITY_PROFILE_ID)

    response = requests.get(
        f"{RADARR_URL}/api/v3/qualityprofile",
        headers=radarr_headers(),
        timeout=15
    )

    if response.status_code != 200:
        raise Exception(f"Impossible de récupérer les profils qualité : {response.text}")

    profiles = response.json()

    if not profiles:
        raise Exception("Aucun profil qualité trouvé dans Radarr")

    profile_id = profiles[0]["id"]
    print(f"Profil qualité utilisé automatiquement : {profiles[0]['name']} / ID {profile_id}", flush=True)

    return profile_id


def ensure_movie_exists(movie):
    tmdb_id = movie.get("tmdbId")

    if not tmdb_id:
        raise Exception("tmdbId manquant")

    existing_movie = get_existing_movie_by_tmdb(tmdb_id)

    if existing_movie:
        return existing_movie

    quality_profile_id = get_quality_profile_id()

    payload = {
        "title": movie.get("title"),
        "qualityProfileId": quality_profile_id,
        "titleSlug": movie.get("titleSlug"),
        "images": movie.get("images", []),
        "tmdbId": tmdb_id,
        "year": movie.get("year"),
        "rootFolderPath": RADARR_ROOT_FOLDER,
        "monitored": True,
        "minimumAvailability": "released",
        "addOptions": {
            "searchForMovie": False
        }
    }

    print(f"Ajout du film dans Radarr : {movie.get('title')} ({movie.get('year')})", flush=True)

    response = requests.post(
        f"{RADARR_URL}/api/v3/movie",
        json=payload,
        headers=radarr_headers(),
        timeout=15
    )

    print("Radarr add movie status:", response.status_code, flush=True)
    print("Radarr add movie response:", response.text, flush=True)

    if response.status_code not in [200, 201]:
        raise Exception(f"Erreur ajout Radarr : {response.text}")

    return response.json()


def rescan_movie(movie_id):
    payload = {
        "name": "RescanMovie",
        "movieIds": [movie_id]
    }

    response = requests.post(
        f"{RADARR_URL}/api/v3/command",
        json=payload,
        headers=radarr_headers(),
        timeout=15
    )

    print("Radarr rescan status:", response.status_code, flush=True)
    print("Radarr rescan response:", response.text, flush=True)

    if response.status_code not in [200, 201]:
        raise Exception(f"Erreur scan Radarr : {response.text}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
