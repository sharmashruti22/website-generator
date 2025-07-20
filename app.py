from flask import Flask, request, render_template, send_file, flash, redirect, url_for
import os
import json
import uuid
import logging
from model import process_website

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.abspath('uploads')
app.config['GENERATED_FOLDER'] = os.path.abspath('generated')
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)

# Path to JSON file with sections
JSON_PATH = "about.json"  # Adjust this path as needed

def read_json(file_path):
    logging.debug(f"Reading JSON file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                logging.error(f"JSON file at {file_path} is empty")
                return None
            return json.loads(content)
    except Exception as e:
        logging.error(f"Failed to read JSON file: {str(e)}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    # Load sections from JSON
    sections_data = read_json(JSON_PATH)
    if not sections_data:
        flash(f'Failed to read JSON file at {JSON_PATH}.')
        return render_template('index.html', sections=[])

    sections = list(sections_data.keys())
    logging.debug(f"Available sections: {sections}")

    if request.method == 'POST':
        # Validate URL
        url = request.form.get('url')
        if not url:
            flash('Please provide a valid URL.')
            logging.error("URL is missing or empty")
            return render_template('index.html', sections=sections)

        # Add https:// if protocol is missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            logging.debug(f"Added https:// to URL: {url}")

        # Validate selected sections
        selected_sections = request.form.getlist('sections')
        if not selected_sections:
            flash('Please select at least one section.')
            logging.error("No sections selected")
            return render_template('index.html', sections=sections)

        # Validate logo upload
        logo_file = request.files.get("logo")
        if not logo_file or not logo_file.filename:
            flash('Please upload a logo file.')
            logging.error("No logo file uploaded")
            return render_template('index.html', sections=sections)

        # Validate file extension
        if not logo_file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
            flash('Logo must be an image file (PNG, JPG, JPEG, GIF, SVG).')
            logging.error(f"Invalid logo file type: {logo_file.filename}")
            return render_template('index.html', sections=sections)

        # Save the logo file
        logo_filename = f"logo_{uuid.uuid4()}{os.path.splitext(logo_file.filename)[1]}"
        logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_filename)
        try:
            logo_file.save(logo_path)
            if not (os.path.exists(logo_path) and os.path.getsize(logo_path) > 0):
                logging.error(f"Failed to save logo or file is empty: {logo_path}")
                flash('Failed to save logo file or file is empty.')
                return render_template('index.html', sections=sections)
            logging.debug(f"Uploaded logo: {logo_path}, size: {os.path.getsize(logo_path)} bytes")
        except Exception as e:
            logging.error(f"Error saving logo file: {str(e)}")
            flash('Error saving logo file.')
            return render_template('index.html', sections=sections)

        # Process website
        try:
            logging.debug(f"Processing website with URL: {url}, Logo: {logo_filename}, Sections: {selected_sections}")
            output_zip = process_website(
                url,
                JSON_PATH,
                app.config['UPLOAD_FOLDER'],
                [logo_filename],
                selected_sections,
                app.config['GENERATED_FOLDER']
            )

            zip_path = os.path.join(app.config['GENERATED_FOLDER'], output_zip)
            if not os.path.exists(zip_path):
                raise ValueError("Website generation failed: Output zip file not created")

            logging.debug(f"Generated zip file: {zip_path}")
            return render_template('result.html', zip_file=output_zip)

        except Exception as e:
            logging.error(f"Error processing website: {str(e)}", exc_info=True)
            flash(f'Error processing website: {str(e)}')
            return render_template('index.html', sections=sections)

    return render_template('index.html', sections=sections)

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['GENERATED_FOLDER'], filename)
    if os.path.exists(file_path):
        logging.debug(f"Sending file: {file_path}")
        return send_file(file_path, as_attachment=True)
    logging.error(f"File not found: {file_path}")
    flash('File not found.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)