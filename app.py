from flask import Flask, request, jsonify
from flask_cors import CORS
from pdfminer.high_level import extract_text
import hashlib
import os
import base64
import io

app = Flask(__name__)
CORS(app, resources={r"/plagiarism": {"origins": ["https://winnowing-web.vercel.app", "exp://*"]}},
     supports_credentials=True)

def winnowing_fingerprint(text, k, window_size):
    shingles = [text[i:i+k] for i in range(len(text) - k + 1)]
    hashes = [hashlib.sha256(shingle.encode('utf-8')).hexdigest() for shingle in shingles]
    
    fingerprints = []
    for i in range(len(hashes) - window_size + 1):
        window = hashes[i:i+window_size]
        fingerprints.append(min(window))  # Take the smallest hash in the window
    
    return fingerprints



def extract_text_from_base64(pdf_base64):
    pdf_bytes = base64.b64decode(pdf_base64)
    pdf_stream = io.BytesIO(pdf_bytes)
    text = extract_text(pdf_stream)
    return text


def compare_documents(doc1, doc2, k, window_size):
    fp1 = winnowing_fingerprint(doc1, k, window_size)
    fp2 = winnowing_fingerprint(doc2, k, window_size)
    
    common_fingerprints = set(fp1) & set(fp2)  # Intersection of both fingerprint sets
    similarity = len(common_fingerprints) / max(len(fp1), len(fp2)) * 100
    return similarity
    
@app.route('/plagiarism', methods=['POST', 'OPTIONS'])
def detect_plagiarism():
    if request.method == 'OPTIONS':
         return '', 200  # Tangani request preflight agar tidak error
         
    data = request.json
    documents = data['documents']
    k = data['k']
    window_size = data['window_size']
    
    similarities = []
    
    for i in range(len(documents)):
        for j in range(i + 1, len(documents)):
            similarity = compare_documents(documents[i], documents[j], k, window_size)
            similarities.append({
                'doc1_index': i,
                'doc2_index': j,
                'similarity': similarity
            })
    
    return jsonify({'similarities': similarities})

     
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
