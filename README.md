# Website-Generator

## Overview
The **Website Generator** is a Flask-based web application that allows users to **input any website URL** and instantly create a **similar-looking website**.

It provides powerful **customization options** where users can change the **logo, banners, and navigation bar**. Once ready, the app generates the **final cloned website** in a **ZIP file**, which can be downloaded directly.

This tool is perfect for quickly prototyping or creating custom-branded versions of existing websites.

---

## Features

- **Website Cloning**
  Enter any URL, and the system scrapes and processes the site’s content.

- **Logo & Banner Customization**
  Replace the default branding with your own logo and banners before generating the site.

- **Navigation Bar Editing**
  Modify or replace the website’s navigation menu.

- **Automatic Link & Form Handling**
  Updates internal links to point to placeholders like `construction.html` and replaces form actions for security.

- **ZIP File Generation**
  After customization, download the full modified website as a ZIP archive.

- **Minimal User Interface**
  A clean HTML/CSS interface with simple user interactions.

---

## Tech Stack

- **Flask** → Backend web framework
- **BeautifulSoup4 & Requests** → For scraping and parsing the input website
- **Jinja2 Templates** → For rendering dynamic HTML pages
- **HTML, CSS, JS** → For frontend pages
- **Gunicorn** → For production deployment
- **Python 3.x** → Core programming language

---

## Requirements

- Python 3.x
- Flask
- BeautifulSoup4
- Requests
- Gunicorn (for deployment)

You can install all dependencies with:

```bash
pip install -r requirements.txt
```

---

## Setup

1️ **Clone the Repository**
```bash
git clone https://github.com/your-username/project1.git
cd project1
```

2️ **Create a Virtual Environment**
```bash
python3 -m venv venv
source venv/bin/activate   # For Mac/Linux
venv\Scripts\activate      # For Windows
```

3️ **Install Dependencies**
```bash
pip install -r requirements.txt
```

4️ **Run the Flask App**
```bash
python app.py
```

Your app will run locally on:
 `http://127.0.0.1:5000`

---

## File Processing

- The app fetches the **HTML structure** of the given URL.
- Parses and **replaces images, banners, and logos** with user-provided ones.
- Updates all **internal links and forms** for safety.
- Generates a **new customized version** of the website.
- Packages everything into a **ZIP file** for download.

---

## Output Management

- Generated sections (like *About Us*, *Contact Us*, etc.) are saved separately.
- Final output is stored in the `generated/` folder.
- A ZIP archive (e.g., `website_xxxxxx.zip`) is created for easy download.

---

## Deployment

The app can be deployed to **Render** or **Heroku**.

- **Procfile**:
  ```
  web: gunicorn app:app
  ```
- **requirements.txt** includes Flask, BeautifulSoup4, Requests, Gunicorn

After deployment, you’ll get a public link like:
```
https://yourwebsitegenerator.onrender.com
```

---

## Example Workflow

1️ Enter `https://example.com` as input URL  
2️ Upload a new **logo** & **banner**  
3️ Modify navigation bar text  
4️ Click **Generate**  
5️ Download the **ZIP file** with the customized site

---

## Customization Options

- Upload a **custom logo**
- Replace **banners/images**
- Edit **menu/navigation links**
- Change **form actions** to custom pages

---

## Conclusion

The **Website Generator** makes it easy to create **custom-branded versions of any site** without manual coding. It’s perfect for designers, developers, and businesses wanting quick website prototypes.

---

## Screenshots

1 Main Page
<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/714d416b-e435-4bfc-adeb-a675257b09b8" />


2 Custom Logo & Banner Upload 
<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/bd9479a0-74cd-4e08-8ff2-1b73892b312c" />

3 Selections made as per the user
<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/0a7b0374-2cb1-4abd-95ef-ab77602e1c3a" />

4 Downloadable ZIP File 
<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/edcde409-300d-487d-b6e2-f7547fefd974" />
 
<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/6d8c3b27-1d4b-47c8-9ce4-995daf035e21" />

5 Generated Website Preview  
<img width="2560" height="1600" alt="image" src="https://github.com/user-attachments/assets/0a499bcf-8fdf-417d-b830-090175450301" />



