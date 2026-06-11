import os
import sys

# Ensure local directory is in path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

from drive_backup import get_gdrive_credentials

def main():
    print("------------------------------------------------------------")
    print("Google Drive Authorization Helper")
    print("------------------------------------------------------------")
    print("This script will open a browser to authenticate your Google Drive.")
    print("If your token is expired or invalid, it will refresh it.")
    print("------------------------------------------------------------\n")
    
    # Force removal of invalid token.json to trigger fresh login if refresh fails
    if os.path.exists("token.json"):
        print("Existing token.json found. Attempting to load/refresh it...")
    else:
        print("No token.json found. Starting fresh login...")
        
    try:
        creds = get_gdrive_credentials()
        if creds and creds.valid:
            print("\nSUCCESS: A valid token has been acquired and saved to 'token.json'!")
            print(f"Token Expiry: {creds.expiry}")
            print("\nTo prevent this token from expiring every 7 days, please ensure")
            print("your Google Cloud Project OAuth Consent Screen is set to 'Production' mode.")
        else:
            print("\nERROR: Failed to acquire valid credentials.")
    except Exception as e:
        print(f"\nError occurred during authorization: {e}")
        print("\nTip: If you get an 'invalid_grant' error, delete the old 'token.json' file and run this script again.")

if __name__ == "__main__":
    main()
