# Langkah-Langkah Dokumentasi

## Pembangunan dan Deployment Aplikasi Monolitik Stateful

Dokumen ini berisi urutan pekerjaan, perintah, hasil yang diharapkan, dan daftar bukti screenshot untuk mendokumentasikan aplikasi puisi sampai berjalan di AWS EC2.

## 1. Informasi Proyek

- Mata kuliah: PACS262521 - Pengembangan Perangkat Lunak Scalable
- Repository: `https://github.com/satyawirapramudita/Monolithic-Stateful-AWS-Deployment`
- Arsitektur: aplikasi monolitik stateful
- Backend: Python standard library `http.server`
- Database: MySQL 8
- Frontend: HTML, CSS, dan JavaScript tanpa framework
- Deployment: AWS EC2 Ubuntu 24.04
- Region: Asia Pacific (Singapore), `ap-southeast-1`
- Tipe instance: `t3.micro`
- Public IP yang digunakan saat dokumentasi: `52.74.6.106`

> **Catatan Public IP:** Public IPv4 biasa dapat berubah setiap kali instance EC2 dihentikan lalu dijalankan kembali. Elastic IP `52.74.6.106` telah di-associate ke instance agar alamat aplikasi tetap stabil. Jika instance belum menggunakan Elastic IP, periksa kembali alamat pada AWS Console sebelum menjalankan pengujian atau memperbarui dokumentasi.

## 2. Struktur Proyek

Struktur utama repository adalah sebagai berikut:

```text
Monolithic-Stateful-AWS-Deployment/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── server.py
├── db/
│   └── init.sql
├── frontend/
│   ├── app.js
│   ├── index.html
│   └── style.css
├── docs/
│   ├── langkah-langkah.md
│   ├── laporan.md
│   └── screenshots/
├── .dockerignore
├── .env.example
├── .gitignore
├── docker-compose.prod.yml
├── docker-compose.yml
└── README.md
```

## 3. Menjalankan Aplikasi Secara Lokal

### 3.1 Prasyarat

Pastikan Docker Desktop dan Git sudah terpasang pada komputer lokal.

Periksa instalasi:

```powershell
docker --version
docker compose version
git --version
```

### 3.2 Menyiapkan Environment

Salin template environment:

```powershell
Copy-Item .env.example .env
```

Isi nilai password pada `.env`. File `.env` tidak boleh di-commit karena berisi kredensial database.

### 3.3 Build dan Menjalankan Container

```powershell
docker compose up --build -d
```

Periksa status:

```powershell
docker compose ps
```

Container `puisi-db` harus berstatus `healthy` dan container `puisi-app` harus berstatus `Up`.

Buka aplikasi lokal:

```text
http://localhost:8000
```

### 3.4 Pengujian Lokal

Uji halaman frontend:

```powershell
curl.exe -i http://localhost:8000/
```

Uji status session sebelum login:

```powershell
curl.exe "http://localhost:8000/?action=me"
```

Hasil yang diharapkan:

```json
{"ok": false, "message": "Belum login"}
```

Lakukan pengujian melalui browser:

1. Buka tab `Register`.
2. Buat akun baru.
3. Login menggunakan akun tersebut.
4. Masukkan judul, kategori, keyword, dan isi puisi.
5. Klik `Kirim Puisi`.
6. Klik `Muat Ulang` dan amati text flash `Daftar puisi diperbarui.`.
7. Buka DevTools dengan `F12` dan periksa request pada tab `Network`.

## 4. Commit dan Push ke GitHub

Periksa perubahan lokal:

```powershell
git status
git diff
```

Tambahkan dan commit file proyek:

```powershell
git add .
git commit -m "feat: add monolithic stateful app with AWS EC2 deployment setup"
git push origin main
```

Pastikan commit terbaru sudah berada di branch `main` pada GitHub.

## 5. Membuat Instance EC2

### 5.1 Region

Region Jakarta tidak tersedia untuk akun yang digunakan. Oleh karena itu, deployment dilakukan pada:

```text
Asia Pacific (Singapore)
Region code: ap-southeast-1
```

Semua resource EC2 seperti key pair dan security group harus dibuat pada region yang sama.

### 5.2 Konfigurasi Instance

Pada AWS Console, buka `EC2 -> Instances -> Launch instances` dan gunakan konfigurasi berikut:

- Name: `puisi-app`
- AMI: Ubuntu Server 24.04 LTS
- Instance type: `t3.micro`
- Key pair: `puisi-singapore`
- Storage: 20 GiB gp3 atau sesuai quota akun
- Auto-assign public IP: Enable

Jika `t2.micro` tidak tersedia, `t3.micro` digunakan sebagai pengganti.

### 5.3 Security Group

Buat inbound rules berikut:

| Type | Protocol | Port | Source |
|---|---|---:|---|
| SSH | TCP | 22 | My IP |
| HTTP | TCP | 80 | `0.0.0.0/0` |

Jangan membuka port MySQL `3306` ke internet.

## 6. User Data EC2

Pada `Advanced details -> User data`, masukkan script berikut:

```bash
#!/bin/bash
set -euxo pipefail

apt-get update
apt-get install -y docker.io docker-compose-v2

systemctl enable --now docker
usermod -aG docker ubuntu

fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Script tersebut melakukan hal berikut:

- Menginstal Docker Engine.
- Menginstal Docker Compose plugin.
- Mengaktifkan service Docker.
- Menambahkan user `ubuntu` ke group `docker`.
- Membuat dan mengaktifkan swap 2 GB.

Tunggu instance berstatus `Running` dan status checks `2/2 checks passed`.

## 7. Login ke EC2 melalui SSH

Dari Windows PowerShell:

```powershell
ssh -i "C:\Users\Satya\Downloads\puisi-singapore.pem" ubuntu@52.74.6.106
```

Setelah masuk, periksa User Data:

```bash
cloud-init status --wait
```

Contoh hasil yang telah didapatkan:

```text
Docker version 29.1.3
Docker Compose version 2.40.3
/swapfile file 2G
```

Keluar dan login kembali agar group `docker` diterapkan:

```bash
exit
```

## 8. Clone Repository di EC2

```bash
cd ~
git clone https://github.com/satyawirapramudita/Monolithic-Stateful-AWS-Deployment.git
cd Monolithic-Stateful-AWS-Deployment
```

Periksa commit yang digunakan:

```bash
git rev-parse --short HEAD
```

Commit deployment yang digunakan adalah:

```text
f6857dd
```

## 9. Menyiapkan `.env` di EC2

Buat file environment lokal pada EC2:

```bash
cp .env.example .env
```

Untuk membuat password acak:

```bash
ROOT_PASSWORD=$(openssl rand -hex 24)
DB_PASSWORD=$(openssl rand -hex 24)
cat > .env <<EOF
MYSQL_ROOT_PASSWORD=$ROOT_PASSWORD
DB_NAME=puisi_db
DB_USER=puisi_user
DB_PASSWORD=$DB_PASSWORD
EOF
chmod 600 .env
```

Jangan menampilkan atau meng-commit isi `.env`.

## 10. Deployment Production

Jalankan Compose dengan dua file agar port host `80` diarahkan ke port aplikasi `8000`:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Periksa status service:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

Hasil yang diharapkan:

```text
puisi-app   Up
puisi-db    Up (healthy)
```

Periksa log backend:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs app --tail 30
```

Log penting:

```text
Database terhubung.
Server monolitik stateful berjalan di 0.0.0.0:8000
```


### 11.1 Pengujian Halaman

Dari komputer lokal:

```powershell
curl.exe -i http://52.74.6.106/
```

Hasil yang diharapkan:

```text
HTTP/1.1 200 OK
```

Buka browser:

```text
http://52.74.6.106
```

### 11.2 Pengujian API

Status session sebelum login:

```powershell
curl.exe "http://52.74.6.106/?action=me"
```

Hasil:

```json
{"ok": false, "message": "Belum login"}
```

Untuk pengujian JSON dari PowerShell, `Invoke-WebRequest` dapat digunakan agar body JSON dan cookie dikirim dengan benar:

```powershell
$base = "http://52.74.6.106"
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

$registerBody = @{
    username = "demoaws"
    nama = "Demo AWS"
    password = "DemoPassword123!"
} | ConvertTo-Json -Compress

$loginBody = @{
    username = "demoaws"
    password = "DemoPassword123!"
} | ConvertTo-Json -Compress

$submitBody = @{
    judul = "Puisi dari EC2"
    kategori = "Deployment"
    keyword = "aws,ec2,docker"
    isi = "Aplikasi puisi berhasil berjalan di EC2 Singapore."
} | ConvertTo-Json -Compress

Invoke-WebRequest "$base/?action=register" -Method Post `
    -Body $registerBody -ContentType "application/json"

Invoke-WebRequest "$base/?action=login" -Method Post `
    -Body $loginBody -ContentType "application/json" -WebSession $session

Invoke-WebRequest "$base/?action=submit_puisi" -Method Post `
    -Body $submitBody -ContentType "application/json" -WebSession $session

Invoke-WebRequest "$base/?action=daftar_puisi" `
    -WebSession $session
```

Status yang diharapkan:

| Aksi | Status |
|---|---:|
| Halaman frontend | 200 |
| `me` sebelum login | 200 dengan `ok: false` |
| `register` | 201 |
| `login` | 200 |
| `submit_puisi` | 201 |
| `daftar_puisi` | 200 |
| `me` setelah login | 200 dengan `ok: true` |

### 11.3 Pengujian melalui Browser

1. Buka `http://52.74.6.106`.
2. Buka tab `Register`.
3. Buat akun baru atau gunakan akun demo.
4. Login.
5. Submit puisi.
6. Pastikan puisi muncul pada tabel.
7. Klik `Muat Ulang`.
8. Pastikan teks `Daftar puisi diperbarui.` muncul dan berkedip.
9. Buka DevTools -> Network.
10. Periksa response login dan header `Set-Cookie`.

## 12. Eksperimen Stateful

Eksperimen ini membuktikan bahwa session tersimpan pada filesystem lokal container app.

1. Login melalui browser atau API.
2. Panggil endpoint `me` dan pastikan hasilnya `ok: true`.
3. Di EC2, buat ulang container app:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate app
```

4. Refresh browser atau panggil endpoint `me` menggunakan cookie lama.
5. Hasil yang diharapkan:

```json
{"ok": false, "message": "Belum login"}
```

Gunakan `--force-recreate`, bukan hanya `docker compose restart app`. Perintah `restart` dapat mempertahankan filesystem container, sedangkan `--force-recreate` membuat container baru dan menghapus session lokal pada container lama.

Database tidak hilang karena data berada pada volume Docker `db_data`.

## 13. Daftar Screenshot

Simpan screenshot pada folder `docs/screenshots/` dengan nama yang konsisten:

| No. | Nama file | Bukti yang diambil |
|---:|---|---|
| 1 | `01-repository.png` | Struktur repository GitHub atau lokal |
| 2 | `02-ec2-running.png` | Instance EC2 status Running dan checks 2/2 |
| 3 | `03-security-group.png` | Inbound rules port 22 dan 80 |
| 4 | `04-user-data.png` | User Data atau hasil cloud-init |
| 5 | `05-ssh-docker-swap.png` | Versi Docker, Compose, dan swap |
| 6 | `06-compose-healthy.png` | Output `docker compose ps` |
| 7 | `07-browser-public-ip.png` | Aplikasi dibuka melalui Public IP |
| 8 | `08-register-login.png` | Register dan login berhasil |
| 9 | `09-set-cookie.png` | Header `Set-Cookie: SID` pada Network |
| 10 | `10-submit-puisi.png` | Puisi berhasil dikirim dan tampil di tabel |
| 11 | `11-refresh-text-flash.png` | Text flash setelah klik `Muat Ulang` |
| 12 | `12-api-testing.png` | Hasil pengujian endpoint |
| 13 | `13-stateful-before-after.png` | Session valid sebelum dan invalid setelah recreate |

## 14. Penyusunan Laporan PDF

1. Isi `[NAMA]`, `[NIM]`, dan identitas lain pada `docs/laporan.md`.
2. Ambil semua screenshot pada daftar di atas.
3. Simpan screenshot pada `docs/screenshots/`.
4. Pastikan link gambar pada laporan sesuai nama file.
5. Periksa kembali Public IP dan region.
6. Export `docs/laporan.md` ke PDF menggunakan editor Markdown atau converter Markdown ke PDF.
7. Jangan masukkan password database ke laporan.
8. Kredensial akun demo sebaiknya dihapus atau diganti setelah demo selesai.

## 15. Informasi Deployment yang Tercatat

```text
Region: Asia Pacific (Singapore)
Region code: ap-southeast-1
Instance type: t3.micro
Operating system: Ubuntu Server 24.04 LTS
Public IP: 52.74.6.106
Docker: 29.1.3
Docker Compose: 2.40.3
Swap: 2 GB
Repository commit: f6857dd
Application URL: http://52.74.6.106
```
