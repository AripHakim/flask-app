from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import fitz  # PyMuPDF untuk ekstrak teks dari PDF
import os

app = Flask(__name__)
CORS(app, resources={r"/plagiarism": {"origins": "*"}}, supports_credentials=True)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Buat folder uploads jika belum ada


def extract_text_from_pdf(pdf_path):
    """Ekstrak teks dari file PDF"""
    try:
        doc = fitz.open(pdf_path)  # Buka file PDF
        text = "\n".join([page.get_text("text") for page in doc])  # Gabungkan teks dari setiap halaman
        return text.strip()
    except Exception as e:
        return f"Error membaca PDF: {e}"


def winnowing_fingerprint(text, k, window_size):
    """Membuat fingerprint menggunakan Winnowing"""
    shingles = [text[i:i + k] for i in range(len(text) - k + 1)]
    hashes = [hashlib.sha256(shingle.encode('utf-8')).hexdigest() for shingle in shingles]

    fingerprints = []
    for i in range(len(hashes) - window_size + 1):
        window = hashes[i:i + window_size]
        fingerprints.append(min(window))  # Ambil hash terkecil di setiap window

    return fingerprints


def compare_documents(doc1, doc2, k, window_size):
    """Membandingkan dua dokumen menggunakan Winnowing"""
    fp1 = winnowing_fingerprint(doc1, k, window_size)
    fp2 = winnowing_fingerprint(doc2, k, window_size)

    common_fingerprints = set(fp1) & set(fp2)  # Cek fingerprint yang sama
    similarity = (len(common_fingerprints) / max(len(fp1), len(fp2))) * 100 if max(len(fp1), len(fp2)) > 0 else 0
    return similarity


@app.route('/plagiarism', methods=['POST', 'OPTIONS'])
def detect_plagiarism():
    if request.method == 'OPTIONS':
        return '', 200  # Tangani preflight request dari CORS

    if 'files' not in request.files:
        return jsonify({'error': 'Tidak ada file yang diunggah'}), 400

    files = request.files.getlist('files')
    k = int(request.form.get('k', 5))
    window_size = int(request.form.get('window_size', 4))

    texts = []
    filenames = []

    for file in files:
        if file.filename == '':
            continue

        filename = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filename)  # Simpan file ke folder uploads

        extracted_text = extract_text_from_pdf(filename)  # Ekstrak teks dari PDF
        texts.append(extracted_text)
        filenames.append(file.filename)

    similarities = []

    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            similarity = compare_documents(texts[i], texts[j], k, window_size)
            similarities.append({
                'doc1': filenames[i],
                'doc2': filenames[j],
                'similarity': similarity
            })

    return jsonify({'similarities': similarities})


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
