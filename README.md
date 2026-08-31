# Monolithic-Stateful-AWS-Deployment

Tugas PACS262521 - Pengembangan Perangkat Lunak Scalable: membangun aplikasi **monolitik stateful** sebagai baseline ("ground truth") sebelum memahami arsitektur stateless dan horizontal scaling.

## Arsitektur

- **Backend**: Python murni (`http.server` stdlib) dalam **satu file** `backend/server.py`, tanpa framework. Routing single-path: semua aksi lewat `/?action=<aksi>`.
- **Database**: MySQL 8 (container `db`), tabel `users` dan `puisi` dengan Foreign Key `puisi.user_id → users.id`.
- **Session**: server-side **local session** berbasis file JSON di direktori `sessions/` milik container (stateful — mati saat container restart, terikat pada satu mesin). Tidak ada JWT.
- **Frontend**: HTML/CSS/JS murni tanpa framework, berkomunikasi via `fetch()` (same-origin, cookie dikelola browser otomatis).
- **Password**: hash PBKDF2-HMAC-SHA256 + salt acak (stdlib `hashlib`).

## Struktur Proyek

```
├── backend/
│   ├── server.py           # Seluruh backend: routing, session, DB, serve static
│   ├── requirements.txt    # PyMySQL (driver DB, bukan framework)
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── app.js              # fetch() ke /?action=...
│   └── style.css
├── db/
│   └── init.sql            # Skema tabel users & puisi (dengan FK)
├── docker-compose.yml      # services: app + db
├── .env.example            # Template kredensial
└── docs/laporan.md         # Kerangka laporan
```

## Menjalankan Secara Lokal (Docker)

1. Salin `.env.example` menjadi `.env`, sesuaikan password bila perlu:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Build dan jalankan:
   ```powershell
   docker compose up --build -d
   ```
3. Buka aplikasi: **http://localhost:8000**
4. Menghentikan: `docker compose down` (data DB bertahan karena volume `db_data`; tambahkan `-v` untuk menghapus data).

## Aksi Endpoint (single path: `/?action=`)

| Aksi | Method | Autentikasi | Input (JSON) | Output |
|---|---|---|---|---|
| `register` | POST | - | username, nama, password | pesan sukses (201) |
| `login` | POST | - | username, password | Set-Cookie `SID`, data user |
| `logout` | POST | sesi | - | hapus sesi + cookie |
| `me` | GET | sesi | - | status sesi aktif |
| `submit_puisi` | POST | sesi | judul, isi, kategori, keyword | id puisi (201) |
| `daftar_puisi` | GET | sesi | - | daftar puisi milik user |

### Uji cepat dengan curl

```powershell
# Register
curl -X POST "http://localhost:8000/?action=register" -H "Content-Type: application/json" -d '{\"username\":\"budi\",\"nama\":\"Budi Santoso\",\"password\":\"rahasia123\"}'

# Login (cookie disimpan ke file cookies.txt)
curl -c cookies.txt -X POST "http://localhost:8000/?action=login" -H "Content-Type: application/json" -d '{\"username\":\"budi\",\"password\":\"rahasia123\"}'

# Submit puisi (terproteksi sesi)
curl -b cookies.txt -X POST "http://localhost:8000/?action=submit_puisi" -H "Content-Type: application/json" -d '{\"judul\":\"Senja\",\"kategori\":\"Alam\",\"keyword\":\"senja,langit\",\"isi\":\"Matahari turun perlahan...\"}'

# Daftar puisi (terproteksi sesi)
curl -b cookies.txt "http://localhost:8000/?action=daftar_puisi"
```

## Observasi State (Tujuan Pedagogis)

1. Buka DevTools (F12) → tab **Network** → login → perhatikan respons `login` memiliki header **`Set-Cookie: SID=...; HttpOnly; SameSite=Lax`**.
2. Buka tab **Application → Cookies** → cookie `SID` tersimpan.
3. Request `submit_puisi` / `daftar_puisi` berikutnya otomatis mengirim cookie `SID` (same-origin) → server menemukan file sesi di lokal → akses diberikan.
4. **Bukti stateful**: buat ulang container aplikasi (simulasi mesin baru):
   ```powershell
   docker compose up -d --force-recreate app
   ```
   → semua sesi hilang (file sesi ada di filesystem lokal container, *bukan* volume), user dipaksa login ulang. Inilah ketergantungan pada satu mesin yang dimaksud tugas; load balancing tanpa sticky session akan gagal.

## Deployment pada AWS EC2 (t2.micro)

Draft langkah (dilakukan setelah resource AWS tersedia):

1. Launch EC2 **t2.micro** (Ubuntu 24.04), Security Group: port **22** (SSH) dan **80** (HTTP) terbuka.
2. Tambah swap 1-2 GB (RAM t2.micro hanya 1 GB, MySQL butuh ruang):
   ```bash
   sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
   sudo mkswap /swapfile && sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```
3. Instal Docker & Compose plugin:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
   sudo usermod -aG docker ubuntu
   ```
4. Clone repo, buat `.env`, ubah mapping port di `docker-compose.yml` menjadi `80:8000`, lalu:
   ```bash
   docker compose up --build -d
   ```
5. Akses aplikasi via **http://<IP_PUBLIK_EC2>** dan uji seluruh fitur.

## Deliverables

- Laporan PDF (`docs/laporan.md` → PDF)
- Tautan repositori GitHub
- Alamat IP Publik EC2 (demo saat kelas)
