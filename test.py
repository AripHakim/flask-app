import hashlib
import PyPDF2

def winnowing_fingerprint(text, k, window_size):
    shingles = [text[i:i+k] for i in range(len(text) - k + 1)]
    hashes = [hashlib.md5(shingle.encode('utf-8')).hexdigest() for shingle in shingles]

    fingerprints = []
    for i in range(len(hashes) - window_size + 1):
        window = hashes[i:i+window_size]
        fingerprints.append(min(window))  # Take the smallest hash in the window
    
    return fingerprints

def compare_documents(doc1, doc2, k, window_size):
    fp1 = winnowing_fingerprint(doc1, k, window_size)
    fp2 = winnowing_fingerprint(doc2, k, window_size)
    
    common_fingerprints = set(fp1) & set(fp2)  # Intersection of both fingerprint sets
    similarity = len(common_fingerprints) / max(len(fp1), len(fp2)) * 100
    return similarity
    
def detect_plagiarism(documents, k, window_size):
    similarities = []
    
    for i in range(len(documents)):
        for j in range(i + 1, len(documents)):
            similarity = compare_documents(documents[i], documents[j], k, window_size)
            similarities.append({
                'doc1_index': i,
                'doc2_index': j,
                'similarity': similarity
            })
    
    return similarities

def display_fingerprints(document, k, window_size):
    fingerprints = winnowing_fingerprint(document, k, window_size)
    print(f"Fingerprints for the document: {fingerprints}")

if __name__ == '__main__':
    # Example usage
    def read_pdf(file_path):
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ''
                num_pages = len(reader.pages)
                print(f"Number of pages in {file_path}: {num_pages}")
                for page_num in range(num_pages):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    print(f"Text from page {page_num} of {file_path}: {page_text[:500]}")  # Print first 500 characters for brevity
                    text += page_text
            return text
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return ''

    # Example usage
    pdf_files = ["docs/Arief Rahman Hakim.pdf", "docs/Faiz.pdf"]
    documents = [read_pdf(file) for file in pdf_files]
    
    # Print the extracted text for debugging
    for i, doc in enumerate(documents):
        print(f"Document {i} text: {doc[:500]}")  # Print first 500 characters for brevity
    
    k = 5
    window_size = 4
    similarities = detect_plagiarism(documents, k, window_size)
    print(similarities)
    
    # Display fingerprints for the first document
    display_fingerprints(documents[0], k, window_size)
