from flask import Flask, request, render_template, send_file
import io
import zipfile
import fitz  # PyMuPDF
from PIL import Image
import re

app = Flask(__name__)

def sanitize_filename(filename):
    sanitized = re.sub(r'\W+', '_', filename)
    sanitized = re.sub(r'_+', '_', sanitized)
    return sanitized.strip('_')

def convert_image_mode(image, mode='RGB'):
    if image.mode != mode:
        image = image.convert(mode)
    return image

def extract_images_from_pdf(file_stream, image_type='png', image_mode='RGB'):
    image_data = []
    doc = fitz.open(stream=file_stream.read(), filetype="pdf")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images(full=True)
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image = Image.open(io.BytesIO(image_bytes))
            image = convert_image_mode(image, mode=image_mode)
            
            image_io = io.BytesIO()
            image.save(image_io, format=image_type.upper())
            image_io.seek(0)
            image_data.append((f"page_{page_num + 1}_{img_index + 1}.{image_type.lower()}", image_io))
    
    doc.close()
    return image_data

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        pdf_files = request.files.getlist('pdf_files')  # Get list of files
        image_type = request.form['image_type']
        image_mode = request.form['image_mode']

        # Extract images and prepare zip file
        zip_io = io.BytesIO()
        with zipfile.ZipFile(zip_io, 'w') as zipf:
            for pdf_file in pdf_files:
                image_data = extract_images_from_pdf(pdf_file.stream, image_type, image_mode)
                for image_filename, image_io in image_data:
                    zipf.writestr(image_filename, image_io.read())

        zip_io.seek(0)
        # Save the zip file to a temporary path
        zip_filename = 'extracted_images.zip'
        with open(zip_filename, 'wb') as f:
            f.write(zip_io.read())

        return render_template('result.html', filename=zip_filename)

    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True, download_name=filename)

if __name__ == '__main__':
    app.run(debug=True)
