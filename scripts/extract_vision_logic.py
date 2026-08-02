import json
import os
from pathlib import Path
try:
    from PIL import Image
    import pytesseract
except ImportError:
    print("Missing PIL or pytesseract. Please install with: pip3 install Pillow pytesseract")
    exit(1)

def main():
    keywords_dir = Path('../keywords')
    images_dir = keywords_dir / 'images'
    
    json_files = list(keywords_dir.glob('*.json'))
    print(f"Found {len(json_files)} JSON files to process for OCR.")
    
    processed_count = 0
    updated_files_count = 0
    
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
                
        image_urls = data.get('example_image_urls', [])
        
        if not image_urls:
            continue
            
        extracted_texts = []
        for local_ref in image_urls:
            if local_ref.startswith('./images/'):
                filename = local_ref.replace('./images/', '')
                img_path = images_dir / filename
                
                if img_path.exists():
                    try:
                        # Extract text using Tesseract OCR
                        img = Image.open(img_path)
                        text = pytesseract.image_to_string(img)
                        clean_text = text.strip()
                        if clean_text:
                            extracted_texts.append(f"Image [{filename}] Text:\n{clean_text}")
                    except Exception as e:
                        print(f"Failed OCR on {filename}: {e}")
        
        if extracted_texts:
            data['visual_logic_extracted'] = "\n\n".join(extracted_texts)
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            updated_files_count += 1
            processed_count += len(extracted_texts)
            
    print(f"Finished OCR extraction. Processed {processed_count} images.")
    print(f"Updated {updated_files_count} JSON files with visual logic text.")

if __name__ == "__main__":
    main()
