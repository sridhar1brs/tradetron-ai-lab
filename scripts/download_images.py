import json
import os
import re
import urllib.request
from pathlib import Path

def download_image(url, save_path):
    try:
        # Add a basic User-Agent to avoid simple blocks
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(save_path, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def main():
    keywords_dir = Path('../keywords')
    images_dir = keywords_dir / 'images'
    images_dir.mkdir(parents=True, exist_ok=True)
    
    json_files = list(keywords_dir.glob('*.json'))
    print(f"Found {len(json_files)} JSON files to process.")
    
    download_count = 0
    updated_files_count = 0
    
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error reading JSON from {json_file.name}")
                continue
                
        image_urls = data.get('example_image_urls', [])
        markdown_text = data.get('how_to_use_markdown', '')
        
        if not image_urls:
            continue
            
        new_urls = []
        modified = False
        
        for url in image_urls:
            if not url.startswith('http'):
                # Already local or invalid
                new_urls.append(url)
                continue
                
            # Generate a safe local filename based on the URL's tail
            filename = url.split('/')[-1]
            # Ensure it ends with an image extension
            if not re.search(r'\.(png|jpg|jpeg|gif)$', filename.lower()):
                filename += '.png'
                
            local_save_path = images_dir / filename
            local_reference = f"./images/{filename}"
            
            # Download the image if it doesn't already exist
            if not local_save_path.exists():
                success = download_image(url, local_save_path)
                if success:
                    download_count += 1
                else:
                    new_urls.append(url)
                    continue
            
            # If download succeeded or file already exists, update references
            new_urls.append(local_reference)
            markdown_text = markdown_text.replace(url, local_reference)
            modified = True
            
        if modified:
            data['example_image_urls'] = new_urls
            data['how_to_use_markdown'] = markdown_text
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            updated_files_count += 1
            
    print(f"Finished processing. Downloaded {download_count} images.")
    print(f"Updated {updated_files_count} JSON files to use local image paths.")

if __name__ == "__main__":
    main()
