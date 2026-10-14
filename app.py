import os
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
import pypdf

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'txt', 'csv', 'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max limit

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(filepath, filename):
    ext = filename.rsplit('.', 1)[1].lower()
    text = ""
    if ext == 'pdf':
        reader = pypdf.PdfReader(filepath)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    else:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    return text

@app.route('/')
index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file attached", 400
    
    file = request.files['file']
    instruction = request.form.get('instruction', '').lower()

    if file.filename == '':
        return "No selected file", 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Extract content based on file type (PDF, TXT, CSV)
        content = extract_text_from_file(filepath, filename)
        lines = content.splitlines()
        processed_lines = []

        # Execute AI-style transformations based on prompt instruction
        if 'email' in instruction:
            import re
            emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', content)
            processed_lines = sorted(list(set(emails)))
        elif 'phone' in instruction or 'number' in instruction:
            import re
            phones = re.findall(r'\+?[0-9\s\-()]{10,}', content)
            processed_lines = [p.strip() for p in phones if len(p.strip()) >= 10]
        elif 'duplicate' in instruction or 'dedup' in instruction:
            seen = set()
            for line in lines:
                cleaned = line.strip()
                if cleaned and cleaned not in seen:
                    seen.add(cleaned)
                    processed_lines.append(cleaned)
        elif 'mask' in instruction or 'privacy' in instruction:
            import re
            # Mask 4-digit codes or pins
            masked = re.sub(r'\b\d{4}\b', '**', content)
            processed_lines = masked.splitlines()
        elif 'upper' in instruction:
            processed_lines = [line.upper() for line in lines]
        else:
            # Default: clean formatting
            processed_lines = [line.strip() for line in lines if line.strip()]

        # Save output result
        output_filename = f"processed_{filename.rsplit('.', 1)[0]}.txt"
        output_filepath = os.path.join(OUTPUT_FOLDER, output_filename)
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(processed_lines))

        return send_file(output_filepath, as_attachment=True)

    return "Invalid file type. Please upload a .txt, .csv, or .pdf file.", 400

if __name__ == '__main__':
    app.run(debug=True)