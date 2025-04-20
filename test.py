from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import pdfplumber
import os
import sqlite3
import fitz  # PyMuPDF
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

UPLOAD_FOLDER = "upload"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Inisialisasi dan koneksi ke SQLite ---
DB_PATH = 'plagiarism.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS plagiarism_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc1_name TEXT,
            doc2_name TEXT,
            doc1_text TEXT,
            doc2_text TEXT,
            similarity REAL,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def save_result_to_db(doc1_name, doc2_name, doc1_text, doc2_text, similarity):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO plagiarism_results 
        (doc1_name, doc2_name, doc1_text, doc2_text, similarity) 
        VALUES (?, ?, ?, ?, ?)
    ''', (doc1_name, doc2_name, doc1_text, doc2_text, similarity))
    conn.commit()
    conn.close()


# --- Fungsi Winnowing & Plagiarism ---
def winnowing_fingerprint(text, k, window_size):
    shingles = [text[i:i+k] for i in range(len(text) - k + 1)]
    hashes = [hashlib.sha256(shingle.encode('utf-8')).hexdigest() for shingle in shingles]

    fingerprints = []
    for i in range(len(hashes) - window_size + 1):
        window = hashes[i:i+window_size]
        fingerprints.append(min(window)) 
    
    return fingerprints

def compare_documents(doc1, doc2, k, window_size):
    fp1 = winnowing_fingerprint(doc1, k, window_size)
    fp2 = winnowing_fingerprint(doc2, k, window_size)
    
    common_fingerprints = set(fp1) & set(fp2)  
    similarity = len(common_fingerprints) / max(len(fp1), len(fp2)) * 100
    return similarity

# --- Ekstrak teks dari PDF ---
@app.route('/extract-text', methods=['POST'])
def extract_text():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    pdf_file = request.files['pdf']
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype='pdf')
        text = ""
        for page in doc:
            text += page.get_text()
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- Endpoint untuk cek plagiarisme ---
@app.route('/plagiarism', methods=['POST'])
def detect_plagiarism():
    data = request.json
    documents = data['documents']  # [{'name': ..., 'text': ...}]
    k = data['k']
    window_size = data['window_size']

    similarities = []

    for i in range(len(documents)):
        for j in range(i + 1, len(documents)):
            doc1 = documents[i]
            doc2 = documents[j]

            similarity = compare_documents(doc1['text'], doc2['text'], k, window_size)

            result = {
                'doc1_index': i,
                'doc2_index': j,
                'doc1_name': doc1['name'],
                'doc2_name': doc2['name'],
                'similarity': similarity
            }
            similarities.append(result)

            save_result_to_db(
                doc1_name=doc1['name'],
                doc2_name=doc2['name'],
                doc1_text=doc1['text'],
                doc2_text=doc2['text'],
                similarity=similarity
            )

    return jsonify({'similarities': similarities})

# Menampilkan Riwayat
@app.route('/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, doc1_name, doc2_name, similarity, checked_at FROM plagiarism_results ORDER BY checked_at DESC')
    rows = c.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            'id': row[0],
            'doc1_name': row[1],
            'doc2_name': row[2],
            'similarity': row[3],
            'checked_at': row[4]
        })

    return jsonify({'history': history})


# --- Menjalankan server ---
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
