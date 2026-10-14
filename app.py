import os
import re
import pypdf
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

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

def generate_structured_pdf(parsed_rows, output_filepath):
    # Use landscape letter for wide table layout
    doc = SimpleDocTemplate(output_filepath, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=15
    )

    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#334155')
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica-Bold',
        textColor=colors.whitesmoke
    )

    story.append(Paragraph("NexusAI Cleaned & Structured Data Report", title_style))
    story.append(Spacer(1, 10))

    # Format all rows into Paragraphs to enable auto-wrapping inside table cells
    table_data = []
    
    # Add header
    table_data.append([
        Paragraph("ID", header_style),
        Paragraph("Customer Name", header_style),
        Paragraph("Email Address", header_style),
        Paragraph("Phone Number", header_style),
        Paragraph("Notes / Details", header_style)
    ])

    for row in parsed_rows:
        if len(row) >= 5:
            table_data.append([
                Paragraph(row[0], cell_style),
                Paragraph(row[1], cell_style),
                Paragraph(row[2], cell_style),
                Paragraph(row[3], cell_style),
                Paragraph(row[4], cell_style)
            ])

    # Build ReportLab Table with proper column widths
    t = Table(table_data, colWidths=[40, 130, 180, 110, 290])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,1), (-1,-1), 4),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
    ]))

    story.append(t)
    doc.build(story)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file attached", 400
    
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        content = extract_text_from_file(filepath, filename)
        lines = content.splitlines()

        # Intelligent row parser for pipe-separated or unstructured records
        parsed_rows = []
        for line in lines:
            line_str = line.strip()
            if not line_str or 'Massive Test Records' in line_str or 'This document contains' in line_str or 'ID | Customer Name' in line_str:
                continue
            
            if '|' in line_str:
                parts = [p.strip() for p in line_str.split('|')]
                if len(parts) >= 5:
                    parsed_rows.append(parts[:5])

        # Fallback if text format differs: extract emails/phones into structured rows
        if not parsed_rows:
            emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', content)
            phones = re.findall(r'\+?[0-9\s\-()]{10,}', content)
            for i in range(max(len(emails), len(phones))):
                em = emails[i] if i < len(emails) else "N/A"
                ph = phones[i].strip() if i < len(phones) else "N/A"
                parsed_rows.append([str(i+1), f"Record {i+1}", em, ph, "Extracted via AI pipeline"])

        output_filename = f"structured_report_{filename.rsplit('.', 1)[0]}.pdf"
        output_filepath = os.path.join(OUTPUT_FOLDER, output_filename)
        
        generate_structured_pdf(parsed_rows, output_filepath)

        return send_file(output_filepath, as_attachment=True)

    return "Invalid file type.", 400

if __name__ == '__main__':
    app.run(debug=True)