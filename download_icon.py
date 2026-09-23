import urllib.request
import os

url = "https://cdn-icons-png.flaticon.com/512/3135/3135692.png" # Simple study/book icon
output_path = "icon.png"

print("Downloading icon...")
try:
    urllib.request.urlretrieve(url, output_path)
    print("Icon downloaded successfully.")
except Exception as e:
    print(f"Failed to download icon: {e}")
