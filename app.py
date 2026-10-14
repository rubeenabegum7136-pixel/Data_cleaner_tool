import os
import re
import pandas as pd
import pypdf
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'txt', 'csv', 'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

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
def index():
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

        # Extract text content
        content = extract_text_from_file(filepath, filename)
        lines = content.splitlines()

        # Clean message clutter, empty spaces, and headers if requested
        cleaned_rows = []
        for line in lines:
            line_str = line.strip()
            # Skip typical noisy metadata or filler text if needed
            if not line_str or 'Massive Test Records' in line_str or 'This document contains' in line_str:
                continue
            
            # If it looks like a table row with pipes or separators
            if '|' in line_str:
                parts = [p.strip() for p in line_str.split('|')]
                cleaned_rows.append(parts)
            else:
                # Fallback: treat line as a single column record
                cleaned_rows.append([line_str])

        # Convert structured data into a pandas DataFrame
        if cleaned_rows:
            # Check if first row is header
            header = cleaned_rows[0]
            data = cleaned_rows[1:] if len(cleaned_rows) > 1 else []
            
            # If lengths match nicely, build proper columns
            try:
                if data and len(set(len(r) for r in cleaned_rows)) == 1:
                    df = pd.DataFrame(data, columns=header)
                else:
                    df = pd.DataFrame(cleaned_rows)
            except Exception:
                df = pd.DataFrame(cleaned_rows)
        else:
            df = pd.DataFrame(["No data found"])

        # Save output as a clean Excel spreadsheet (.xlsx)
        output_filename = f"structured_{filename.rsplit('.', 1)[0]}.xlsx"
        output_filepath = os.path.join(OUTPUT_FOLDER, output_filename)
        
        df.to_excel(output_filepath, index=False, header=False if len(df.columns) == 1 else True)

        return send_file(output_filepath, as_attachment=True)

    return "Invalid file type. Please upload a .txt, .csv, or .pdf file.", 400

if __name__ == '__main__':
    app.run(debug=True)