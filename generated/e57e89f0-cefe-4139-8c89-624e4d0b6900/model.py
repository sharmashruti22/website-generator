import requests
from bs4 import BeautifulSoup
import json
import os
import re
from PIL import Image
import io
import base64
from openai import OpenAI
import uuid
import logging
import shutil
import zipfile

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# API configuration
BASE_URL = "https://openrouter.ai/api/v1"
API_KEY = "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"

# Initialize OpenAI client for OpenRouter
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def fetch_html(url):
    if not url.startswith("http"):
        raise ValueError("Invalid URL format. Must start with 'http' or 'https'.")
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    content_type = response.headers.get('content-type', '').lower()
    if 'html' not in content_type:
        logging.error(f"URL '{url}' does not return HTML content (Content-Type: {content_type})")
        raise ValueError("Expected HTML content")
    return response.text

def read_json(file_path):
    if not os.path.exists(file_path):
        logging.error(f"File {file_path} does not exist.")
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if not content.strip():
            logging.error(f"File {file_path} is empty.")
            return None
        return json.loads(content)

def read_config():
    config_path = "config.json"
    if not os.path.exists(config_path):
        logging.warning(f"Config file {config_path} does not exist. Falling back to user input.")
        return None
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if not content.strip():
            logging.warning(f"Config file {config_path} is empty. Falling back to user input.")
            return None
        return json.loads(content)

def ask_user_sections(options):
    print("\nAvailable Sections:")
    for i, key in enumerate(options, 1):
        print(f"{i}. {key}")
    try:
        selected = input("\nEnter section numbers (comma separated): ").strip()
        if not selected:
            logging.info("No sections selected.")
            return []
        selected_indices = [int(i.strip()) for i in selected.split(",") if i.strip().isdigit()]
        selected_sections = [list(options.keys())[i - 1] for i in selected_indices if 1 <= i <= len(options)]
        logging.info(f"Selected sections: {selected_sections}")
        return selected_sections
    except EOFError:
        logging.warning("Input interrupted. Skipping section selection.")
        return []

def enhance_content_with_ai(content, section_title):
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct:free",
            messages=[
                {"role": "system", "content": "You are a content enhancement assistant. Improve the provided text by making it more engaging and professional while maintaining its original meaning."},
                {"role": "user", "content": f"Enhance this content for the section '{section_title}': {content}"}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"AI content enhancement failed: {e}. Using original content.")
        return content

def optimize_image(image_path, output_path, max_size=(800, 800)):
    try:
        with Image.open(image_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(output_path, optimize=True, quality=85)
        logging.debug(f"Image optimized: {output_path}")
        return True
    except Exception as e:
        logging.error(f"Image optimization failed for {image_path}: {e}")
        return False

def insert_links_manually(html_body, selected_keys):
    soup = BeautifulSoup(html_body, "html.parser")
    if not soup.body:
        logging.warning("No <body> tag found in HTML. Creating one.")
        soup.append(soup.new_tag("body"))

    footer = soup.new_tag("footer")
    footer['style'] = "text-align: center; padding: 20px; width: 100%; background-color: #f8f9fa;"

    if selected_keys:
        links_html = " | ".join(
            [f'<a href="sections/{key.replace(" ", "_").lower()}.html">{key.title()}</a>' for key in selected_keys]
        )
        footer.append(BeautifulSoup(links_html, "html.parser"))
        logging.debug(f"Footer links created: {links_html}")
    else:
        footer.string = "No sections selected."
        logging.info("No sections to link in footer.")

    soup.body.insert(0, footer)
    return str(soup)

def replace_top_nav_with_json_links(soup, selected_keys):
    nav_container = None

    for tag in soup.find_all(['div', 'nav', 'header', 'center'], recursive=True):
        if any(keyword in tag.get_text(strip=True).lower() for keyword in ['search', 'images', 'maps', 'news', 'youtube', 'gmail', 'drive']):
            nav_container = tag
            break

    if not nav_container:
        nav_container = soup.new_tag("div")
        soup.body.insert(0, nav_container)

    nav_container.clear()

    for key in selected_keys:
        a_tag = soup.new_tag("a", href=f"sections/{key.lower().replace(' ', '_')}.html")
        a_tag.string = key
        a_tag['style'] = "margin-right: 10px; font-weight: bold; color: purple;"
        nav_container.append(a_tag)

    return soup

def find_logo(soup):
    indicators = ["logo", "brand", "site-logo", "nav-logo", "header-logo", "googlelogo", "main"]

    # Check for <img> tags with SVG source
    for img in soup.find_all("img"):
        src = img.get("src", "").lower()
        if src.endswith(".svg"):
            combined_attrs = " ".join([
                src,
                img.get("alt", "").lower(),
                img.get("id", "").lower(),
                " ".join(img.get("class", [])).lower()
            ])
            if any(ind in combined_attrs for ind in indicators):
                logging.debug(f"Found logo via SVG image: {combined_attrs}")
                return img

    # Check for pure SVG logos
    for svg in soup.find_all("svg"):
        combined_attrs = " ".join([
            svg.get("id", "").lower(),
            " ".join(svg.get("class", [])).lower(),
            str(svg.get("aria-label", "")).lower(),
            str(svg.get("role", "")).lower()
        ])
        if any(ind in combined_attrs for ind in indicators):
            logging.debug(f"Found logo via SVG: {combined_attrs}")
            return svg

    # Check for regular <img> tags
    for img in soup.find_all("img"):
        combined_attrs = " ".join([
            img.get("src", "").lower(),
            img.get("alt", "").lower(),
            img.get("id", "").lower(),
            " ".join(img.get("class", [])).lower()
        ])
        if any(ind in combined_attrs for ind in indicators):
            logging.debug(f"Found logo via image: {combined_attrs}")
            return img

    # Fallback to first SVG or image
    result = soup.find("svg") or soup.find("img")
    if result:
        logging.debug(f"Using fallback: {result.name} tag")
    else:
        logging.warning("No logo found in the HTML")
    return result

def replace_logo(soup, logo_filename, image_folder):
    if not logo_filename:
        logging.warning("No logo filename provided. Skipping logo replacement.")
        return

    try:
        logo_path = os.path.join(image_folder, logo_filename)
        if not os.path.exists(logo_path):
            logging.error(f"Logo file not found at {logo_path}. Skipping logo replacement.")
            return

        optimized_logo = f"optimized_{logo_filename}"
        optimized_path = os.path.join(image_folder, optimized_logo)
        logo_src = f"static/images/{logo_filename}"
        if optimize_image(logo_path, optimized_path):
            logo_src = f"static/images/{optimized_logo}"
            logging.debug(f"Using optimized logo: {logo_src}")
        else:
            logging.warning("Logo optimization failed, using original.")

        new_logo = soup.new_tag("img", src=logo_src, alt="Custom Logo")
        new_logo['style'] = "max-height: 92px; display: block; margin: 30px auto;"
        existing_logo = find_logo(soup)

        if existing_logo:
            tag_type = "SVG" if existing_logo.name == "svg" else "Image"
            if tag_type == "Image" and existing_logo.get("src", "").lower().endswith(".svg"):
                tag_type = "SVG-referenced Image"
            
            # Preserve parent structure and styling
            parent = existing_logo.parent
            if parent and parent.name in ["div", "span", "a"]:
                parent_style = parent.get("style", "")
                parent_class = " ".join(parent.get("class", []))
                logging.debug(f"Existing logo parent: {parent.name}, style: {parent_style}, class: {parent_class}")

                wrapper = soup.new_tag(parent.name)
                if parent_style:
                    wrapper['style'] = parent_style
                if parent_class:
                    wrapper['class'] = parent_class

                wrapper.append(new_logo)
                existing_logo.parent.replace_with(wrapper)
                logging.debug(f"Replaced logo, preserving parent {parent.name} structure")
            else:
                existing_logo.replace_with(new_logo)
                logging.debug(f"{tag_type} logo replaced with new logo")
            return

        # Fallback placement if no logo found
        heading = soup.find(["h1", "h2", "h3"])
        if heading:
            heading.insert_before(new_logo)
            logging.debug("New logo inserted before heading")
            return

        body_tag = soup.find("body")
        if body_tag:
            body_tag.insert(0, new_logo)
            logging.debug("New logo inserted at top of body")
        else:
            new_body = soup.new_tag("body")
            new_body.insert(0, new_logo)
            soup.append(new_body)
            logging.debug("Created body and inserted new logo at top")
    except Exception as e:
        logging.error(f"Unexpected error during logo insertion: {e}")

def insert_banner(soup, banner_filename, image_folder):
    if not soup.body:
        logging.warning("No <body> tag found in HTML. Creating one.")
        soup.append(soup.new_tag("body"))

    if banner_filename:
        banner_path = os.path.join(image_folder, banner_filename)
        if not os.path.exists(banner_path):
            logging.error(f"Banner file not found at {banner_path}. Skipping banner insertion.")
            return

        optimized_banner = f"optimized_{banner_filename}"
        optimized_path = os.path.join(image_folder, optimized_banner)
        banner_src = f"static/images/{banner_filename}"
        if optimize_image(banner_path, optimized_path):
            banner_src = f"static/images/{optimized_banner}"
            logging.debug(f"Using optimized banner: {banner_src}")
        else:
            logging.warning("Banner optimization failed, using original.")

        tag = soup.new_tag("img", src=banner_src, alt="Homepage Banner")
        tag['style'] = "display: block; width: 100%; margin: 10px auto;"
        soup.body.insert(0, tag)
        logging.debug(f"Banner inserted: {banner_src}")

def replace_all_links_with_construction(soup, construction_page="construction.html"):
    modified_count = 0
    for a_tag in soup.find_all("a"):
        if a_tag.get("href"):
            original_href = a_tag['href']
            if original_href.startswith("javascript:"):
                a_tag['href'] = construction_page
                if a_tag.get("onclick"):
                    del a_tag['onclick']
                logging.debug(f"Modified JavaScript link from '{original_href}' to '{construction_page}'")
            else:
                a_tag['href'] = construction_page
                logging.debug(f"Modified link from '{original_href}' to '{construction_page}'")
            if 'target' in a_tag.attrs:
                del a_tag['target']
            modified_count += 1
        else:
            logging.debug(f"Skipped <a> tag with no href: {str(a_tag)[:50]}...")
    logging.info(f"Total links modified: {modified_count}")
    return soup

def redirect_form_submissions(soup, submit_page="submit.html"):
    for form in soup.find_all("form"):
        form['action'] = submit_page
        logging.debug(f"Form action changed to '{submit_page}'")

    for btn in soup.find_all(["button", "input"]):
        btn_type = btn.get("type", "").lower()
        if btn_type == "submit":
            if btn.name == "input":
                btn['formaction'] = submit_page
            elif btn.name == "button":
                btn['onclick'] = f"location.href='{submit_page}'; return false;"
            logging.debug(f"Submit button redirected to '{submit_page}'")
    return soup

def write_static_pages(selected_keys, replacements, output_folder="sections"):
    os.makedirs(output_folder, exist_ok=True)
    for key in selected_keys:
        filename = key.replace(" ", "_").lower() + ".html"
        full_path = os.path.join(output_folder, filename)
        if key in replacements:
            enhanced_content = enhance_content_with_ai(replacements[key], key)
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{key.title()}</title>
</head>
<body>
    <h1>{key.title()}</h1>
    <p>{enhanced_content}</p>
    <p><a href="../modified_website.html">← Back to Home</a></p>
</body>
</html>
"""
            soup = BeautifulSoup(html_content, "html.parser")
            soup = replace_all_links_with_construction(soup)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(str(soup).strip())
            logging.debug(f"Created: {full_path}")
        else:
            logging.warning(f"No content found for section: {key}")

    submit_path = os.path.join(output_folder, "submit.html")
    if not os.path.exists(submit_path):
        submit_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Form Submission</title>
</head>
<body>
    <h1>Form Submission</h1>
    <p>Your form has been submitted.</p>
    <p><a href="../modified_website.html">Back to Home</a></p>
</body>
</html>
"""
        submit_soup = BeautifulSoup(submit_content, "html.parser")
        submit_soup = replace_all_links_with_construction(submit_soup)
        with open(submit_path, "w", encoding="utf-8") as f:
            f.write(str(submit_soup).strip())
        logging.debug(f"Created: {submit_path}")

def process_website(url, json_path, image_folder, image_filenames, selected_sections, output_folder):
    logging.debug(f"Starting website processing for URL: {url}")
    try:
        html = fetch_html(url) if url.startswith("http") else open(url, 'r', encoding='utf-8').read()
        soup = BeautifulSoup(html, "html.parser")
        logging.debug("HTML fetched successfully")
    except Exception as e:
        logging.error(f"Failed to fetch HTML: {str(e)}")
        raise

    try:
        replacements = read_json(json_path)
        if not replacements:
            raise ValueError("Failed to read JSON.")
        logging.debug("JSON read successfully")
    except Exception as e:
        logging.error(f"Failed to read JSON: {str(e)}")
        raise

    selected_keys = [key for key in selected_sections if key in replacements]
    if not selected_keys:
        logging.error("No valid sections selected")
        raise ValueError("No valid sections selected.")
    logging.debug(f"Selected JSON keys: {selected_keys}")

    banner_filename = image_filenames[0] if len(image_filenames) > 0 else None
    logo_filename = image_filenames[1] if len(image_filenames) > 1 else None
    logging.debug(f"Banner: {banner_filename}, Logo: {logo_filename}")

    try:
        soup = replace_top_nav_with_json_links(soup, selected_keys)
        insert_banner(soup, banner_filename, image_folder)
        replace_logo(soup, logo_filename, image_folder)
        soup = replace_all_links_with_construction(soup)
        soup = redirect_form_submissions(soup)
        logging.debug("HTML processed successfully")
    except Exception as e:
        logging.error(f"Failed to process HTML: {str(e)}")
        raise

    try:
        output_dir = os.path.join(output_folder, str(uuid.uuid4()))
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "static", "images"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "sections"), exist_ok=True)
        logging.debug(f"Output directory created: {output_dir}")
    except Exception as e:
        logging.error(f"Failed to create output directory: {str(e)}")
        raise

    try:
        construction_src = "construction.html"
        construction_dest = os.path.join(output_dir, "construction.html")
        if os.path.exists(construction_src):
            with open(construction_src, 'r', encoding='utf-8') as f:
                construction_html = f.read()
            construction_soup = BeautifulSoup(construction_html, "html.parser")
            construction_soup = replace_all_links_with_construction(construction_soup)
            with open(construction_dest, 'w', encoding='utf-8') as f:
                f.write(str(construction_soup))
            logging.debug(f"Copied and modified construction.html to {construction_dest}")
        else:
            logging.warning("construction.html not found in current directory")

        submit_src = "submit.html"
        submit_dest = os.path.join(output_dir, "submit.html")
        if os.path.exists(submit_src):
            with open(submit_src, 'r', encoding='utf-8') as f:
                submit_html = f.read()
            submit_soup = BeautifulSoup(submit_html, "html.parser")
            submit_soup = replace_all_links_with_construction(submit_soup)
            with open(submit_dest, 'w', encoding='utf-8') as f:
                f.write(str(submit_soup))
            logging.debug(f"Copied and modified submit.html to {submit_dest}")
        else:
            logging.warning("submit.html not found in current directory")

        model_src = "model.py"
        model_dest = os.path.join(output_dir, "model.py")
        if os.path.exists(model_src):
            shutil.copy(model_src, model_dest)
            logging.debug(f"Copied model.py to {model_dest}")
        else:
            logging.warning("model.py not found in current directory")

        app_src = "app.py"
        app_dest = os.path.join(output_dir, "app.py")
        if os.path.exists(app_src):
            shutil.copy(app_src, app_dest)
            logging.debug(f"Copied app.py to {app_dest}")
        else:
            logging.warning("app.py not found in current directory")

        for image in image_filenames:
            src = os.path.join(image_folder, image)
            optimized_image = f"optimized_{image}"
            optimized_path = os.path.join(image_folder, optimized_image)
            dest = os.path.join(output_dir, "static", "images", optimized_image if os.path.exists(optimized_path) else image)
            shutil.copy(src if not os.path.exists(optimized_path) else optimized_path, dest)
            logging.debug(f"Copied image: {dest}")
    except Exception as e:
        logging.error(f"Failed to copy files: {str(e)}")
        raise

    try:
        with open(os.path.join(output_dir, "modified_website.html"), "w", encoding="utf-8") as f:
            f.write(str(soup))
        logging.debug("Main HTML written")
    except Exception as e:
        logging.error(f"Failed to write main HTML: {str(e)}")
        raise

    try:
        write_static_pages(selected_keys, replacements, os.path.join(output_dir, "sections"))
    except Exception as e:
        logging.error(f"Failed to write static pages: {str(e)}")
        raise

    try:
        zip_filename = f"website_{uuid.uuid4()}.zip"
        zip_path = os.path.join(output_folder, zip_filename)
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_dir)
                    zipf.write(file_path, arcname)
        logging.debug(f"Zip file created: {zip_path}")
    except Exception as e:
        logging.error(f"Failed to create zip file: {str(e)}")
        raise

    try:
        shutil.rmtree(output_dir)
        logging.debug("Temporary output directory removed")
    except Exception as e:
        logging.error(f"Failed to clean up temporary directory: {str(e)}")
        raise

    return zip_filename

def main():
    try:
        url = input("Enter website URL or local HTML file path: ").strip()
        if not url:
            logging.error("No URL provided. Exiting.")
            return

        config = read_config()
        if config:
            json_path = config.get("json_path", "")
            image_folder = config.get("image_folder", "images")
        else:
            json_path = input("Enter JSON file path (About/Contact): ").strip()
            image_folder = input("Enter image folder path (press Enter for default 'images/'): ").strip()
            if not image_folder:
                image_folder = "images"

        if not json_path or not os.path.isfile(json_path):
            logging.error("Invalid JSON file.")
            return

        if not os.path.isdir(image_folder):
            logging.error("Invalid image folder.")
            return

        # List images in the folder to simulate image_filenames
        images = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))]
        if len(images) < 2:
            logging.error("Not enough images in the folder. Need at least a banner and a logo.")
            return
        image_filenames = images[:2]  # Take first two images as banner and logo

        html = fetch_html(url) if url.startswith("http") else open(url, 'r', encoding='utf-8').read()
        soup = BeautifulSoup(html, "html.parser")
        replacements = read_json(json_path)
        if not replacements:
            logging.error("Failed to read JSON.")
            return

        selected_sections = ask_user_sections(replacements)
        output_folder = "output"  # Define output folder for process_website
        os.makedirs(output_folder, exist_ok=True)

        zip_filename = process_website(url, json_path, image_folder, image_filenames, selected_sections, output_folder)
        logging.info(f"Website processed and saved as {zip_filename}")

    except Exception as e:
        logging.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()