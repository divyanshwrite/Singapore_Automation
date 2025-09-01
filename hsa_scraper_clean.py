import os
import asyncio
from urllib.parse import urljoin
from datetime import datetime
import httpx
from selectolax.parser import HTMLParser
import magic
import psycopg2
from psycopg2.extras import Json
import json
import pdfplumber
import docx2txt

BASE_URL = "https://www.hsa.gov.sg"
TIMEOUT = 30
DATA_DIR = "data/hsa"
USER_AGENT = "Mozilla/5.0"
VALID_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx'}
MIME_TO_EXT = {
    'application/pdf': '.pdf',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.ms-excel': '.xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx'
}

DB_CONFIG = {
    'host': 'localhost',
    'database': 'quriousri',
    'user': os.getenv('PGUSER', 'fda_user'),
    'password': os.getenv('PGPASSWORD', ''),
    'port': 5432,
}

def get_db_connection():
    return psycopg2.connect(
        host=DB_CONFIG['host'],
        database=DB_CONFIG['database'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        port=DB_CONFIG['port']
    )

def clear_singapore_entries():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                print("Removing all entries from Singapore...")
                cur.execute("""
                    DELETE FROM source.medical_guidelines
                    WHERE country = 'Singapore'
                """)
                deleted_count = cur.rowcount
                conn.commit()
                print(f"Successfully removed {deleted_count} entries from Singapore")
    except Exception as e:
        print(f"Error clearing Singapore entries: {e}")
        raise

def store_in_db(title, section, file_url, file_path, product_type):
    try:
        # Extract text from the document
        extracted_text = extract_text_from_file(file_path)
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check if entry exists and get current all_text if it does
                cur.execute("""
                    SELECT all_text FROM source.medical_guidelines 
                    WHERE title = %s
                """, (title,))
                result = cur.fetchone()
                
                now = datetime.now()
                if result:
                    # Update existing entry
                    current_text = result[0] or ""
                    if extracted_text:  # Only append if we got new text
                        all_text = current_text + "\n\n" + extracted_text if current_text else extracted_text
                    else:
                        all_text = current_text
                        
                    cur.execute("""
                        UPDATE source.medical_guidelines SET
                            summary = %s,
                            link_guidance = %s,
                            link_file = %s,
                            products = %s,
                            json_data = %s,
                            all_text = %s,
                            updated_at = %s
                        WHERE title = %s
                    """, (
                        f"Guidance document from HSA {section}",
                        BASE_URL + file_url if not file_url.startswith('http') else file_url,
                        file_path,
                        product_type,
                        Json({'section': section}),
                        all_text,
                        now,
                        title
                    ))
                else:
                    # Insert new entry
                    cur.execute("""
                        INSERT INTO source.medical_guidelines (
                            title, summary, link_guidance, link_file, products,
                            country, agency, json_data, all_text, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            'Singapore', 'HSA',
                            %s, %s, %s, %s
                        )
                    """, (
                        title,
                        f"Guidance document from HSA {section}",
                        BASE_URL + file_url if not file_url.startswith('http') else file_url,
                        file_path,
                        product_type,
                        Json({'section': section}),
                        extracted_text,
                        now,
                        now
                    ))
    except Exception as e:
        print(f"Error storing in DB: {e}")

URLS_TO_SCRAPE = [
    ('therapeutic-products/guidance-documents', 'Guidance documents for therapeutic products'),
    ('medical-devices/guidance-documents', 'Guidance documents for medical devices')
]

def extract_text_from_file(file_path):
    """Extract text from PDF or DOCX files."""
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text.strip()
        elif ext in ['.doc', '.docx']:
            return docx2txt.process(file_path).strip()
        else:
            return ""
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return ""

def clean_filename(filename):
    """Clean filename to be filesystem friendly."""
    import re
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    return ' '.join(filename.split()).strip()

async def download_file(client, url, folder_path, filename, section=None, product_type=None):
    resp = await client.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    
    os.makedirs(folder_path, exist_ok=True)
    
    # Try to get extension from URL first
    url_ext = os.path.splitext(url.split('?')[0])[1].lower()
    clean_name = clean_filename(filename)
    name_ext = os.path.splitext(clean_name)[1].lower()
    
    # Use URL extension if valid
    if url_ext in VALID_EXTENSIONS:
        clean_name = f"{os.path.splitext(clean_name)[0]}{url_ext}"
    # If no valid extension, try content type
    elif not name_ext or name_ext not in VALID_EXTENSIONS:
        content_type = resp.headers.get('content-type', '').lower()
        # Try magic bytes detection
        mime = magic.Magic(mime=True)
        mime_type = mime.from_buffer(resp.content)
        ext = MIME_TO_EXT.get(mime_type)
        if ext:
            clean_name = f"{os.path.splitext(clean_name)[0]}{ext}"
        elif not os.path.splitext(clean_name)[1]:
            clean_name = f"{clean_name}.pdf"  # Default to PDF if unknown
    
    file_path = os.path.join(folder_path, clean_name)
    with open(file_path, "wb") as f:
        f.write(resp.content)
    print(f"Downloaded: {clean_name}")
    
    # Store in database
    if section:
        store_in_db(
            title=filename,
            section=section,
            file_url=url,
            file_path=file_path,
            product_type=product_type
        )
    
    return 1

async def scrape_url(client, url_path, base_folder_name):
    processed_urls = set()
    base_folder = os.path.join(DATA_DIR, base_folder_name)
    os.makedirs(base_folder, exist_ok=True)
    
    # Get main page content
    resp = await client.get(f"{BASE_URL}/{url_path}", timeout=TIMEOUT)
    tree = HTMLParser(resp.text)
    
    # Dynamically get main sections from the page
    allowed_sections = set()
    for section in tree.css('button.collapse-header'):
        title = section.text().strip()
        if title:
            allowed_sections.add(title)
    
    if not allowed_sections:
        # Fallback to finding headers in the document
        for section in tree.css('h1, h2, h3, h4, h5'):
            if section.parent.css_first('a[href]'):  # Only take headers that have links
                title = section.text().strip()
                if title:
                    allowed_sections.add(title)
    
    print(f"\nProcessing {base_folder_name}")
    print(f"Found sections: {', '.join(sorted(allowed_sections))}")
    return tree, allowed_sections, base_folder, processed_urls

async def main():
    total_files = 0
    all_processed_urls = set()
    
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for url_path, folder_name in URLS_TO_SCRAPE:
            tree, allowed_sections, base_folder, processed_urls = await scrape_url(client, url_path, folder_name)
            print(f"\nStarting to download files for {folder_name}...")
            
            # Find all document links for this URL
            for link in tree.css('a[href]'):
                href = link.attributes.get('href', '').strip()
                text = link.text().strip()
                
                if not href or not text:
                    continue
                    
                # Make absolute URL
                if not href.startswith('http'):
                    href = urljoin(BASE_URL, href)
                
                # Skip if already processed
                if href in processed_urls:
                    continue
                    
                try:
                    # Determine appropriate folder
                    parent = link
                    folder_name = "Other Documents"
                    while parent:
                        if parent.css_first('h1, h2, h3, h4, h5'):
                            section_title = parent.css_first('h1, h2, h3, h4, h5').text().strip()
                            if section_title in allowed_sections:
                                folder_name = section_title
                                break
                        parent = parent.parent
                    
                    # Only proceed if we're in an allowed section
                    if folder_name not in allowed_sections:
                        continue
                    
                    # Determine product type based on the folder name
                    product_type = "Medical Device" if "device" in base_folder.lower() else "Drugs"
                    
                    # Download if it looks like a document
                    if any(ext in href.lower() for ext in VALID_EXTENSIONS) or 'download' in href.lower():
                        section_folder = os.path.join(base_folder, clean_filename(folder_name))
                        await download_file(client, href, section_folder, text, folder_name, product_type)
                        processed_urls.add(href)
                        total_files += 1
                    # Otherwise try to scrape the page for documents
                    else:
                        try:
                            page = await client.get(href, timeout=TIMEOUT)
                            page_tree = HTMLParser(page.text)
                            for doc_link in page_tree.css('a[href]'):
                                doc_href = doc_link.attributes.get('href', '').strip()
                                doc_text = doc_link.text().strip()
                                
                                if not doc_href or not doc_text:
                                    continue
                                    
                                if not doc_href.startswith('http'):
                                    doc_href = urljoin(BASE_URL, doc_href)
                                    
                                if doc_href not in processed_urls and any(ext in doc_href.lower() for ext in VALID_EXTENSIONS):
                                    section_folder = os.path.join(base_folder, clean_filename(folder_name))
                                    await download_file(client, doc_href, section_folder, doc_text, folder_name, product_type)
                                    processed_urls.add(doc_href)
                                    total_files += 1
                        except Exception as e:
                            print(f"Error processing page {href}: {e}")
                except Exception as e:
                    print(f"Error processing {text}: {e}")
            
            all_processed_urls.update(processed_urls)  # Combine processed URLs after each URL is done
            href = link.attributes.get('href', '').strip()
            text = link.text().strip()
            
            if not href or not text:
                continue
                
            # Make absolute URL
            if not href.startswith('http'):
                href = urljoin(BASE_URL, href)
            
            # Skip if already processed
            if href in processed_urls:
                continue
                
    print(f"\nDownload complete. Total files downloaded: {total_files}")
        
    print(f"\nDownload complete. Total files downloaded: {total_files}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--clear-only':
        # Only clear the entries
        clear_singapore_entries()
    else:
        # First clear existing Singapore entries
        clear_singapore_entries()
        # Then run the scraper
        asyncio.run(main())
