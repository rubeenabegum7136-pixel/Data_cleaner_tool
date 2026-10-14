from flask import Flask, render_template, request, send_file
import os
import re

app = Flask(__name__)

# Security Setting: Maximum file size allowed (5 MB)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 

# Security Setting: Allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_data():
    raw_data = request.form.get('raw_text', '')
    lines = raw_data.splitlines()
    cleaned_lines = [line.strip().title() for line in lines if line.strip()]
    processed_result = "\n".join(cleaned_lines)
    return render_template('index.html', original=raw_data, result=processed_result)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file uploaded", 400
    
    file = request.files['file']
    instruction = request.form.get('instruction', '').lower()
    
    if file.filename == '':
        return "No selected file", 400

    if not allowed_file(file.filename):
        return "Invalid file type. Only .txt and .csv files are allowed.", 400

    if file:
        try:
            content = file.read().decode('utf-8', errors='ignore')
            
            # Feature 1: Extract Emails
            if 'extract email' in instruction or 'emails' in instruction:
                emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', content)
                cleaned_content = "\n".join(list(set(emails)))
                
            # Feature 2: Extract Phone Numbers
            elif 'extract phone' in instruction or 'phone' in instruction:
                phones = re.findall(r'\+?\d[\d -]{8,12}\d', content)
                cleaned_content = "\n".join(list(set(phones)))
                
            # Feature 3: Text Masking & Privacy Cleaner
            elif 'mask' in instruction or 'privacy' in instruction or 'redact' in instruction:
                masked = re.sub(r'\b\d{4}\b', '**', content)
                cleaned_content = masked
                
            # Feature 4: Remove Duplicates
            elif 'remove duplicate' in instruction or 'duplicates' in instruction:
                lines = content.splitlines()
                unique_lines = list(dict.fromkeys([line.strip() for line in lines if line.strip()]))
                cleaned_content = "\n".join(unique_lines)
                
            # Feature 5: Uppercase Conversion
            elif 'uppercase' in instruction:
                lines = content.splitlines()
                cleaned_content = "\n".join([line.strip().upper() for line in lines if line.strip()])
                
            # Default Clean Fallback
            else:
                lines = content.splitlines()
                cleaned_lines = [line.strip().title() for line in lines if line.strip()]
                cleaned_content = "\n".join(cleaned_lines)
            
            output_filename = "processed_" + file.filename
            output_path = os.path.join('/tmp', output_filename) if os.path.exists('/tmp') else output_filename
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
                
            return send_file(output_path, as_attachment=True)
            
        except Exception as e:
            return f"An error occurred while processing the file: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)