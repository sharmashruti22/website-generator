from flask import Flask, request, render_template, send_file, flash, redirect, url_for
import os
import shutil
import zipfile
import uuid
import logging
import json
from model import process_website

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['GENERATED_FOLDER'] = 'generated'
app.config['SECRET_KEY'] = 'your-secret-key'  # Replace with secure key

# Read config.json
CONFIG_PATH = "/Users/shrutisharma/Desktop/websitegenerator/config.json"
try:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
    JSON_PATH = config['json_path']
    logging.debug(f"Loaded config: JSON_PATH={JSON_PATH}")
except Exception as e:
    logging.error(f"Failed to read config.json: {str(e)}")
    JSON_PATH = "/Users/shrutisharma/Desktop/websitegenerator/about.json"

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)

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

        # Validate selected sections
        selected_sections = request.form.getlist('sections')
        if not selected_sections:
            flash('Please select at least one section.')
            logging.error("No sections selected")
            return render_template('index.html', sections=sections)

        # Handle optional banner and logo uploads
        uploaded_images = []

        banner_file = request.files.get("banner")
        if banner_file and banner_file.filename:
            # Validate file extension
            if not banner_file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                flash('Banner must be an image file (PNG, JPG, JPEG, GIF, SVG).')
                logging.error(f"Invalid banner file type: {banner_file.filename}")
                return render_template('index.html', sections=sections)
            banner_path = os.path.join(app.config['UPLOAD_FOLDER'], banner_file.filename)
            banner_file.save(banner_path)
            if os.path.exists(banner_path):
                uploaded_images.append(banner_file.filename)
                logging.debug(f"Uploaded banner: {banner_path}")
            else:
                logging.error(f"Failed to save banner: {banner_path}")
                flash('Failed to save banner file.')
                return render_template('index.html', sections=sections)

        logo_file = request.files.get("logo")
        if logo_file and logo_file.filename:
            # Validate file extension
            if not logo_file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                flash('Logo must be an image file (PNG, JPG, JPEG, GIF, SVG).')
                logging.error(f"Invalid logo file type: {logo_file.filename}")
                return render_template('index.html', sections=sections)
            logo_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_file.filename)
            logo_file.save(logo_path)
            if os.path.exists(logo_path):
                uploaded_images.append(logo_file.filename)
                logging.debug(f"Uploaded logo: {logo_path}")
            else:
                logging.error(f"Failed to save logo: {logo_path}")
                flash('Failed to save logo file.')
                return render_template('index.html', sections=sections)
        else:
            logging.warning("No logo file uploaded. Logo replacement will be skipped.")
            flash('No logo file uploaded. The original website logo will remain unchanged.')

        # Ensure at least one image is uploaded
        if not uploaded_images:
            flash('Please upload at least a banner image.')
            logging.error("No images uploaded")
            return render_template('index.html', sections=sections)

        # Ensure image_filenames has at least two elements (banner and logo)
        while len(uploaded_images) < 2:
            uploaded_images.append(None)  # Pad with None if logo is missing

        # Process website
        try:
            logging.debug(f"Processing website with URL: {url}, Uploaded Images: {uploaded_images}, Sections: {selected_sections}")
            output_zip = process_website(
                url,
                JSON_PATH,
                app.config['UPLOAD_FOLDER'],
                uploaded_images,
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

    # GET request
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
