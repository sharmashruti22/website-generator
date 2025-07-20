import requests
from bs4 import BeautifulSoup
import json
import os
import re
import logging

# Set up logging to a file instead of printing to console
logging.basicConfig(filename="website_generator.log", level=logging.INFO, format="%(message)s")

def fetch_html(url):
    if not url.startswith("http"):
        raise ValueError("Invalid URL format. Must start with 'http' or 'https'.")
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    content_type = response.headers.get('content-type', '').lower()
    if 'html' not in content_type:
        logging.error(f"Error: URL '{url}' does not return HTML content (Content-Type: {content_type})")
        raise ValueError("Expected HTML content")
    return response.text

def read_json(file_path):
    if not os.path.exists(file_path):
        logging.error(f"❌ Error: File {file_path} does not exist.")
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if not content.strip():
            logging.error(f"❌ Error: File {file_path} is empty.")
            return None
        return json.loads(content)

def read_config():
    config_path = "config.json"
    if not os.path.exists(config_path):
        logging.error(f"❌ Error: Config file {config_path} does not exist. Falling back to user input.")
        return None
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if not content.strip():
            logging.error(f"❌ Error: Config file {config_path} is empty. Falling back to user input.")
            return None
        return json.loads(content)

def ask_user_sections(options):
    print("\n📌 Available Sections:")  # Keep this print for user interaction
    for i, key in enumerate(options, 1):
        print(f"{i}. {key}")
    try:
        selected = input("\n✅ Enter section numbers (comma separated): ").strip()
        if not selected:
            logging.warning("No sections selected.")
            return []
        selected_indices = [int(i.strip()) for i in selected.split(",") if i.strip().isdigit()]
        selected_sections = [list(options.keys())[i - 1] for i in selected_indices if 1 <= i <= len(options)]
        logging.info(f"Selected sections: {selected_sections}")
        return selected_sections
    except EOFError:
        logging.warning("⚠️ Input interrupted. Skipping section selection.")
        return []

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
        logging.info(f"Footer links created: {links_html}")
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
    else:
        nav_container.clear()

    for key in selected_keys:
        a_tag = soup.new_tag("a", href=f"{key.lower().replace(' ', '_')}.html")
        a_tag.string = key.title()
        a_tag['style'] = "margin-right: 15px; font-weight: bold; color: purple; text-decoration: none;"
        nav_container.append(a_tag)

    return soup

def find_logo(soup):
    indicators = ["logo", "brand", "site-logo", "nav-logo", "header-logo", "googlelogo"]
    for img in soup.find_all("img"):
        combined_attrs = " ".join([
            img.get("src", "").lower(),
            img.get("alt", "").lower(),
            img.get("id", "").lower(),
            " ".join(img.get("class", [])).lower()
        ])
        if any(ind in combined_attrs for ind in indicators):
            return img
    return soup.find("img")

def replace_logo(soup, logo_filename):
    if not logo_filename:
        return
    try:
        new_logo = soup.new_tag("img", src=f"images/{logo_filename}")
        new_logo['style'] = "max-height: 80px; display: block; margin: 20px auto;"
        existing_logo = soup.find("img")
        if existing_logo and existing_logo != new_logo:
            existing_logo.replace_with(new_logo)
            logging.info("✅ Existing logo replaced.")
            return
        heading = soup.find(["h1", "h2", "h3"])
        if heading:
            heading.insert_before(new_logo)
            logging.info("✅ Logo inserted before heading.")
            return
        body_tag = soup.find("body")
        if body_tag:
            body_tag.insert(0, new_logo)
            logging.info("✅ Logo inserted at top of body.")
        else:
            new_body = soup.new_tag("body")
            new_body.insert(0, new_logo)
            soup.append(new_body)
            logging.info("✅ Created body and inserted logo at top.")
    except Exception as e:
        logging.error(f"❌ Unexpected error during logo insertion: {e}")

def insert_banner(soup, image_folder):
    print("\n📂 Available images:")  # Keep this print for user interaction
    images = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))]
    for i, img in enumerate(images):
        print(f"{i + 1}. {img}")

    def choose_image(label):
        try:
            choice = input(f"🖼️ Enter image file name for {label} (or press Enter to skip): ").strip()
            return choice if choice in images else None
        except EOFError:
            logging.warning(f"⚠️ Skipping {label} selection.")
            return None

    banner = choose_image("Homepage Banner")
    logo = choose_image("Logo")

    if not soup.body:
        logging.warning("No <body> tag found in HTML. Creating one.")
        soup.append(soup.new_tag("body"))

    if banner:
        banner_path = os.path.join("images", banner).replace("\\", "/")
        full_path = os.path.join(image_folder, banner)
        if os.path.exists(full_path):
            tag = soup.new_tag("img", src=banner_path, alt="Homepage Banner")
            tag['style'] = "display: block; width: 100%; margin: 10px auto;"
            soup.body.insert(0, tag)
            logging.info(f"✅ Banner inserted: {banner_path}")
        else:
            logging.error(f"❌ Banner image not found at: {full_path}")
    if logo:
        replace_logo(soup, logo)

def write_static_pages(selected_keys, replacements, output_folder="sections"):
    os.makedirs(output_folder, exist_ok=True)
    for key in selected_keys:
        filename = key.replace(" ", "_").lower() + ".html"
        full_path = os.path.join(output_folder, filename)
        if key in replacements:
            content = replacements[key]["content"] if isinstance(replacements[key], dict) and "content" in replacements[key] else replacements[key]
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
    <p><a href="../modified_website.html">← Back to Home</a></p>
</body>
</html>
"""
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(html_content.strip())
            logging.info(f"✅ Created: {full_path}")
        else:
            logging.error(f"❌ No content found for section: {key}")

def replace_all_links_with_construction(soup, construction_page="construction.html"):
    for a_tag in soup.find_all("a", href=True):
        a_tag['href'] = construction_page
        if 'target' in a_tag.attrs:
            del a_tag['target']
    logging.info(f"🔗 All links now point to '{construction_page}'")
    return soup

def redirect_form_submissions(soup, submit_page="submit.html"):
    for form in soup.find_all("form"):
        form['action'] = submit_page
        logging.info(f"📝 Form action changed to '{submit_page}'")

    for btn in soup.find_all(["button", "input"]):
        btn_type = btn.get("type", "").lower()
        if btn_type == "submit":
            if btn.name == "input":
                btn['formaction'] = submit_page
            elif btn.name == "button":
                btn['onclick'] = f"location.href='{submit_page}'; return false;"
            logging.info(f"🔘 Submit button redirected to '{submit_page}'")
    return soup

def main():
    try:
        url = input("🔗 Enter website URL or local HTML file path: ").strip()
        if not url:
            print("⚠️ No URL provided. Exiting.")
            return

        config = read_config()
        if config:
            json_path = config.get("json_path", "")
            image_folder = config.get("image_folder", "images")
        else:
            json_path = input("📄 Enter JSON file path (About/Contact): ").strip()
            image_folder = input("🗂️ Enter image folder path (press Enter for default 'images/'): ").strip()
            if not image_folder:
                image_folder = "images"

        if not json_path or not os.path.isfile(json_path):
            logging.error("❌ Invalid JSON file.")
            return

        if not os.path.isdir(image_folder):
            logging.error("❌ Invalid image folder.")
            return

        html = fetch_html(url) if url.startswith("http") else open(url, 'r', encoding='utf-8').read()
        soup = BeautifulSoup(html, "html.parser")
        replacements = read_json(json_path)
        if not replacements:
            logging.error("❌ Failed to read JSON.")
            return

        selected_keys = ask_user_sections(replacements)

        soup = replace_top_nav_with_json_links(soup, selected_keys)
        insert_banner(soup, image_folder)
        soup = replace_all_links_with_construction(soup)
        soup = redirect_form_submissions(soup)

        updated_html = insert_links_manually(str(soup), selected_keys)
        soup = BeautifulSoup(updated_html, "html.parser")
        with open("modified_website.html", "w", encoding="utf-8") as f:
            f.write(str(soup))
        logging.info("\n✅ Website saved as `modified_website.html`")

        write_static_pages(selected_keys, replacements)

    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()