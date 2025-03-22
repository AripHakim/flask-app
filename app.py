from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import pdfplumber
import os

app = Flask(__name__)
CORS(app, resources={r"/plagiarism": {"origins": "*"}},
     supports_credentials=True)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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


@app.route('/extract-text', methods=['POST'])
def extract_text():
    if 'pdf' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['pdf']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    try:
        with pdfplumber.open(file_path) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": f"Failed to extract text: {str(e)}"}), 500

@app.route('/plagiarism', methods=['POST'])
def detect_plagiarism():
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
