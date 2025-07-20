import requests
from bs4 import BeautifulSoup
import json
import os
from openai import OpenAI
import re

# OpenRouter client setup
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

def fetch_html(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text

def read_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def ask_llm_to_edit(html_body, replacements):
    prompt = f"""
You are a professional HTML editor.

Here is the HTML body of a webpage:

{html_body}

Below is a JSON object containing updated section texts:
{json.dumps(replacements)}

Please replace or add these sections ("about us", "contact us") in the HTML above where appropriate. If the section is missing, insert it at a logical location like at the bottom of the body. Keep the structure clean and do not remove other page content.
Return only the updated <body> HTML content.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    content = response.choices[0].message.content.strip()
    cleaned = re.sub(r"```(?:html)?", "", content).strip("` \n")
    return cleaned

def replace_main_logo(soup, new_logo_filename):
    if not new_logo_filename:
        return

    new_logo_path = os.path.join("assets", new_logo_filename).replace("\\", "/")

    # Try to find an existing logo <img> tag by common attributes
    possible_logos = soup.find_all("img")
    logo_tag = None
    for img in possible_logos:
        alt_text = img.get("alt", "").lower()
        src_text = img.get("src", "").lower()
        if "logo" in alt_text or "logo" in src_text or "branding" in src_text or "google" in alt_text:
            logo_tag = img
            break

    # If logo found, replace its src
    if logo_tag:
        logo_tag['src'] = new_logo_path
        logo_tag['alt'] = "Custom Logo"
        if not logo_tag.get("width") and not logo_tag.get("style"):
            logo_tag['style'] = "width: 120px; height: auto;"
        print(f"Replaced existing logo with: {new_logo_path}")
    else:
        # If no existing logo found, insert at top as fallback
        fallback_tag = soup.new_tag("img", src=new_logo_path, alt="Custom Logo")
        fallback_tag['style'] = "width: 120px; height: auto;"
        soup.body.insert(0, fallback_tag)
        print(f"No logo detected. Inserted logo at top instead: {new_logo_path}")

def insert_banner(soup, image_folder):
    print("\nAvailable images in folder:")
    images = [f for f in os.listdir(image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))]
    for i, img in enumerate(images):
        print(f"{i+1}. {img}")

    def choose_image(label):
        choice = input(f"\nEnter image file name for {label} (or leave empty to skip): ").strip()
        if choice and choice in images:
            return choice
        return None

    banner = choose_image("Homepage Banner")
    logo = choose_image("Logo")

    if banner:
        banner_path = os.path.join("assets", banner).replace("\\", "/")
        banner_tag = soup.new_tag("img", src=banner_path, alt="Homepage Banner")
        banner_tag['style'] = "display: block; width: 100%; margin: 10px auto;"
        soup.body.insert(0, banner_tag)

    if logo:
        replace_main_logo(soup, logo)

def main():
    url = input("Enter website URL: ").strip()
    json_path = input("Enter JSON file path with section text (e.g., about/contact): ").strip()
    image_folder = input("Enter folder path for images: ").strip()

    if not os.path.isfile(json_path):
        print("JSON file path is invalid.")
        return
    if not os.path.isdir(image_folder):
        print("Image folder path is invalid.")
        return

    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    replacements = read_json(json_path)
    body_content = str(soup.body)
    updated_body_html = ask_llm_to_edit(body_content, replacements)

    updated_soup = BeautifulSoup(updated_body_html, "html.parser")
    insert_banner(updated_soup, image_folder)

    soup.body.clear()
    for element in updated_soup.contents:
        soup.body.append(element)

    with open("modified_website.html", "w", encoding="utf-8") as f:
        f.write(str(soup))

    print("\n Website saved as modified_website.html")

if __name__ == "__main__":
    main()
