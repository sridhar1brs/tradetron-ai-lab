from bs4 import BeautifulSoup

html_path = '/Users/srbalakrishnan/.gemini/antigravity-ide/brain/5a21aa8a-a5ce-41a4-91bd-b7830194f334/.system_generated/steps/271/content.md'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()
soup = BeautifulSoup(html, 'html.parser')
keyword_data = soup.find(id='keyword_data')
divs = keyword_data.find_all('div', class_='card', recursive=False)
desc_div = divs[0]

print("RAW HTML:")
print(desc_div.prettify())

print("\nCHILDREN:")
for child in desc_div.children:
    print(f"- {child.name}: {str(child)[:50]}")
