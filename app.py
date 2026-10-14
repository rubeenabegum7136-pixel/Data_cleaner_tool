from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Route 1: The Main Web Interface
@app.route('/')
def index():
    return render_template('index.html')

# Route 2: The Core Data-Cleaning Logic (Processes text/data automatically)
@app.route('/process', methods=['POST'])
def process_data():
    raw_data = request.form.get('raw_text', '')
    
    # Simple automated cleaning logic: 
    # Removes extra spaces, trims lines, and capitalizes correctly
    lines = raw_data.splitlines()
    cleaned_lines = [line.strip().title() for line in lines if line.strip()]
    processed_result = "\n".join(cleaned_lines)
    
    return render_template('index.html', original=raw_data, result=processed_result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)