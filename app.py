import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import time
import firebase_admin
from firebase_admin import credentials, firestore
import datetime

app = Flask(__name__)

# --- Konfigurasi Firebase/Firestore ---
FIREBASE_SERVICE_ACCOUNT_KEY = os.path.join(app.root_path, 'serviceAccountKey.json')
db = None
try:
    cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Koneksi Firebase/Firestore berhasil.")
except Exception as e:
    print(f"Gagal terhubung ke Firebase/Firestore: {e}")

# --- Konfigurasi Data Bus Lokal ---
BUS_ROUTES_FILE = os.path.join(app.root_path, 'data', 'rute-bis.json')
bus_routes_data = []
try:
    with open(BUS_ROUTES_FILE, 'r', encoding='utf-8') as f:
        bus_routes_data = json.load(f)
    print(f"Berhasil memuat {len(bus_routes_data)} rute bus dari {BUS_ROUTES_FILE}")
except FileNotFoundError:
    print(f"Error: File '{BUS_ROUTES_FILE}' tidak ditemukan.")
except json.JSONDecodeError:
    print(f"Error: Gagal parse JSON dari '{BUS_ROUTES_FILE}'. Pastikan formatnya benar.")

# --- Konfigurasi Penyimpanan Lokal untuk Pemesanan Tiket dan Pengukuran ---
LOCAL_BOOKINGS_FILE = os.path.join(app.root_path, 'data', 'local_bookings.json')
LOCAL_MEASUREMENTS_FILE = os.path.join(app.root_path, 'data', 'local_measurements.json')

def save_to_local_json(booking_data):
    """Fungsi untuk menyimpan data pemesanan ke file JSON lokal secara aman."""
    bookings = []
    
    # --- STEP 1: Baca data yang sudah ada ---
    if os.path.exists(LOCAL_BOOKINGS_FILE) and os.path.getsize(LOCAL_BOOKINGS_FILE) > 0:
        try:
            with open(LOCAL_BOOKINGS_FILE, 'r', encoding='utf-8') as f:
                bookings = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {LOCAL_BOOKINGS_FILE} contains invalid JSON or is empty. Starting with an empty list for bookings.")
            bookings = []
        except Exception as e:
            print(f"Error reading {LOCAL_BOOKINGS_FILE}: {e}. Starting with an empty list for bookings.")
            bookings = []

    # --- STEP 2: Tambahkan data baru ---
    # Pastikan data yang masuk adalah tipe dasar Python untuk JSON
    # Konversi datetime object kembali ke ISO string jika perlu, karena json.dump tidak bisa serialize datetime object langsung
    if isinstance(booking_data.get('booking_time'), datetime.datetime):
        booking_data['booking_time'] = booking_data['booking_time'].isoformat()
    
    # Tambahkan timestamp lokal saat disimpan ke file
    booking_data['timestamp_local_saved'] = time.time() 

    bookings.append(booking_data)

    # --- STEP 3: Tulis ke file sementara, lalu ganti file asli ---
    temp_file_path = LOCAL_BOOKINGS_FILE + '.tmp'
    try:
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(bookings, f, indent=4, ensure_ascii=False)
        
        # Jika berhasil ditulis ke file sementara, ganti file asli
        os.replace(temp_file_path, LOCAL_BOOKINGS_FILE)
        print(f"Data pemesanan berhasil disimpan ke {LOCAL_BOOKINGS_FILE}")
    except Exception as e:
        print(f"Error writing to {LOCAL_BOOKINGS_FILE} (via temp file): {e}")
        # Jika terjadi error saat menulis, pastikan file sementara dihapus
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def save_measurement_log_local(log_data):
    """Fungsi untuk menyimpan log pengukuran ke file JSON lokal secara aman."""
    measurements = []
    
    # --- STEP 1: Baca data yang sudah ada ---
    if os.path.exists(LOCAL_MEASUREMENTS_FILE) and os.path.getsize(LOCAL_MEASUREMENTS_FILE) > 0:
        try:
            with open(LOCAL_MEASUREMENTS_FILE, 'r', encoding='utf-8') as f:
                measurements = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {LOCAL_MEASUREMENTS_FILE} contains invalid JSON or is empty. Starting with an empty list for measurements.")
            measurements = []
        except Exception as e:
            print(f"Error reading {LOCAL_MEASUREMENTS_FILE}: {e}. Starting with an empty list for measurements.")
            measurements = []

    # --- STEP 2: Tambahkan data baru ---
    # Konversi Firestore Timestamp atau datetime object ke float/ISO string
    if isinstance(log_data.get('timestamp_booking'), firestore.SERVER_TIMESTAMP.__class__):
        log_data['timestamp_booking'] = log_data['timestamp_booking'].timestamp()
    elif isinstance(log_data.get('timestamp_booking'), datetime.datetime):
        log_data['timestamp_booking'] = log_data['timestamp_booking'].timestamp()

    if isinstance(log_data.get('timestamp_test'), firestore.SERVER_TIMESTAMP.__class__):
        log_data['timestamp_test'] = log_data['timestamp_test'].timestamp()
    elif isinstance(log_data.get('timestamp_test'), datetime.datetime):
        log_data['timestamp_test'] = log_data['timestamp_test'].timestamp()

    # Pastikan list latencies yang dikirim ke lokal JSON tidak mengandung Firestore Timestamp object
    # Ini penting karena json.dump tidak bisa serialize objek Firestore Timestamp
    if 'all_firestore_latencies' in log_data and log_data['all_firestore_latencies'] is not None:
        log_data['all_firestore_latencies'] = [l.timestamp() if isinstance(l, firestore.SERVER_TIMESTAMP.__class__) else l for l in log_data['all_firestore_latencies']]
    if 'all_local_latencies' in log_data and log_data['all_local_latencies'] is not None:
        log_data['all_local_latencies'] = [l.timestamp() if isinstance(l, firestore.SERVER_TIMESTAMP.__class__) else l for l in log_data['all_local_latencies']]
        
    measurements.append(log_data)

    # --- STEP 3: Tulis ke file sementara, lalu ganti file asli ---
    temp_file_path = LOCAL_MEASUREMENTS_FILE + '.tmp'
    try:
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(measurements, f, indent=4, ensure_ascii=False)
        
        os.replace(temp_file_path, LOCAL_MEASUREMENTS_FILE)
        print(f"Log pengukuran berhasil disimpan ke {LOCAL_MEASUREMENTS_FILE}")
    except Exception as e:
        print(f"Error writing to {LOCAL_MEASUREMENTS_FILE} (via temp file): {e}")
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
# --- Routing Aplikasi ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/bus-list.html')
def list_bis():
    return render_template('list_bis.html')

@app.route('/form_tiket.html')
def form_tiket():
    return render_template('form_tiket.html')

@app.route('/measurement_results.html')
def measurement_results():
    return render_template('measurement_results.html')

# --- API Endpoint untuk Pemesanan Tiket Tunggal ---
@app.route('/api/bus_routes', methods=['GET'])
def get_bus_routes():
    return jsonify(bus_routes_data)

@app.route('/api/book_ticket', methods=['POST'])
def book_ticket():
    received_data = request.get_json()
    if not received_data:
        return jsonify({"success": False, "message": "Data tidak valid."}), 400

    # Validasi field wajib sesuai yang dikirim dari frontend
    required_fields = ['namaLengkap', 'email', 'bus_id', 'seat_booked', 'total_payment', 'booking_time', 'tanggalBerangkat']
    if not all(field in received_data and received_data[field] for field in required_fields):
        return jsonify({"success": False, "message": "Semua field wajib diisi (namaLengkap, email, bus_id, seat_booked, total_payment, booking_time, tanggalBerangkat)."}), 400

    # Ambil detail bus berdasarkan bus_id
    selected_bus_detail = next((bus for bus in bus_routes_data if str(bus['id']) == str(received_data['bus_id'])), None)
    if not selected_bus_detail:
        return jsonify({"success": False, "message": "Bus ID tidak ditemukan."}), 400

    # Siapkan data untuk disimpan, sesuai skema tiket_payment dan bus
    # Mengabaikan payment_id (auto-generated oleh Firestore) dan user_id (belum diimplementasikan)
    data_to_save = {
        # Dari tiket_payment
        "bus_id": received_data['bus_id'],
        # "user_id": "dummy_user_id_123", # Diabaikan dulu
        "seat_booked": received_data['seat_booked'],
        "total_payment": received_data['total_payment'],
        "booking_time": datetime.datetime.fromisoformat(received_data['booking_time']), # Konversi ISO string ke datetime object

        # Informasi pengguna (dari form)
        "nama_lengkap_pemesan": received_data['namaLengkap'], # Tambahkan ini agar ada di tiket_payment
        "email_pemesan": received_data['email'], # Tambahkan ini agar ada di tiket_payment

        # Informasi tanggal berangkat (dari form)
        "tanggal_keberangkatan": received_data['tanggalBerangkat'],

        # Informasi bus (dari data rute-bis.json, terkait dengan bus_id)
        "bus_jurusan": selected_bus_detail['jurusan'],
        "bus_rute_pergi": selected_bus_detail['rute_pergi'],
        "bus_rute_pulang": selected_bus_detail['rute_pulang'],
        "bus_harga": selected_bus_detail['harga'], # Harga per tiket dari rute-bis.json
        # "bus_jumlah_kursi": selected_bus_detail['jumlah_kursi'], # jika ada di rute-bis.json
    }

    latency_firestore = None
    latency_local = None
    ticket_id_firestore = None
    ticket_id_local = "LOCAL_" + str(int(time.time() * 1000))

    # Simpan ke Firestore
    if db:
        start_time_firestore = time.perf_counter()
        try:
            firestore_data = data_to_save.copy()
            firestore_data['timestamp_server_firestore'] = firestore.SERVER_TIMESTAMP # Timestamp saat Firestore menerima
            update_time, doc_ref = db.collection('ticket_payments').add(firestore_data) # Nama koleksi sesuai skema
            ticket_id_firestore = doc_ref.id
            latency_firestore = (time.perf_counter() - start_time_firestore) * 1000
            print(f"Pemesanan Firestore berhasil dalam {latency_firestore:.2f} ms")
        except Exception as e:
            print(f"Error saat menyimpan ke Firestore: {e}")
            latency_firestore = -1
    else:
        print("Firestore tidak terkoneksi, melewati penyimpanan Firestore.")

    # Simpan ke Lokal JSON
    start_time_local = time.perf_counter()
    try:
        # Untuk lokal, kita bisa simpan data_to_save apa adanya
        save_to_local_json(data_to_save)
        latency_local = (time.perf_counter() - start_time_local) * 1000
        print(f"Pemesanan Lokal berhasil dalam {latency_local:.2f} ms")
    except Exception as e:
        print(f"Error saat menyimpan ke JSON lokal: {e}")
        latency_local = -1

    # Simpan hasil pengukuran ke log terpisah (lokal dan Firestore)
    measurement_log = {
        "type": "single_booking",
        "timestamp_booking": time.time(),
        "latency_firestore_ms": latency_firestore,
        "latency_local_ms": latency_local,
        "ticket_id_firestore": ticket_id_firestore,
        "ticket_id_local": ticket_id_local
    }

    if db:
        try:
            db.collection('measurement_logs').add(measurement_log)
            print("Log pengukuran single_booking disimpan ke Firestore.")
        except Exception as e:
            print(f"Error saat menyimpan log pengukuran single_booking ke Firestore: {e}")
    
    save_measurement_log_local(measurement_log)

    return jsonify({
        "success": True,
        "message": "Pemesanan berhasil diproses.",
        "ticket_id_firestore": ticket_id_firestore,
        "ticket_id_local": ticket_id_local,
        "latency_firestore_ms": latency_firestore,
        "latency_local_ms": latency_local
    }), 201

# --- NEW API Endpoint: Menjalankan Tes Performa ---
@app.route('/api/run_performance_test', methods=['POST'])
def run_performance_test():
    test_params = request.get_json()
    num_iterations = test_params.get('iterations', 10)
    
    if num_iterations <= 0:
        return jsonify({"success": False, "message": "Jumlah iterasi harus lebih dari 0."}), 400

    firestore_latencies = []
    local_latencies = []
    
    # Generate dummy data for testing
    selected_bus_for_test = bus_routes_data[0] if bus_routes_data else {
        'id': 'DUMMY_BUS_ID', 'jurusan': 'Dummy Route', 'rute_pergi': 'Dummy Start',
        'rute_pulang': 'Dummy End', 'harga': 5000
    }

    total_start_time = time.perf_counter()

    for i in range(num_iterations):
        dummy_booking_time = datetime.datetime.now().isoformat() # ISO string untuk dummy booking time
        dummy_data_to_save = {
            "bus_id": selected_bus_for_test['id'],
            # "user_id": "dummy_user_id_test",
            "seat_booked": f"A{i+1},B{i+1}",
            "total_payment": selected_bus_for_test['harga'] * 2, # Asumsi 2 kursi
            "booking_time": datetime.datetime.fromisoformat(dummy_booking_time), # Konversi
            "nama_lengkap_pemesan": f"Test User {i}",
            "email_pemesan": f"test{i}@example.com",
            "tanggal_keberangkatan": datetime.date.today().isoformat(),
            "bus_jurusan": selected_bus_for_test['jurusan'],
            "bus_rute_pergi": selected_bus_for_test['rute_pergi'],
            "bus_rute_pulang": selected_bus_for_test['rute_pulang'],
            "bus_harga": selected_bus_for_test['harga'],
        }

        # Test Firestore Save
        if db:
            start_time = time.perf_counter()
            try:
                firestore_test_data = dummy_data_to_save.copy()
                firestore_test_data['timestamp_server_firestore'] = firestore.SERVER_TIMESTAMP
                db.collection('test_payments').add(firestore_test_data) # Simpan di koleksi terpisah agar tidak bercampur
                latency = (time.perf_counter() - start_time) * 1000
                firestore_latencies.append(latency)
            except Exception as e:
                print(f"Error pada iterasi {i} saat tes Firestore: {e}")
                firestore_latencies.append(-1)
        else:
            firestore_latencies.append(-1)

        # Test Local JSON Save
        start_time = time.perf_counter()
        try:
            save_to_local_json(dummy_data_to_save) # Gunakan fungsi yang sama
            latency = (time.perf_counter() - start_time) * 1000
            local_latencies.append(latency)
        except Exception as e:
            print(f"Error pada iterasi {i} saat tes Lokal: {e}")
            local_latencies.append(-1)
    
    total_end_time = time.perf_counter()
    total_duration = total_end_time - total_start_time

    avg_firestore_latency = sum([l for l in firestore_latencies if l != -1]) / len([l for l in firestore_latencies if l != -1]) if any(l != -1 for l in firestore_latencies) else None
    avg_local_latency = sum([l for l in local_latencies if l != -1]) / len([l for l in local_latencies if l != -1]) if any(l != -1 for l in local_latencies) else None

    firestore_successful_ops = len([l for l in firestore_latencies if l != -1])
    local_successful_ops = len([l for l in local_latencies if l != -1])

    firestore_throughput = firestore_successful_ops / (sum([l for l in firestore_latencies if l != -1]) / 1000) if firestore_successful_ops > 0 and sum([l for l in firestore_latencies if l != -1]) > 0 else 0
    local_throughput = local_successful_ops / (sum([l for l in local_latencies if l != -1]) / 1000) if local_successful_ops > 0 and sum([l for l in local_latencies if l != -1]) > 0 else 0


    test_log = {
        "type": "performance_test",
        "timestamp_test": time.time(),
        "iterations": num_iterations,
        "total_duration_seconds": total_duration,
        "avg_firestore_latency_ms": avg_firestore_latency,
        "avg_local_latency_ms": avg_local_latency,
        "firestore_throughput_ops_per_sec": firestore_throughput,
        "local_throughput_ops_per_sec": local_throughput,
        "all_firestore_latencies": firestore_latencies,
        "all_local_latencies": local_latencies
    }

    if db:
        try:
            db.collection('measurement_logs').add(test_log)
            print("Log tes performa disimpan ke Firestore.")
        except Exception as e:
            print(f"Error saat menyimpan log tes performa ke Firestore: {e}")
    
    save_measurement_log_local(test_log)

    return jsonify({
        "success": True,
        "message": "Tes performa selesai.",
        "iterations": num_iterations,
        "total_duration_seconds": total_duration,
        "avg_firestore_latency_ms": avg_firestore_latency,
        "avg_local_latency_ms": avg_local_latency,
        "firestore_throughput_ops_per_sec": firestore_throughput,
        "local_throughput_ops_per_sec": local_throughput,
        "all_firestore_latencies": firestore_latencies, # Kirim ini ke frontend
        "all_local_latencies": local_latencies        # Kirim ini ke frontend
    })

@app.route('/api/get_measurements', methods=['GET'])
def get_measurements():
    measurements = []
    
    if db:
        try:
            docs = db.collection('measurement_logs').order_by('timestamp_booking', direction=firestore.Query.DESCENDING).limit(50).stream() 
            # Jika ingin ambil berdasarkan timestamp_test juga, perlu gabungkan query atau ambil semua
            # Untuk sekarang, ambil yang paling baru.
            
            for doc in docs:
                data = doc.to_dict()
                # Handle Firestore Timestamps for single_booking and performance_test types
                if 'timestamp_booking' in data and hasattr(data['timestamp_booking'], 'timestamp'):
                    data['timestamp_booking'] = data['timestamp_booking'].timestamp()
                elif 'timestamp_test' in data and hasattr(data['timestamp_test'], 'timestamp'):
                    data['timestamp_test'] = data['timestamp_test'].timestamp()
                
                # Handle Firestore datetime objects for booking_time in test_payments
                if 'booking_time' in data and isinstance(data['booking_time'], datetime.datetime):
                    data['booking_time'] = data['booking_time'].isoformat()
                
                # Ensure all_firestore_latencies and all_local_latencies are arrays if they exist
                if 'all_firestore_latencies' in data and not isinstance(data['all_firestore_latencies'], list):
                    data['all_firestore_latencies'] = []
                if 'all_local_latencies' in data and not isinstance(data['all_local_latencies'], list):
                    data['all_local_latencies'] = []

                measurements.append(data)
            print(f"Berhasil mengambil {len(measurements)} log pengukuran dari Firestore.")
        except Exception as e:
            print(f"Error saat mengambil log pengukuran dari Firestore: {e}")
            if os.path.exists(LOCAL_MEASUREMENTS_FILE) and os.path.getsize(LOCAL_MEASUREMENTS_FILE) > 0:
                try:
                    with open(LOCAL_MEASUREMENTS_FILE, 'r', encoding='utf-8') as f:
                        measurements = json.load(f)
                    print(f"Fallback: Berhasil mengambil {len(measurements)} log pengukuran dari lokal.")
                except json.JSONDecodeError:
                    measurements = []
    else:
        if os.path.exists(LOCAL_MEASUREMENTS_FILE) and os.path.getsize(LOCAL_MEASUREMENTS_FILE) > 0:
            try:
                with open(LOCAL_MEASUREMENTS_FILE, 'r', encoding='utf-8') as f:
                    measurements = json.load(f)
                print(f"Mengambil {len(measurements)} log pengukuran dari lokal (Firestore tidak terkoneksi).")
            except json.JSONDecodeError:
                measurements = []
    
    # Sort by timestamp, prioritizing test logs if they are more recent
    measurements.sort(key=lambda x: x.get('timestamp_booking') or x.get('timestamp_test') or 0, reverse=True)
    
    return jsonify(measurements)


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    app.run(debug=True)