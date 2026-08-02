import json
import os
import re
from bs4 import BeautifulSoup

def sanitize_filename(name):
    # Convert to lowercase and replace spaces/special chars with underscores
    clean = re.sub(r'[^a-zA-Z0-9]+', '_', name.lower())
    return clean.strip('_')

def main():
    # Use the local html file that we already successfully fetched
    html_path = '/Users/srbalakrishnan/.gemini/antigravity-ide/brain/5a21aa8a-a5ce-41a4-91bd-b7830194f334/.system_generated/steps/271/content.md'
    
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract options
    select = soup.find('select', id='keyword')
    if not select:
        print("Could not find keyword dropdown.")
        return
        
    options = select.find_all('option')
    
    # Extract keyword divs
    keyword_data = soup.find(id='keyword_data')
    if not keyword_data:
        print("Could not find keyword_data container.")
        return
        
    divs = keyword_data.find_all('div', class_='card', recursive=False)
    
    # Filter out empty or placeholder options like '-Select-'
    valid_options = []
    for opt in options:
        if opt.get('value') and opt.get('value').strip():
            valid_options.append(opt.text.strip())
            
    print(f"Found {len(valid_options)} valid keyword names.")
    print(f"Found {len(divs)} documentation divs.")
    
    if len(valid_options) != len(divs):
        print("Warning: The number of keyword names does not match the number of descriptions!")
        
    out_dir = '../keywords'
    os.makedirs(out_dir, exist_ok=True)
    
    count = 0
    for i, name in enumerate(valid_options):
        if i >= len(divs):
            break
            
        desc_div = divs[i]
        
        # 1. Extract raw text for legacy support
        raw_text = desc_div.get_text(separator='\n').strip()
        raw_text = re.sub(r'\n+', '\n', raw_text)
        
        # 2. Extract structured Markdown instructions
        markdown_instructions = ""
        image_urls = []
        card_body = desc_div.find('div', class_='card-body')
        
        if card_body:
            for child in card_body.children:
                if child.name == 'p':
                    text = child.get_text(separator=' ').strip()
                    if text:
                        markdown_instructions += f"{text}\n\n"
                    # Check for images inside this p tag
                    for img in child.find_all('img'):
                        src = img.get('src')
                        if src:
                            markdown_instructions += f"![Example]({src})\n\n"
                            image_urls.append(src)
                elif child.name == 'img':
                    src = child.get('src')
                    if src:
                        markdown_instructions += f"![Example]({src})\n\n"
                        image_urls.append(src)
                elif child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    markdown_instructions += f"### {child.get_text(separator=' ').strip()}\n\n"
                elif child.name == 'ul' or child.name == 'ol':
                    for li in child.find_all('li'):
                        markdown_instructions += f"- {li.get_text(separator=' ').strip()}\n"
                    markdown_instructions += "\n"
        
        markdown_instructions = markdown_instructions.strip()
        
        # 3. Short description
        paragraphs = desc_div.find_all('p')
        short_desc = ""
        for p in paragraphs:
            text = p.get_text().strip()
            if text and name.lower() not in text.lower() and len(text) > 10:
                short_desc = text
                break
        if not short_desc and paragraphs:
            short_desc = paragraphs[0].get_text().strip()
            
        data = {
            "name": name,
            "description": short_desc,
            "how_to_use_markdown": markdown_instructions,
            "example_image_urls": image_urls,
            "parameters": [
                {
                    "name": "Extract parameters manually or update script parser",
                    "type": "Any",
                    "description": "Details pending"
                }
            ],
            "return_type": "Any",
            "raw_scraped_text": raw_text
        }
        
        safe_name = sanitize_filename(name)
        file_path = os.path.join(out_dir, f"{safe_name}.json")
        
        with open(file_path, 'w', encoding='utf-8') as out_f:
            json.dump(data, out_f, indent=4)
            
        count += 1
        
    print(f"Successfully scraped and saved {count} keywords to {out_dir}/")

if __name__ == "__main__":
    main()
