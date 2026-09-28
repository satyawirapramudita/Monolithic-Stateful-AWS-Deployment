-- migrate_001_gambar.sql
-- Tambah kolom bait dan gambar_file ke tabel puisi
-- Jalankan sekali saja di database yang sudah berjalan (BUKAN bagian dari init.sql)

SET NAMES utf8mb4;

ALTER TABLE puisi
    ADD COLUMN bait TEXT NULL COMMENT 'Kutipan pendek yang ditampilkan di gambar puisi' AFTER isi,
    ADD COLUMN gambar_file VARCHAR(255) NULL COMMENT 'Path file gambar di S3, contoh: hasil-puisi/puisi-1234-abcd.jpg' AFTER bait;
