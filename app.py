from flask import Flask, request, jsonify
from flask_cors import CORS
from pdfminer.high_level import extract_text
import hashlib
import base64
import io

app = Flask(__name__)

# Mengizinkan CORS agar bisa diakses dari web dan mobile
CORS(app, resources={r"/plagiarism": {"origins": "*"}}, 
     supports_credentials=True, methods=["GET", "POST", "OPTIONS"])

def winnowing_fingerprint(text, k, window_size):
    """ Menghasilkan fingerprint menggunakan algoritma Winnowing """
    shingles = [text[i:i+k] for i in range(len(text) - k + 1)]
    hashes = [hashlib.sha256(shingle.encode('utf-8')).hexdigest() for shingle in shingles]

    fingerprints = []
    for i in range(len(hashes) - window_size + 1):
        window = hashes[i:i+window_size]
        fingerprints.append(min(window))  # Ambil nilai hash terkecil di window

    return fingerprints

def extract_text_from_base64(pdf_base64):
    """ Mengonversi PDF dalam Base64 menjadi teks """
    try:
        pdf_bytes = base64.b64decode(pdf_base64)
        pdf_stream = io.BytesIO(pdf_bytes)
        text = extract_text(pdf_stream)
        return text if text else "No text extracted"
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def compare_documents(doc1, doc2, k, window_size):
    """ Membandingkan dua dokumen menggunakan Winnowing """
    fp1 = winnowing_fingerprint(doc1, k, window_size)
    fp2 = winnowing_fingerprint(doc2, k, window_size)

    common_fingerprints = set(fp1) & set(fp2)  # Irisan fingerprint
    similarity = (len(common_fingerprints) / max(len(fp1), len(fp2))) * 100 if max(len(fp1), len(fp2)) > 0 else 0
    return similarity

@app.route('/plagiarism', methods=['POST', 'OPTIONS'])
def detect_plagiarism():
    """ Endpoint untuk mendeteksi plagiarisme """
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'Preflight request handled'})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response, 200

    try:
        # Cek apakah request mengandung JSON
        if not request.is_json:
            return jsonify({"error": "Invalid JSON format"}), 400
        
        data = request.get_json()

        # Pastikan JSON memiliki semua kunci yang diperlukan
        if 'documents' not in data or 'k' not in data or 'window_size' not in data:
            return jsonify({"error": "Missing required fields"}), 400
        
        documents_base64 = data['documents']
        k = data['k']
        window_size = data['window_size']

        extracted_texts = []
        for pdf in documents_base64:
            text = extract_text_from_base64(pdf)
            extracted_texts.append(text)

        similarities = []
        for i in range(len(extracted_texts)):
            for j in range(i + 1, len(extracted_texts)):
                similarity = compare_documents(extracted_texts[i], extracted_texts[j], k, window_size)
                similarities.append({
                    'doc1_index': i,
                    'doc2_index': j,
                    'similarity': similarity
                })

        response = jsonify({'similarities': similarities})
        response.headers.add("Access-Control-Allow-Origin", "*")  # Pastikan semua request diizinkan
        return response

    except Exception as e:
        print("Error:", str(e))  # Debugging log di terminal
        return jsonify({"error": str(e)}), 500  # Response error 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
