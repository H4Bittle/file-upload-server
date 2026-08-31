import os
import time
from pathlib import Path
from functools import wraps

from flask import (
    Flask, request, render_template, redirect,
    url_for, send_from_directory, abort, Response
)
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Config (all overridable via environment variables — see README)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", BASE_DIR / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 0 = unlimited. Default 10 GB per upload.
_max_mb = int(os.environ.get("MAX_UPLOAD_MB", "10240"))
if _max_mb > 0:
    app.config["MAX_CONTENT_LENGTH"] = _max_mb * 1024 * 1024

# If both are set, every route requires HTTP Basic Auth.
AUTH_USER = os.environ.get("UPLOAD_USER", "")
AUTH_PASS = os.environ.get("UPLOAD_PASS", "")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if AUTH_USER and AUTH_PASS:
            auth = request.authorization
            if not auth or auth.username != AUTH_USER or auth.password != AUTH_PASS:
                return Response(
                    "Authentication required", 401,
                    {"WWW-Authenticate": 'Basic realm="Upload Server"'}
                )
        return f(*args, **kwargs)
    return wrapper


def human_size(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def unique_dest(filename):
    dest = UPLOAD_DIR / filename
    stem, suffix = dest.stem, dest.suffix
    counter = 1
    while dest.exists():
        dest = UPLOAD_DIR / f"{stem}_{counter}{suffix}"
        counter += 1
    return dest


def list_files():
    files = []
    for p in UPLOAD_DIR.iterdir():
        if p.is_file():
            stat = p.stat()
            files.append({
                "name": p.name,
                "size": human_size(stat.st_size),
                "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
                "mtime_raw": stat.st_mtime,
            })
    files.sort(key=lambda f: f["mtime_raw"], reverse=True)
    return files


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
@auth_required
def index():
    return render_template("index.html", files=list_files())


@app.route("/upload", methods=["POST"])
@auth_required
def upload():
    uploaded = request.files.getlist("file")
    for f in uploaded:
        if f and f.filename:
            filename = secure_filename(f.filename)
            if not filename:
                continue
            f.save(unique_dest(filename))
    # AJAX requests get JSON; plain form fallback gets a redirect.
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"ok": True, "files": list_files()}
    return redirect(url_for("index"))


@app.route("/files/<path:filename>")
@auth_required
def download(filename):
    safe = secure_filename(filename)
    if not safe or not (UPLOAD_DIR / safe).is_file():
        abort(404)
    return send_from_directory(UPLOAD_DIR, safe, as_attachment=True)


@app.route("/delete/<path:filename>", methods=["POST"])
@auth_required
def delete(filename):
    safe = secure_filename(filename)
    target = UPLOAD_DIR / safe
    if target.is_file():
        target.unlink()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"ok": True}
    return redirect(url_for("index"))


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    debug = os.environ.get("DEBUG", "0") == "1"

    print(f"Uploads dir : {UPLOAD_DIR}")
    print(f"Basic auth  : {'ON' if (AUTH_USER and AUTH_PASS) else 'OFF (set UPLOAD_USER / UPLOAD_PASS to enable)'}")
    print(f"Serving on  : http://{host}:{port}")

    app.run(host=host, port=port, debug=debug)
