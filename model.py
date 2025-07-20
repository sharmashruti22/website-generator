import requests
from bs4 import BeautifulSoup
import json
import os
import uuid
import shutil
import zipfile
from PIL import Image

def fetch_html(url):
    if not url.startswith("http"):
        raise ValueError("Invalid URL format. Must start with 'http' or 'https'.")
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    content_type = response.headers.get('content-type', '').lower()
    if 'html' not in content_type:
        print(f"Error: URL '{url}' does not return HTML content (Content-Type: {content_type})")
        raise ValueError("Expected HTML content")
    return response.text

def read_json(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist.")
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if not content.strip():
            print(f"Error: File {file_path} is empty.")
            return None
        return json.loads(content)

def read_config():
    config_path = "config.json"
    if not os.path.exists(config_path):
        print(f"Error: Config file {config_path} does not exist. Falling back to user input.")
        return None
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if not content.strip():
            print(f"Error: Config file {config_path} is empty. Falling back to user input.")
            return None
        return json.loads(content)

def ask_user_sections(options):
    print("\nAvailable Sections:")
    for i, key in enumerate(options, 1):
        print(f"{i}. {key}")
    try:
        selected = input("\nEnter section numbers (comma separated): ").strip()
        if not selected:
            print("No sections selected.")
            return []
        selected_indices = [int(i.strip()) for i in selected.split(",") if i.strip().isdigit()]
        selected_sections = [list(options.keys())[i - 1] for i in selected_indices if 1 <= i <= len(options)]
        print(f"Selected sections: {selected_sections}")
        return selected_sections
    except EOFError:
        print("Input interrupted. Skipping section selection.")
        return []

def optimize_image(image_path, output_path, max_size=(800, 800)):
    try:
        with Image.open(image_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(output_path, optimize=True, quality=85)
        return True
    except Exception as e:
        print(f"Image optimization failed: {e}")
        return False

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
        a_tag = soup.new_tag("a", href="construction.html")
        a_tag.string = key
        a_tag['style'] = "margin-right: 10px; font-weight: bold; color: purple;"
        nav_container.append(a_tag)
    return soup

def find_logo(soup):
    indicators = ["logo", "brand", "site-logo", "nav-logo", "header-logo", "googlelogo", "main"]
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
                return img

    for svg in soup.find_all("svg"):
        combined_attrs = " ".join([
            svg.get("id", "").lower(),
            " ".join(svg.get("class", [])).lower(),
            str(svg.get("aria-label", "")).lower(),
            str(svg.get("role", "")).lower()
        ])
        if any(ind in combined_attrs for ind in indicators):
            return svg

    for img in soup.find_all("img"):
        combined_attrs = " ".join([
            img.get("src", "").lower(),
            img.get("alt", "").lower(),
            img.get("id", "").lower(),
            " ".join(img.get("class", [])).lower()
        ])
        if any(ind in combined_attrs for ind in indicators):
            return img

    return soup.find("svg") or soup.find("img")

def replace_logo(soup, logo_filename, image_folder):
    if not logo_filename:
        return
    try:
        logo_path = os.path.join(image_folder, logo_filename)
        optimized_logo = f"optimized_{logo_filename}"
        optimized_path = os.path.join(image_folder, optimized_logo)
        logo_src = f"images/{logo_filename}"
        if optimize_image(logo_path, optimized_path):
            logo_src = f"images/{optimized_logo}"
            print(f"Using optimized logo: {logo_src}")
        else:
            print("Logo optimization failed, using original.")

        new_logo = soup.new_tag("img", src=logo_src)
        new_logo['style'] = "max-height: 80px; display: block; margin: 20px auto;"
        existing_logo = find_logo(soup)

        if existing_logo:
            tag_type = "SVG" if existing_logo.name == "svg" else "Image"
            if tag_type == "Image" and existing_logo.get("src", "").lower().endswith(".svg"):
                tag_type = "SVG-referenced Image"
            existing_logo.replace_with(new_logo)
            print(f"{tag_type} logo replaced with new logo.")
            return

        heading = soup.find(["h1", "h2", "h3"])
        if heading:
            heading.insert_before(new_logo)
            print("New logo inserted before heading.")
            return

        body_tag = soup.find("body")
        if body_tag:
            body_tag.insert(0, new_logo)
            print("New logo inserted at top of body.")
        else:
            new_body = soup.new_tag("body")
            new_body.insert(0, new_logo)
            soup.append(new_body)
            print("Created body and inserted new logo at top.")
    except Exception as e:
        print(f"Unexpected error during logo insertion: {e}")

def write_static_pages(selected_keys, replacements, output_folder="sections"):
    os.makedirs(output_folder, exist_ok=True)
    for key in selected_keys:
        filename = key.replace(" ", "_").lower() + ".html"
        full_path = os.path.join(output_folder, filename)
        if key in replacements:
            content = replacements[key]
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{key.title()}</title>
</head>
<body>
    <h1>{key.title()}</h1>
    <p>{content}</p>
    <p><a href="../construction.html">← Back to Home</a></p>
</body>
</html>
"""
            # Parse the section page HTML to modify links
            soup = BeautifulSoup(html_content, "html.parser")
            soup = replace_all_links_with_construction(soup)
            soup = redirect_form_submissions(soup)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(str(soup).strip())
            print(f"Created: {full_path}")
        else:
            print(f"No content found for section: {key}")

def replace_all_links_with_construction(soup, construction_page="construction.html"):
    for a_tag in soup.find_all("a", href=True):
        a_tag['href'] = construction_page
        if 'target' in a_tag.attrs:
            del a_tag['target']
    print(f"All links now point to '{construction_page}'")
    return soup

def redirect_form_submissions(soup, submit_page="submit.html"):
    for form in soup.find_all("form"):
        form['action'] = submit_page
        print(f"Form action changed to '{submit_page}'")

    for btn in soup.find_all(["button", "input"]):
        btn_type = btn.get("type", "").lower()
        if btn_type == "submit":
            if btn.name == "input":
                btn['formaction'] = submit_page
            elif btn.name == "button":
                btn['onclick'] = f"location.href='{submit_page}'; return false;"
            print(f"Submit button redirected to '{submit_page}'")
    return soup

def create_construction_and_submit_pages(output_dir):
    # Create construction.html
    construction_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Under Construction</title>
</head>
<body>
    <h1>Under Construction</h1>
    <p>This page is currently under construction. Please check back later!</p>
</body>
</html>
"""
    with open(os.path.join(output_dir, "construction.html"), "w", encoding="utf-8") as f:
        f.write(construction_content.strip())
    print("Created: construction.html")

    # Create submit.html
    submit_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Form Submitted</title>
</head>
<body>
    <h1>Form Submitted</h1>
    <p>Your form has been submitted successfully!</p>
    <p><a href="construction.html">Back to Construction Page</a></p>
</body>
</html>
"""
    with open(os.path.join(output_dir, "submit.html"), "w", encoding="utf-8") as f:
        f.write(submit_content.strip())
    print("Created: submit.html")

def process_website(url, json_path, image_folder, image_filenames, selected_sections, output_folder):
    try:
        html = fetch_html(url) if url.startswith("http") else open(url, 'r', encoding='utf-8').read()
        soup = BeautifulSoup(html, "html.parser")
        print("HTML fetched successfully")
    except Exception as e:
        print(f"Failed to fetch HTML: {str(e)}")
        raise

    try:
        output_dir = os.path.join(output_folder, str(uuid.uuid4()))
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "sections"), exist_ok=True)
        print(f"Output directory created: {output_dir}")
    except Exception as e:
        print(f"Failed to create output directory: {str(e)}")
        raise

    try:
        replacements = read_json(json_path)
        if not replacements:
            raise ValueError("Failed to read JSON.")
        print("JSON read successfully")
    except Exception as e:
        print(f"Failed to read JSON: {str(e)}")
        raise

    selected_keys = [key for key in selected_sections if key in replacements]
    if not selected_keys:
        print("No valid sections selected")
        raise ValueError("No valid sections selected.")
    print(f"Selected JSON keys: {selected_keys}")

    logo_filename = image_filenames[0] if image_filenames else None
    print(f"Logo: {logo_filename}")

    try:
        soup = replace_top_nav_with_json_links(soup, selected_keys)
        replace_logo(soup, logo_filename, image_folder)
        # Apply the link and form redirection
        soup = replace_all_links_with_construction(soup)
        soup = redirect_form_submissions(soup)
        print("HTML processed successfully")
    except Exception as e:
        print(f"Failed to process HTML: {str(e)}")
        raise

    try:
        if logo_filename:
            src = os.path.join(image_folder, logo_filename)
            optimized_logo = f"optimized_{logo_filename}"
            optimized_path = os.path.join(image_folder, optimized_logo)
            dest = os.path.join(output_dir, "images", optimized_logo if os.path.exists(optimized_path) else logo_filename)
            shutil.copy(src if not os.path.exists(optimized_path) else optimized_path, dest)
            print(f"Copied logo: {dest}")
    except Exception as e:
        print(f"Failed to copy logo: {str(e)}")
        raise

    try:
        with open(os.path.join(output_dir, "modified_website.html"), "w", encoding="utf-8") as f:
            f.write(str(soup))
        print("Main HTML written")
    except Exception as e:
        print(f"Failed to write main HTML: {str(e)}")
        raise

    try:
        write_static_pages(selected_keys, replacements, os.path.join(output_dir, "sections"))
    except Exception as e:
        print(f"Failed to write static pages: {str(e)}")
        raise

    try:
        create_construction_and_submit_pages(output_dir)
    except Exception as e:
        print(f"Failed to create construction and submit pages: {str(e)}")
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
        print(f"Zip file created: {zip_path}")
    except Exception as e:
        print(f"Failed to create zip file: {str(e)}")
        raise

    try:
        shutil.rmtree(output_dir)
        print("Temporary output directory removed")
    except Exception as e:
        print(f"Failed to clean up temporary directory: {str(e)}")
        raise

    return zip_filename

def main():
    try:
        url = input("Enter website URL or local HTML file path: ").strip()
        if not url:
            print("No URL provided. Exiting.")
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
            print("Invalid JSON file.")
            return

        if not os.path.isdir(image_folder):
            print("Invalid image folder.")
            return

        print("\nAvailable images:")
        images = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))]
        for i, img in enumerate(images, 1):
            print(f"{i}. {img}")
        try:
            logo_choice = input("\nEnter image file name for Logo (or press Enter to skip): ").strip()
            logo_filename = logo_choice if logo_choice in images else None
        except EOFError:
            print("Skipping logo selection.")
            logo_filename = None

        replacements = read_json(json_path)
        if not replacements:
            print("Failed to read JSON.")
            return

        selected_keys = ask_user_sections(replacements)

        output_folder = "generated"
        os.makedirs(output_folder, exist_ok=True)

        zip_filename = process_website(
            url,
            json_path,
            image_folder,
            [logo_filename] if logo_filename else [],
            selected_keys,
            output_folder
        )

        print(f"\nWebsite processed and saved as a zip file: {os.path.join(output_folder, zip_filename)}")

    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()