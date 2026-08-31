# Laporan: Pembangunan Aplikasi Monolitik Stateful dan Deployment pada AWS EC2

Mata Kuliah: PACS262521 - Pengembangan Perangkat Lunak Scalable
Nama: [NAMA]
NIM: [NIM]

## 1. Pendahuluan
Penjelasan tujuan: membangun baseline arsitektur monolithic-stateful sebagai ground truth sebelum memahami arsitektur stateless dan horizontal scaling.

## 2. Arsitektur Sistem
- Diagram arsitektur: Browser (FE HTML/JS) → HTTP → server.py (single path `/?action=`) → MySQL
- Satu file backend, tanpa framework, routing single-path
- [Screenshot struktur repo]

## 3. Basis Data
- Skema `users` dan `puisi` + Foreign Key
- Penjelasan relasi 1:N dan integritas referensial
- [Screenshot/tabel skema]

## 4. Manajemen Session (Stateful)
- Mekanisme: file JSON lokal di container (`sessions/<SID>.json`), cookie SID HttpOnly
- Alur login → Set-Cookie → request berikutnya membawa cookie → validasi file sesi
- Dilarang JWT: session benar-benar tersimpan di server, menciptakan ketergantungan satu mesin
- [Screenshot Set-Cookie di tab Network]

## 5. Frontend Minimalis
- Fetch API, tanpa framework, cookie jar browser mengelola SID otomatis
- [Screenshot halaman]

## 6. Bukti Stateful (Eksperimen)
- Restart container `app` (`docker compose restart app`) → file sesi lokal hilang → user dipaksa login ulang
- Implikasi: load balancing tanpa sticky session akan memutus sesi → motivasi arsitektur stateless di masa depan
- [Screenshot sebelum/sesudah restart]

## 7. Deployment pada AWS EC2
- Tipe instance t2.micro, region [REGION]
- Security Group: port 80 terbuka
- Docker & docker compose di EC2, mapping port 80:8000
- [Screenshot EC2 console + hasil akses via IP publik]
- Alamat IP Publik: [IP]

## 8. Kesimpulan
Pelajaran yang diperoleh mengenai state management, ketergantungan mesin, dan arah evolusi ke arsitektur stateless.
