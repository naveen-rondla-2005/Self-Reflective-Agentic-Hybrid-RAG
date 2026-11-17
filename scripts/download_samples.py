import os
import requests

DATA_DIR = "./data/transit_docs"
os.makedirs(DATA_DIR, exist_ok=True)

# Official public documents from Kochi Metro Rail Limited (KMRL)
KMRL_DOCS = {
    "kmrl_annual_report_2023_24.pdf": "https://kochimetro.org/wp-content/uploads/2024/11/Annual-Report-2023-24.pdf",
    "kmrl_annual_report_2022_23.pdf": "https://kochimetro.org/wp-content/uploads/2023/12/Annual-Report-2022-23.pdf"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print("Fetching KMRL operational documents for proxy corpus...")

for filename, url in KMRL_DOCS.items():
    dest = os.path.join(DATA_DIR, filename)
    if not os.path.exists(dest):
        print(f"Downloading {filename}...")
        try:
            res = requests.get(url, headers=headers, timeout=90)
            if res.status_code == 200:
                with open(dest, "wb") as f:
                    f.write(res.content)
                print(f" Saved {filename} ({len(res.content) // 1024} KB)")
            else:
                print(f"Failed to fetch {filename} (HTTP {res.status_code})")
        except Exception as e:
            print(f"Error downloading {filename}: {e}")
    else:
        print(f"Already present: {filename}")

print("Corpus setup complete!")