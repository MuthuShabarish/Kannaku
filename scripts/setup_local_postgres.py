import os
import sys
import urllib.request
import zipfile
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = BASE_DIR / ".tools"
PG_DIR = TOOLS_DIR / "pgsql"
DATA_DIR = PG_DIR / "data"
ZIP_PATH = TOOLS_DIR / "postgresql-16.15-5-windows-x64-binaries.zip"
DOWNLOAD_URL = "https://get.enterprisedb.com/postgresql/postgresql-16.15-5-windows-x64-binaries.zip"

def download_file(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 300_000_000:
        print(f"Zip already downloaded ({dest.stat().st_size} bytes).")
        return

    print(f"Downloading PostgreSQL 16 binaries from {url}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req) as resp, open(dest, "wb") as out_file:
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024 * 4  # 4MB chunks
        last_pct = -1
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = int(downloaded * 100 / total)
                if pct != last_pct and pct % 10 == 0:
                    print(f"Downloaded {pct}% ({downloaded // (1024*1024)}MB / {total // (1024*1024)}MB)")
                    last_pct = pct

    print("Download completed successfully.")

def extract_zip(zip_path: Path, target_dir: Path):
    if (target_dir / "bin" / "postgres.exe").exists():
        print("PostgreSQL binaries already extracted.")
        return
    print(f"Extracting {zip_path.name} to {target_dir}...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(target_dir.parent)
    print("Extraction completed.")

def init_cluster():
    bin_dir = PG_DIR / "bin"
    initdb = bin_dir / "initdb.exe"
    if not (DATA_DIR / "PG_VERSION").exists():
        print("Initializing PostgreSQL database cluster...")
        cmd = [
            str(initdb),
            "-D", str(DATA_DIR),
            "-U", "postgres",
            "-E", "UTF8",
            "--locale=C",
            "-A", "trust"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        print("initdb output:", res.stdout)
        if res.returncode != 0:
            print("initdb error:", res.stderr)
            raise RuntimeError(f"initdb failed: {res.stderr}")
    else:
        print("Database cluster already initialized.")

def start_server():
    bin_dir = PG_DIR / "bin"
    pg_ctl = bin_dir / "pg_ctl.exe"
    log_file = PG_DIR / "server.log"
    print("Starting PostgreSQL server...")
    cmd = [
        str(pg_ctl),
        "-D", str(DATA_DIR),
        "-l", str(log_file),
        "-w",
        "start"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("pg_ctl start output:", res.stdout)
    if res.returncode != 0:
        print("pg_ctl start error:", res.stderr)

def create_user_and_db():
    bin_dir = PG_DIR / "bin"
    psql = bin_dir / "psql.exe"
    
    # Wait for server to respond
    time.sleep(2)
    sql_commands = """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'kanakku') THEN
            CREATE ROLE kanakku WITH LOGIN SUPERUSER PASSWORD 'kanakku_secret_123';
        ELSE
            ALTER ROLE kanakku WITH PASSWORD 'kanakku_secret_123';
        END IF;
    END
    $$;
    """
    cmd = [str(psql), "-U", "postgres", "-p", "5432", "-d", "postgres", "-c", sql_commands]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("Role setup:", res.stdout, res.stderr)
    
    # Check if database kanakku_prod exists
    check_db = [str(psql), "-U", "postgres", "-p", "5432", "-d", "postgres", "-tAc", "SELECT 1 FROM pg_database WHERE datname='kanakku_prod'"]
    db_res = subprocess.run(check_db, capture_output=True, text=True)
    if "1" not in db_res.stdout:
        create_db = [str(psql), "-U", "postgres", "-p", "5432", "-d", "postgres", "-c", "CREATE DATABASE kanakku_prod OWNER kanakku;"]
        res_create = subprocess.run(create_db, capture_output=True, text=True)
        print("Create DB:", res_create.stdout, res_create.stderr)
    else:
        print("Database kanakku_prod already exists.")

if __name__ == "__main__":
    download_file(DOWNLOAD_URL, ZIP_PATH)
    extract_zip(ZIP_PATH, PG_DIR)
    init_cluster()
    start_server()
    create_user_and_db()
    print("PostgreSQL local setup completed successfully.")
