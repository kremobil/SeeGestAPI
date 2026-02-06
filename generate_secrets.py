import os
import secrets
import re
import shutil

if not os.path.exists(".env.example"):
    print(".env.example file not found.")
    exit()

with open(".env.example", "r") as f:
    env_data = f.read()

def update_val(key, value, text):
    return re.sub(rf"{key}=.*", f"{key}={value}", text)

credentials = {
    "GOOGLE_CLIENT_ID_WEB": input("Google Client ID for Website: ").strip(),
    "GOOGLE_CLIENT_ID_ANDROID": input("Google Client ID for Android: ").strip(),
    "GOOGLE_CLIENT_ID_IOS": input("Google Client ID for iOS: ").strip(),
    "GOOGLE_MAPS_API_KEY": input("Google Maps API Key: ").strip(),
    "JWT_SECRET_KEY": secrets.token_hex(32),
    "DATABASE_URL": "sqlite:///seegest.db",
    "MAIL_USERNAME": input("Gmail Address: ").strip(),
    "MAIL_PASSWORD": input("Gmail App Password: ").strip()
}

for key, val in credentials.items():
    env_data = update_val(key, val, env_data)

with open(".env", "w") as f:
    f.write(env_data)

shutil.copy(".flaskenv.example", ".flaskenv")

print("\n.flaskenv and .env were generated successfully.")
