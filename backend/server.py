import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime
from http import cookies as http_cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pymysql
from pymysql.cursors import DictCursor

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "puisi_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "puisi_db")
PORT = int(os.environ.get("PORT", "8000"))
# Base URL aset statis (CloudFront/S3). Dipakai untuk membentuk URL gambar puisi.
# Contoh: https://d1234abcd.cloudfront.net
# Kosongkan di lokal — frontend akan menangani fallback.
ASSET_BASE_URL = os.environ.get("ASSET_BASE_URL", "").rstrip("/")

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
SESSION_DIR = Path(os.environ.get("SESSION_DIR", BASE_DIR / "sessions"))
SESSION_TTL = 3600

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}

SID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")
PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return f"{salt}:{digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split(":", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return hmac.compare_digest(candidate, digest)


def db_connect() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        cursorclass=DictCursor,
        autocommit=True,
    )


def load_session(sid: str | None) -> dict | None:
    if not sid or not SID_PATTERN.fullmatch(sid):
        return None
    path = SESSION_DIR / f"{sid}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if data.get("expires", 0) < time.time():
        path.unlink(missing_ok=True)
        return None
    return data


def destroy_session(sid: str | None) -> None:
    if sid and SID_PATTERN.fullmatch(sid):
        (SESSION_DIR / f"{sid}.json").unlink(missing_ok=True)


class PuisiHandler(BaseHTTPRequestHandler):
    server_version = "MonolitikStateful/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        stamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{stamp}] {self.address_string()} {fmt % args}", flush=True)

    def do_GET(self):
        parsed = urlparse(self.path)
        action = (parse_qs(parsed.query).get("action") or [""])[0]
        if action == "daftar_puisi":
            self.handle_daftar_puisi()
        elif action == "me":
            self.handle_me()
        elif action == "":
            self.serve_static(parsed.path)
        else:
            self.send_json(404, {"ok": False, "message": "Aksi GET tidak dikenal"})

    def do_POST(self):
        parsed = urlparse(self.path)
        action = (parse_qs(parsed.query).get("action") or [""])[0]
        self._read_request_body()
        routes = {
            "register": self.handle_register,
            "login": self.handle_login,
            "logout": self.handle_logout,
            "submit_puisi": self.handle_submit_puisi,
        }
        handler = routes.get(action)
        if handler is None:
            self.send_json(404, {"ok": False, "message": "Aksi POST tidak dikenal"})
            return
        handler()

    def serve_static(self, path: str):
        entry = STATIC_FILES.get(path.rstrip("/") or "/")
        if entry is None:
            self.send_text(404, "404 Not Found")
            return
        fname, ctype = entry
        try:
            body = (FRONTEND_DIR / fname).read_bytes()
        except OSError:
            self.send_text(500, "500 Internal Server Error")
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, status: int, text: str):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status: int, payload: dict, set_cookie: str | None = None):
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()
        self.wfile.write(body)

    def _read_request_body(self):
        self._raw_body = b""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > 0:
            self._raw_body = self.rfile.read(length)

    def get_json_body(self) -> dict | None:
        try:
            data = json.loads(self._raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def clean_str(value, max_len: int) -> str:
        if not isinstance(value, str):
            return ""
        return value.strip()[:max_len]

    def get_session_cookie(self) -> str | None:
        jar = http_cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
        except http_cookies.CookieError:
            return None
        morsel = jar.get("SID")
        return morsel.value if morsel else None

    def require_session(self) -> tuple[str, dict] | None:
        sid = self.get_session_cookie()
        session = load_session(sid)
        if session is None:
            self.send_json(
                401,
                {"ok": False, "message": "Sesi tidak valid atau sudah berakhir. Silakan login."},
            )
            return None
        return sid, session

    def handle_register(self):
        body = self.get_json_body()
        if body is None:
            self.send_json(400, {"ok": False, "message": "Body JSON tidak valid"})
            return
        username = str(body.get("username", "")).strip()
        nama = str(body.get("nama", "")).strip()
        password = str(body.get("password", ""))
        if not USERNAME_PATTERN.fullmatch(username):
            self.send_json(
                400,
                {"ok": False, "message": "Username 3-50 karakter, hanya huruf, angka, _ . -"},
            )
            return
        if not (1 <= len(nama) <= 100):
            self.send_json(400, {"ok": False, "message": "Nama lengkap wajib diisi (max 100)"})
            return
        if len(password) < 6:
            self.send_json(400, {"ok": False, "message": "Password minimal 6 karakter"})
            return
        conn = db_connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cur.fetchone():
                    self.send_json(409, {"ok": False, "message": "Username sudah terdaftar"})
                    return
                cur.execute(
                    "INSERT INTO users (username, password, nama) VALUES (%s, %s, %s)",
                    (username, hash_password(password), nama),
                )
        finally:
            conn.close()
        self.send_json(201, {"ok": True, "message": f"Akun {username} berhasil didaftarkan"})

    def handle_login(self):
        body = self.get_json_body()
        if body is None:
            self.send_json(400, {"ok": False, "message": "Body JSON tidak valid"})
            return
        username = str(body.get("username", "")).strip()
        password = str(body.get("password", ""))
        conn = db_connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, username, password, nama FROM users WHERE username = %s", (username,)
                )
                row = cur.fetchone()
        finally:
            conn.close()
        if row is None or not verify_password(password, row["password"]):
            self.send_json(401, {"ok": False, "message": "Username atau password salah"})
            return
        sid = secrets.token_hex(32)
        now = time.time()
        data = {
            "user_id": row["id"],
            "username": row["username"],
            "nama": row["nama"],
            "created": now,
            "expires": now + SESSION_TTL,
        }
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        path = SESSION_DIR / f"{sid}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(path)
        cookie = f"SID={sid}; HttpOnly; Path=/; SameSite=Lax; Max-Age={SESSION_TTL}"
        self.send_json(
            200,
            {"ok": True, "message": "Login berhasil", "nama": row["nama"], "username": row["username"]},
            set_cookie=cookie,
        )

    def handle_logout(self):
        sid = self.get_session_cookie()
        destroy_session(sid)
        cookie = "SID=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0"
        self.send_json(200, {"ok": True, "message": "Logout berhasil"}, set_cookie=cookie)

    def handle_me(self):
        session = load_session(self.get_session_cookie())
        if session is None:
            self.send_json(200, {"ok": False, "message": "Belum login"})
            return
        self.send_json(
            200, {"ok": True, "username": session["username"], "nama": session["nama"]}
        )

    def handle_submit_puisi(self):
        auth = self.require_session()
        if auth is None:
            return
        _, session = auth
        body = self.get_json_body()
        if body is None:
            self.send_json(400, {"ok": False, "message": "Body JSON tidak valid"})
            return
        judul = str(body.get("judul", "")).strip()
        isi = str(body.get("isi", "")).strip()
        kategori = str(body.get("kategori", "")).strip()
        keyword = str(body.get("keyword", "")).strip()
        # Field baru: kutipan pendek untuk gambar, template yang dipilih, dan nama file gambar
        bait = self.clean_str(body.get("bait", ""), 500)
        gambar_file = self.clean_str(body.get("gambar_file", ""), 255)
        if not (1 <= len(judul) <= 150):
            self.send_json(400, {"ok": False, "message": "Judul wajib diisi (max 150)"})
            return
        if not (1 <= len(isi) <= 10_000):
            self.send_json(400, {"ok": False, "message": "Isi puisi wajib diisi (max 10000)"})
            return
        if not (1 <= len(kategori) <= 50):
            self.send_json(400, {"ok": False, "message": "Kategori wajib diisi (max 50)"})
            return
        # gambar_file boleh kosong (untuk dev lokal tanpa Lambda).
        # Regex: hanya izinkan path satu level (prefix/nama.ext), tanpa '..' atau leading '/'
        # Contoh valid:   "hasil-puisi/puisi-1234-abcd.jpg"
        # Contoh invalid: "../../etc/passwd", "/etc/passwd", "nama/../secret"
        if gambar_file and not re.fullmatch(r"[\w-][\w/-]*\.[\w]{1,10}", gambar_file):
            self.send_json(400, {"ok": False, "message": "Format gambar_file tidak valid"})
            return
        conn = db_connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO puisi "
                    "(user_id, judul, tgl_submit, isi, bait, kategori, keyword, gambar_file) "
                    "VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s)",
                    (
                        session["user_id"],
                        judul,
                        isi,
                        bait or None,
                        kategori,
                        keyword or None,
                        gambar_file or None,
                    ),
                )
                id_puisi = cur.lastrowid
        finally:
            conn.close()
        self.send_json(201, {"ok": True, "message": "Puisi berhasil dikirim", "id_puisi": id_puisi})

    def handle_daftar_puisi(self):
        auth = self.require_session()
        if auth is None:
            return
        _, session = auth
        conn = db_connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT p.id, p.judul, p.tgl_submit, p.kategori, p.isi, p.bait, "
                    "p.keyword, p.gambar_file, u.nama "
                    "FROM puisi p JOIN users u ON p.user_id = u.id "
                    "WHERE p.user_id = %s ORDER BY p.tgl_submit DESC",
                    (session["user_id"],),
                )
                rows = cur.fetchall()
        finally:
            conn.close()
        # Bentuk URL gambar lengkap agar frontend tinggal pakai di <img src>
        for row in rows:
            gf = row.get("gambar_file")
            row["gambar_url"] = f"{ASSET_BASE_URL}/{gf}" if ASSET_BASE_URL and gf else ""
        self.send_json(200, {"ok": True, "puisi": rows})


def wait_for_db():
    for attempt in range(1, 31):
        try:
            conn = db_connect()
            conn.close()
            print("Database terhubung.", flush=True)
            return
        except Exception as exc:
            print(f"Menunggu database... ({attempt}/30): {exc}", flush=True)
            time.sleep(2)
    raise SystemExit("Database tidak dapat dihubungi, server dihentikan.")


if __name__ == "__main__":
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    wait_for_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), PuisiHandler)
    print(f"Server monolitik stateful berjalan di 0.0.0.0:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
