# Laporan: Pembangunan Aplikasi Monolitik Stateful dan Deployment pada AWS EC2

**Mata Kuliah:** PACS262521 - Pengembangan Perangkat Lunak Scalable
**Nama:** [ISI NAMA]
**NIM:** [ISI NIM]
**Tanggal:** [ISI TANGGAL]

> **Catatan pengisian:** Semua teks dengan format `[ISI ...]` harus diganti sebelum laporan dikumpulkan. Placeholder gambar menggunakan folder `docs/screenshots/`.

## Abstrak

Proyek ini membangun aplikasi puisi dengan arsitektur monolitik stateful sebagai baseline atau ground truth sebelum mempelajari arsitektur stateless dan horizontal scaling. Seluruh backend berada dalam satu file Python dan menggunakan routing single-path berbasis query string. Data aplikasi disimpan pada MySQL 8, sedangkan session login disimpan sebagai file JSON lokal pada container aplikasi. Frontend dibuat menggunakan HTML, CSS, dan JavaScript tanpa framework.

Aplikasi dijalankan menggunakan Docker Compose dan kemudian dideploy ke AWS EC2 pada region Asia Pacific (Singapore) dengan tipe instance `t3.micro`. Pengujian membuktikan bahwa register, login, submit puisi, dan daftar puisi berjalan baik. Eksperimen `--force-recreate` pada container aplikasi juga membuktikan sifat stateful karena session hilang ketika container yang menyimpan file session dibuat ulang.

## 1. Pendahuluan

### 1.1 Latar Belakang

Arsitektur monolitik stateful menyimpan proses aplikasi dan state pengguna pada satu instance atau satu mesin. Arsitektur seperti ini mudah dipahami dan sesuai digunakan sebagai baseline pembelajaran, tetapi memiliki ketergantungan kuat terhadap filesystem dan instance tempat aplikasi berjalan.

Proyek ini dibuat untuk menunjukkan cara kerja aplikasi monolitik stateful secara nyata. Aplikasi memiliki proses backend, database, dan frontend yang dikemas dalam lingkungan Docker. Session tidak menggunakan JWT, melainkan disimpan pada filesystem lokal container backend.

### 1.2 Tujuan

Tujuan proyek ini adalah:

1. Membangun aplikasi monolitik dengan backend dan frontend yang sederhana.
2. Menggunakan MySQL sebagai database relasional.
3. Menerapkan autentikasi dengan password hashing.
4. Menerapkan server-side session berbasis file JSON.
5. Menjalankan aplikasi secara lokal menggunakan Docker Compose.
6. Men-deploy aplikasi ke AWS EC2.
7. Membuktikan dampak ketergantungan session lokal terhadap skalabilitas.

### 1.3 Repository

Repository proyek:

`https://github.com/satyawirapramudita/Monolithic-Stateful-AWS-Deployment`

Commit deployment yang digunakan:

```text
f6857dd feat: add production compose port override
```

## 2. Arsitektur Sistem

### 2.1 Diagram Arsitektur

```text
+------------------+
| Browser pengguna  |
| HTML/CSS/JS       |
+--------+---------+
         | HTTP + Cookie SID
         v
+--------------------------------+
| puisi-app                       |
| Python http.server              |
| Routing /?action=<aksi>         |
| File session lokal: sessions/   |
+---------------+----------------+
                | PyMySQL
                v
+--------------------------------+
| puisi-db                        |
| MySQL 8                         |
| Volume Docker: db_data          |
+--------------------------------+
```

Browser mengakses backend melalui HTTP. Backend menyajikan file frontend dan menangani endpoint yang dibedakan menggunakan parameter `action`. Backend kemudian berkomunikasi dengan MySQL melalui jaringan internal Docker Compose.

### 2.2 Komponen Sistem

| Komponen | Teknologi | Peran |
|---|---|---|
| Frontend | HTML, CSS, JavaScript | Form login, register, submit puisi, dan daftar puisi |
| Backend | Python 3.12 `http.server` | Routing, autentikasi, session, static file server, dan akses DB |
| Driver DB | PyMySQL 1.1.1 | Koneksi backend ke MySQL |
| Password security | PBKDF2-HMAC-SHA256 | Hash password dengan salt acak |
| Database | MySQL 8 | Penyimpanan users dan puisi |
| Container runtime | Docker Compose | Menjalankan service app dan db |
| Deployment | AWS EC2 | Menyediakan instance untuk aplikasi production |

### 2.3 Struktur Repository

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
├── docker-compose.prod.yml
├── docker-compose.yml
├── .env.example
└── README.md
```

![Struktur repository](screenshots/01-repository.png)

*Gambar 1. Placeholder screenshot struktur repository.*

### 2.4 Endpoint Aplikasi

Semua request API menggunakan single path `/?action=<aksi>`.

| Aksi | Method | Autentikasi | Fungsi |
|---|---|---|---|
| `register` | POST | Tidak | Membuat akun baru |
| `login` | POST | Tidak | Memvalidasi akun dan membuat session |
| `logout` | POST | Session | Menghapus session aktif |
| `me` | GET | Session opsional | Memeriksa status session |
| `submit_puisi` | POST | Wajib | Menyimpan puisi milik user aktif |
| `daftar_puisi` | GET | Wajib | Mengambil puisi milik user aktif |

## 3. Basis Data

### 3.1 Skema Database

Database menggunakan dua tabel utama, yaitu `users` dan `puisi`.

#### Tabel `users`

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INT AUTO_INCREMENT | Primary key |
| `username` | VARCHAR(50) | Username unik |
| `password` | VARCHAR(255) | Password hash PBKDF2 |
| `nama` | VARCHAR(100) | Nama lengkap pengguna |
| `no_id` | VARCHAR(30), nullable | Kolom identitas opsional |

#### Tabel `puisi`

| Kolom | Tipe | Keterangan |
|---|---|---|
| `id` | INT AUTO_INCREMENT | Primary key |
| `user_id` | INT | Foreign key ke `users.id` |
| `judul` | VARCHAR(150) | Judul puisi |
| `tgl_submit` | DATETIME | Waktu submit |
| `isi` | TEXT | Isi puisi |
| `kategori` | VARCHAR(50) | Kategori puisi |
| `keyword` | VARCHAR(255), nullable | Keyword puisi |

Relasi database adalah one-to-many. Satu user dapat memiliki banyak puisi, sedangkan setiap puisi hanya dimiliki oleh satu user. Foreign key `puisi.user_id` mengarah ke `users.id` untuk menjaga integritas referensial.

```text
users (1) ---------------- (N) puisi
  id  <--------------------  user_id
```

![Skema database](screenshots/03-skema-database.png)

*Gambar 2. Placeholder screenshot tabel atau skema database.*

### 3.2 Inisialisasi Database

Skema dibuat oleh file `db/init.sql` yang di-mount ke direktori initialization MySQL:

```yaml
- ./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
```

Data MySQL disimpan pada volume Docker `db_data`, sehingga data database tetap ada ketika container dihentikan atau dibuat ulang. Script initialization hanya dijalankan saat volume database masih kosong.

## 4. Manajemen Session Stateful

### 4.1 Mekanisme Session

Saat login berhasil, backend membuat session ID acak sepanjang 64 karakter hexadecimal. Data session disimpan sebagai file JSON pada:

```text
sessions/<SID>.json
```

Isi session mencakup `user_id`, `username`, `nama`, waktu pembuatan, dan waktu kedaluwarsa. Session memiliki TTL 3600 detik atau satu jam.

Cookie yang dikirim ke browser memiliki atribut:

```text
SID=<nilai-session>; HttpOnly; Path=/; SameSite=Lax; Max-Age=3600
```

Password tidak disimpan dalam bentuk plaintext. Backend menggunakan PBKDF2-HMAC-SHA256 dengan salt acak untuk menyimpan hash password.

### 4.2 Alur Login

1. Browser mengirim username dan password ke `/?action=login`.
2. Backend mengambil data user dari MySQL.
3. Backend memverifikasi password terhadap hash yang tersimpan.
4. Backend membuat file session JSON pada filesystem lokal container app.
5. Backend mengirim `Set-Cookie: SID=...`.
6. Browser menyimpan cookie tersebut.
7. Request berikutnya mengirim cookie SID secara otomatis.
8. Backend membaca file session berdasarkan SID.
9. Akses ke endpoint protected diberikan jika file session valid.

![Set-Cookie login](screenshots/09-set-cookie.png)

*Gambar 3. Placeholder screenshot header Set-Cookie pada tab Network.*

### 4.3 Alasan Aplikasi Disebut Stateful

Session tidak disimpan pada database, Redis, atau token yang dapat diverifikasi secara mandiri. Session berada di filesystem lokal container app. Jika container tersebut dibuat ulang, file session hilang dan cookie lama tidak lagi dapat digunakan.

Konsekuensinya, load balancing tanpa sticky session dapat mengarahkan request ke instance yang tidak memiliki file session. Hal ini menjadi motivasi untuk mempelajari arsitektur stateless pada tahap berikutnya.

## 5. Frontend Minimalis

Frontend dibuat tanpa framework dan tanpa bundler. File yang digunakan adalah:

- `index.html` untuk struktur halaman.
- `app.js` untuk request API menggunakan `fetch()`.
- `style.css` untuk tampilan sederhana bergaya web tahun 1990-an.

Frontend memiliki fitur:

1. Tab Login dan Register.
2. Form pendaftaran akun.
3. Form login.
4. Form submit puisi.
5. Tabel daftar puisi user aktif.
6. Tombol logout.
7. Tombol `Muat Ulang` untuk mengambil daftar puisi terbaru.
8. Text flash `Daftar puisi diperbarui.` setelah reload berhasil.

Request dilakukan secara same-origin sehingga browser mengirim cookie SID secara otomatis.

![Halaman frontend](screenshots/07-browser-public-ip.png)

*Gambar 4. Placeholder screenshot halaman frontend melalui Public IP EC2.*

![Text flash refresh](screenshots/11-refresh-text-flash.png)

*Gambar 5. Placeholder screenshot text flash setelah tombol Muat Ulang ditekan.*

## 6. Deployment pada AWS EC2

### 6.1 Konfigurasi AWS

Region Jakarta tidak tersedia untuk akun AWS yang digunakan. Deployment dilakukan pada region Singapore.

| Konfigurasi | Nilai |
|---|---|
| Region | Asia Pacific (Singapore) |
| Region code | `ap-southeast-1` |
| Instance type | `t3.micro` |
| AMI | Ubuntu Server 24.04 LTS |
| Public IP / Elastic IP | `52.74.6.106` |
| URL aplikasi | `http://52.74.6.106` |
| Docker | 29.1.3 |
| Docker Compose | 2.40.3 |
| Swap | 2 GB |

Tipe `t2.micro` tidak tersedia untuk akun tersebut sehingga digunakan `t3.micro`. Swap 2 GB ditambahkan karena instance memiliki RAM terbatas dan aplikasi menjalankan MySQL 8.

![EC2 instance](screenshots/02-ec2-running.png)

*Gambar 6. Placeholder screenshot instance EC2 berstatus Running dan status checks 2/2.*

### 6.2 Security Group

Security Group menyediakan akses SSH dan HTTP:

| Rule | Port | Source | Tujuan |
|---|---:|---|---|
| SSH | 22 | My IP | Administrasi server |
| HTTP | 80 | `0.0.0.0/0` | Akses aplikasi publik |

Port `3306` tidak dibuka karena MySQL hanya digunakan oleh container backend melalui jaringan internal Docker.

![Security Group](screenshots/03-security-group.png)

*Gambar 7. Placeholder screenshot Security Group.*

### 6.3 User Data

User Data digunakan untuk memasang Docker, Docker Compose, dan swap secara otomatis saat instance pertama kali dibuat.

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

![User Data](screenshots/04-user-data.png)

*Gambar 8. Placeholder screenshot User Data atau hasil cloud-init.*

### 6.4 Proses Deployment

Repository di-clone ke EC2 menggunakan HTTPS karena repository bersifat public. File `.env` dibuat langsung pada server dan tidak dimasukkan ke Git.

Perintah deployment:

```bash
git clone https://github.com/satyawirapramudita/Monolithic-Stateful-AWS-Deployment.git
cd Monolithic-Stateful-AWS-Deployment
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

File `docker-compose.prod.yml` mengarahkan port host 80 ke port aplikasi 8000:

```yaml
services:
  app:
    ports:
      - "80:8000"
```

![Compose healthy](screenshots/06-compose-healthy.png)

*Gambar 9. Placeholder screenshot output `docker compose ps` dengan database healthy.*

## 7. Hasil Pengujian

### 7.1 Pengujian Infrastruktur

| Pengujian | Hasil |
|---|---|
| SSH ke EC2 | Berhasil |
| User Data selesai | Berhasil |
| Docker terpasang | Berhasil |
| Docker Compose terpasang | Berhasil |
| Swap 2 GB aktif | Berhasil |
| MySQL container | `Up (healthy)` |
| App container | `Up` |
| Akses Public IP | HTTP 200 |

### 7.2 Pengujian Endpoint

Hasil pengujian end-to-end melalui Public IP:

| Aksi | Status HTTP | Hasil |
|---|---:|---|
| `GET /` | 200 | Frontend tampil |
| `GET /?action=me` sebelum login | 200 | `ok: false` |
| `POST /?action=register` | 201 | Akun berhasil dibuat |
| `POST /?action=login` | 200 | Session berhasil dibuat |
| `POST /?action=submit_puisi` | 201 | Puisi berhasil disimpan |
| `GET /?action=daftar_puisi` | 200 | Puisi berhasil diambil |
| `GET /?action=me` setelah login | 200 | `ok: true` |

![API testing](screenshots/12-api-testing.png)

*Gambar 10. Placeholder screenshot hasil pengujian endpoint.*

### 7.3 Data Uji

Akun demo yang digunakan untuk pengujian:

```text
Username: ec2demo0901024353
Nama: Demo EC2 Singapore
Password: DemoPassword123!
```

Data puisi yang berhasil disimpan:

```text
Judul: Puisi dari EC2
Kategori: Deployment
Keyword: aws,ec2,docker
Isi: Aplikasi puisi berhasil berjalan di EC2 Singapore.
```

Kredensial tersebut hanya digunakan sebagai akun demonstrasi. Password harus diganti atau akun dihapus setelah kegiatan demo selesai.

![Submit puisi](screenshots/10-submit-puisi.png)

*Gambar 11. Placeholder screenshot submit puisi dan daftar puisi.*

## 8. Bukti Stateful

### 8.1 Prosedur Eksperimen

Eksperimen dilakukan dengan urutan berikut:

1. Login menggunakan akun demo.
2. Panggil endpoint `me` dengan cookie session.
3. Hasil sebelum container dibuat ulang menunjukkan session aktif.
4. Jalankan:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate app
```

5. Panggil endpoint `me` kembali menggunakan cookie yang sama.
6. Hasil setelah container dibuat ulang menunjukkan session tidak valid.

### 8.2 Hasil Eksperimen

Sebelum container app dibuat ulang:

```json
{"ok": true, "username": "ec2demo0901024353", "nama": "Demo EC2 Singapore"}
```

Setelah container app dibuat ulang:

```json
{"ok": false, "message": "Belum login"}
```

Hasil ini membuktikan bahwa session disimpan pada filesystem container app. Container baru tidak memiliki file session dari container lama.

> **Catatan:** `docker compose restart app` tidak digunakan sebagai bukti utama karena restart dapat mempertahankan filesystem container. Perintah `--force-recreate` digunakan agar container benar-benar dibuat ulang.

![Stateful before and after](screenshots/13-stateful-before-after.png)

*Gambar 12. Placeholder screenshot session sebelum dan sesudah force recreate.*

### 8.3 Implikasi terhadap Scalability

Jika aplikasi dijalankan pada beberapa instance tanpa mekanisme tambahan, request pengguna dapat masuk ke instance yang tidak memiliki session file. Akibatnya user dianggap belum login walaupun cookie SID masih berada di browser.

Untuk mengembangkan aplikasi menjadi stateless, session dapat dipindahkan ke penyimpanan bersama seperti Redis atau database, atau diganti dengan mekanisme token yang sesuai. Perubahan tersebut berada di luar scope proyek baseline ini.

## 9. Kesimpulan

Proyek berhasil membangun dan men-deploy aplikasi puisi monolitik stateful ke AWS EC2. Backend menggunakan satu file Python tanpa framework, frontend menggunakan HTML/CSS/JavaScript sederhana, dan database menggunakan MySQL 8 dalam container Docker.

Deployment pada EC2 `t3.micro` di region Singapore berjalan dengan baik. Docker Compose berhasil menjalankan service app dan database, dan aplikasi dapat diakses melalui Elastic IP `http://52.74.6.106`.

Pengujian endpoint membuktikan fitur register, login, submit puisi, dan daftar puisi berjalan sesuai rancangan. Eksperimen force recreate membuktikan bahwa session tersimpan pada filesystem lokal container aplikasi. Ketergantungan tersebut menjelaskan mengapa aplikasi stateful membutuhkan sticky session atau migrasi state bersama ketika akan menggunakan horizontal scaling.

## 10. Daftar Bukti Screenshot

Screenshot yang perlu diganti atau dilengkapi sebelum laporan dikumpulkan:

1. `screenshots/01-repository.png` - struktur repository.
2. `screenshots/02-ec2-running.png` - EC2 running dan status checks.
3. `screenshots/03-security-group.png` - Security Group port 22 dan 80.
4. `screenshots/03-skema-database.png` - skema tabel database.
5. `screenshots/04-user-data.png` - User Data atau cloud-init.
6. `screenshots/06-compose-healthy.png` - container healthy.
7. `screenshots/07-browser-public-ip.png` - aplikasi melalui Public IP.
8. `screenshots/09-set-cookie.png` - Set-Cookie SID.
9. `screenshots/10-submit-puisi.png` - data puisi.
10. `screenshots/11-refresh-text-flash.png` - text flash refresh.
11. `screenshots/12-api-testing.png` - hasil pengujian API.
12. `screenshots/13-stateful-before-after.png` - bukti session hilang.

## 11. Referensi dan Informasi Deployment

- Repository: `https://github.com/satyawirapramudita/Monolithic-Stateful-AWS-Deployment`
- Region: `ap-southeast-1` (Asia Pacific, Singapore)
- Instance: `t3.micro`
- Elastic IP saat dokumentasi: `52.74.6.106`
- URL aplikasi: `http://52.74.6.106`
- Docker: `29.1.3`
- Docker Compose: `2.40.3`
- Swap: `2 GB`
