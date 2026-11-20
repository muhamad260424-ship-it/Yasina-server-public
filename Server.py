from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import sqlite3, os
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')

def get_db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = get_db(); cur = c.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS siswa (id INTEGER PRIMARY KEY AUTOINCREMENT, nis TEXT UNIQUE NOT NULL, nama TEXT NOT NULL, jenjang TEXT DEFAULT 'SMP', kelas TEXT DEFAULT 'VII-A', ortu TEXT DEFAULT '', wa TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS pemasukan (id INTEGER PRIMARY KEY AUTOINCREMENT, siswa_id INTEGER, siswa_nama TEXT DEFAULT 'Umum', jenjang TEXT DEFAULT 'SMP', jenis TEXT NOT NULL, bulan TEXT DEFAULT 'Januari 2026', jumlah REAL NOT NULL DEFAULT 0, metode TEXT DEFAULT 'TUNAI', tgl TEXT DEFAULT CURRENT_DATE, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS pengeluaran (id INTEGER PRIMARY KEY AUTOINCREMENT, jenjang TEXT DEFAULT 'SMP', jenis TEXT NOT NULL, jumlah REAL NOT NULL DEFAULT 0, penerima TEXT DEFAULT '', ket TEXT DEFAULT '', tgl TEXT DEFAULT CURRENT_DATE, akun TEXT DEFAULT 'Kas Utama', created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    cur.execute("CREATE TABLE IF NOT EXISTS setting (id INTEGER PRIMARY KEY CHECK(id=1), target_smp_spp REAL DEFAULT 2110000, target_smp_infak REAL DEFAULT 13075000, target_smp_dks REAL DEFAULT 5510000, target_smp_ipp REAL DEFAULT 22250000, target_sma_spp REAL DEFAULT 2190000, target_sma_infak REAL DEFAULT 3480000, target_sma_dks REAL DEFAULT 2800000, target_sma_ipp REAL DEFAULT 8820000, target_smk_spp REAL DEFAULT 6480000, target_smk_infak REAL DEFAULT 3450000, target_smk_dks REAL DEFAULT 5200000, target_smk_ipp REAL DEFAULT 24650000, rekening TEXT DEFAULT 'BANK BRI : A.N SITI MASELAH - 479701037976536', pesan_wa TEXT DEFAULT '')")
    cur.execute("SELECT COUNT(*) c FROM setting WHERE id=1")
    if cur.fetchone()['c']==0: cur.execute("INSERT INTO setting (id) VALUES (1)")
    cur.execute("SELECT COUNT(*) c FROM siswa")
    if cur.fetchone()['c']==0:
        cur.executemany("INSERT INTO siswa (nis,nama,jenjang,kelas,ortu,wa) VALUES (?,?,?,?,?,?)", [('001','Ahmad Fauzi','SMP','VII-A','Bapak Ahmad','6281234567890'),('002','Siti Maryam','SMA','X-IPA','Ibu Maryam','6285678901234'),('003','Budi Santoso','SMK','X-MPLB','Bapak Budi','6281111111111')])
        cur.executemany("INSERT INTO pemasukan (siswa_id,siswa_nama,jenjang,jenis,bulan,jumlah,metode,tgl) VALUES (?,?,?,?,?,?,?,?)", [(1,'Ahmad Fauzi (001)','SMP','SPP','Januari 2026',150000,'TUNAI','2026-01-05'),(1,'Ahmad Fauzi (001)','SMP','Infak Pesantren','Januari 2026',200000,'TRANSFER','2026-01-05')])
        cur.executemany("INSERT INTO pengeluaran (jenjang,jenis,jumlah,penerima,ket,tgl) VALUES (?,?,?,?,?,?)", [('SMP','Belanja Sayur',250000,'Pasar','Sayur harian','2026-01-05'),('SMP','Beras',500000,'Toko Beras','Beras 20kg','2026-01-16')])
    c.commit(); c.close(); print(f"[DB] Siap: {DB_PATH}")

init_db()
def d(r): return dict(r) if r else None

@app.route('/')
def index(): return render_template('index.html')
@app.route('/health')
def health(): return jsonify({"status":"ok","server_id":"yasina-utama-2026"}),200

@app.route('/api/data', methods=['GET'])
def api_data():
    try:
        c=get_db()
        siswa=[d(r) for r in c.execute("SELECT * FROM siswa ORDER BY nis").fetchall()]
        masuk=[d(r) for r in c.execute("SELECT * FROM pemasukan ORDER BY created_at DESC").fetchall()]
        keluar=[d(r) for r in c.execute("SELECT * FROM pengeluaran ORDER BY created_at DESC").fetchall()]
        setting=d(c.execute("SELECT * FROM setting WHERE id=1").fetchone())
        c.close()
        return jsonify({"success":True,"siswa":siswa,"masuk":masuk,"keluar":keluar,"setting":setting}),200
    except Exception as e: return jsonify({"success":False,"message":str(e)}),500

@app.route('/api/siswa', methods=['POST'])
def add_siswa():
    try:
        data=request.get_json() or {}; nis=str(data.get('nis','')).strip(); nama=str(data.get('nama','')).strip()
        if not nis or not nama: return jsonify({"success":False,"message":"NIS dan Nama wajib!"}),400
        if nis.isdigit(): nis=nis.zfill(3)
        wa=''.join(filter(str.isdigit, str(data.get('wa',''))))
        if wa.startswith('0'): wa='62'+wa[1:]
        elif wa.startswith('8'): wa='62'+wa
        c=get_db(); c.execute("INSERT INTO siswa (nis,nama,jenjang,kelas,ortu,wa) VALUES (?,?,?,?,?,?) ON CONFLICT(nis) DO UPDATE SET nama=excluded.nama, jenjang=excluded.jenjang, kelas=excluded.kelas, ortu=excluded.ortu, wa=excluded.wa", (nis,nama,str(data.get('jenjang','SMP')),str(data.get('kelas','VII-A')),str(data.get('ortu','')),wa)); c.commit(); c.close()
        return jsonify({"success":True,"message":"Siswa tersimpan!"}),201
    except Exception as e: return jsonify({"success":False,"message":str(e)}),500

@app.route('/api/siswa/<int:id>', methods=['DELETE'])
def del_siswa(id):
    try:
        c=get_db(); c.execute("DELETE FROM siswa WHERE id=?", (id,)); c.commit(); c.close()
        return jsonify({"success":True}),200
    except Exception as e: return jsonify({"success":False,"message":str(e)}),500

@app.route('/api/pemasukan', methods=['POST'])
def add_masuk():
    try:
        data=request.get_json() or {}; jenis=str(data.get('jenis','')).strip(); jumlah=float(data.get('jumlah',0))
        if not jenis or jumlah<=0: return jsonify({"success":False,"message":"Jenis & Jumlah wajib!"}),400
        c=get_db(); c.execute("INSERT INTO pemasukan (siswa_id,siswa_nama,jenjang,jenis,bulan,jumlah,metode,tgl) VALUES (?,?,?,?,?,?,?,?)", (data.get('siswa_id'),str(data.get('siswa_nama','Umum')),str(data.get('jenjang','SMP')),jenis,str(data.get('bulan','Januari 2026')),jumlah,str(data.get('metode','TUNAI')),str(data.get('tgl',datetime.now().strftime('%Y-%m-%d'))))); c.commit(); c.close()
        return jsonify({"success":True,"message":"Pemasukan tersimpan!"}),201
    except Exception as e: return jsonify({"success":False,"message":str(e)}),500

@app.route('/api/pemasukan/<int:id>', methods=['DELETE'])
def del_masuk(id):
    try:
        c=get_db(); c.execute("DELETE FROM pemasukan WHERE id=?", (id,)); c.commit(); c.close()
        return jsonify({"success":True}),200
    except Exception as e: return jsonify({"success":False,"message":str(e)}),500

@app.route('/api/pengeluaran', methods=['POST'])
def add_keluar():
    try:
        data=request.get_json() or {}; jenis=str(data.get('jenis','')).strip(); jumlah=float(data.get('jumlah',0))
        if not jenis or jumlah<=0: return jsonify({"success":False,"message":"Jenis & Jumlah wajib!"}),400
        c=get_db(); c.execute("INSERT INTO pengeluaran (jenjang,jenis,jumlah,penerima,ket,tgl) VALUES (?,?,?,?,?,?)", (str(data.get('jenjang','SMP')),jenis,jumlah,str(data.get('penerima','')),str(data.get('ket','')),str(data.get('tgl',datetime.now().strftime('%Y-%m-%d'))))); c.commit(); c.close()
        return jsonify({"success":True,"message":"Pengeluaran tersimpan!"}),201
    except Exception as e: return jsonify({"success":False,"message":str(e)}),500

@app.route('/api/pengeluaran/<int:id>', methods=['DELETE'])
def del_keluar(id):
    try:
        c=get_db(); c.execute("DELETE FROM pengeluaran WHERE id=?", (id,)); c.commit(); c.close()
        return jsonify({"success":True}),200
    except Exception as e: return jsonify({"success":False,"message":str(e)}),500

if __name__=='__main__':
    print("Buka: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
