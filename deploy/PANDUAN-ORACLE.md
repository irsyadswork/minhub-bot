# Panduan Oracle Cloud (gratis) untuk Minhub

## Bagian A — Daftar akun (±15 menit, aktivasi bisa sampai beberapa jam)
1. Buka https://signup.cloud.oracle.com/
2. Isi **Country/Territory: Indonesia**, nama, dan email → klik **Verify my email** → buka email dari Oracle dan klik link-nya.
3. Buat **password**, isi **Cloud Account Name** (bebas, huruf kecil, misal `clipperhub`).
4. **Home Region** → pilih **Indonesia North (Batam)** atau **Singapore**.
   ⚠️ Tidak bisa diganti nanti. Server gratis cuma bisa dibuat di home region.
5. Isi alamat dan **nomor HP** (verifikasi SMS).
6. **Payment verification** → masukkan kartu Visa/Mastercard (kredit atau debit).
   Oracle cuma menahan ±US$1 sementara untuk verifikasi, lalu dikembalikan. Akun tetap **Free Tier**, tidak ditagih.
7. Centang persetujuan → **Start my free trial**.
8. Tunggu email **"Your Oracle Cloud account is fully provisioned"** (biasanya beberapa menit, kadang beberapa jam).

## Bagian B — Bikin server (VM) (±10 menit)
1. Login di https://cloud.oracle.com/ (isi Cloud Account Name → email & password).
2. Di halaman utama klik **Create a VM instance** (atau menu ☰ → **Compute** → **Instances** → **Create instance**).
3. **Name:** `minhub`
4. **Image and shape** → klik **Edit**:
   - **Image** → **Change image** → pilih **Ubuntu** → versi **Canonical Ubuntu 24.04** (atau 22.04) → **Select image**.
   - **Shape** → **Change shape** → pilih salah satu yang ada label **Always Free-eligible**:
     - **Ampere → VM.Standard.A1.Flex** (atur 1 OCPU, 6 GB memory) — lebih kencang, atau
     - **Specialty and previous generation → VM.Standard.E2.1.Micro** — kalau A1 "out of capacity".
5. **Networking:** biarkan default (Create new virtual cloud network) dan pastikan **Assign a public IPv4 address** = **Yes**.
6. **Add SSH keys** → pilih **Generate a key pair for me** → klik **Download private key**.
   Simpan file `.key` itu di tempat aman (misal folder Documents). **Ini kunci masuk server — jangan dikirim ke siapa pun.**
7. Klik **Create**. Tunggu status berubah jadi **RUNNING** (hijau).
8. Di halaman instance, salin **Public IP address** (contoh: `140.238.xx.xx`).

## Bagian C — Kirim ke Claude
- **Public IP address** server
- **Lokasi file `.key`** di PC kamu (contoh: `C:\Users\muham\Documents\ssh-key-2026-10-21.key`) — cukup lokasinya, bukan isinya.

Sisanya (install, upload bot, auto-restart 24 jam) dikerjakan Claude.

## Tips
- Kalau muncul **"Out of capacity for shape VM.Standard.A1.Flex"**: pakai **VM.Standard.E2.1.Micro**, atau coba lagi beberapa jam kemudian.
- Oracle bisa **mengambil kembali server gratis yang "nganggur"** (pemakaian CPU sangat rendah selama 7 hari). Bot ini memang ringan, jadi supaya aman:
  di menu ☰ → **Billing & Cost Management** → **Upgrade and Manage Payment** → **Upgrade to Pay As You Go**.
  Selama tetap memakai resource berlabel *Always Free*, **tetap Rp0**, dan server tidak akan diambil kembali.
