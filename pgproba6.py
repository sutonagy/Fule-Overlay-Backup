#!/usr/bin/env python3
import requests

response = requests.get("https://api.github.com/repos/sutonagy/Fule-Overlay-Backup/releases/latest")
#print(response.json()["name"])
print(response.json())
