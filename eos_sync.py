#!/usr/bin/env python3
"""
Google Drive Sync for Steensma EOS Platform
Syncs EOS Google Sheets (exported as CSVs) to ~/eosplatform/datasheets/

Required CSV files in Google Drive folder 'eos':
- rocks.csv
- scorecard.csv
- issues.csv
- todos.csv
- vto.csv
- accountability.csv

Usage:
    ./eos_sync.py
"""
import os
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================
GDRIVE_REMOTE = "gdrive:"  # rclone remote name
GDRIVE_FOLDER = "eos"  # Folder in Google Drive to watch
LOCAL_DIR = "/home/ubuntu/eosplatform/datasheets"
STATE_FILE = "/home/ubuntu/eosplatform/.eos_sync_state.json"
CHECK_INTERVAL = 60  # Check every 60 seconds
LOG_FILE = "/home/ubuntu/eosplatform/eos_sync.log"

# Expected files
EXPECTED_FILES = [
    'rocks.csv',
    'scorecard.csv',
    'issues.csv',
    'todos.csv',
    'vto.csv',
    'accountability.csv'
]

# ============================================================================
# Logging
# ============================================================================
def log(message, also_print=True):
    """Log a message to file and optionally print it"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    
    if also_print:
        print(log_msg)
    
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_msg + '\n')
    except:
        pass

# ============================================================================
# State Management
# ============================================================================
def load_state():
    """Load the last sync state from file"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_state(state):
    """Save the sync state to file"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"Error saving state: {e}")

# ============================================================================
# Google Drive Operations
# ============================================================================
def verify_rclone():
    """Verify rclone is installed and configured"""
    try:
        result = subprocess.run(['which', 'rclone'], capture_output=True, text=True)
        if result.returncode != 0:
            log("✗ rclone not found. Install with: sudo apt install rclone")
            return False
        
        # Check if remote is configured
        result = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True)
        if GDRIVE_REMOTE not in result.stdout:
            log(f"✗ rclone remote '{GDRIVE_REMOTE}' not configured")
            log("  Run: rclone config")
            return False
        
        return True
    except Exception as e:
        log(f"✗ Error verifying rclone: {e}")
        return False

def get_gdrive_files():
    """Get list of files in Google Drive folder with their modified times"""
    try:
        cmd = ['rclone', 'lsjson', f'{GDRIVE_REMOTE}{GDRIVE_FOLDER}']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            log(f"✗ Error listing Google Drive files: {result.stderr}")
            return {}
        
        files = json.loads(result.stdout)
        file_info = {}
        
        for file in files:
            name = file['Name']
            # Only track CSV files
            if name.endswith('.csv'):
                file_info[name] = {
                    'size': file['Size'],
                    'modified': file['ModTime']
                }
        
        return file_info
    except subprocess.TimeoutExpired:
        log("✗ Timeout listing Google Drive files")
        return {}
    except Exception as e:
        log(f"✗ Error getting Google Drive files: {e}")
        return {}

def sync_file(filename):
    """Sync a single file from Google Drive to local directory"""
    try:
        source = f'{GDRIVE_REMOTE}{GDRIVE_FOLDER}/{filename}'
        dest = LOCAL_DIR
        
        cmd = ['rclone', 'copy', source, dest, '-v']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            log(f"✓ Synced: {filename}")
            return True
        else:
            log(f"✗ Failed to sync {filename}: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        log(f"✗ Timeout syncing {filename}")
        return False
    except Exception as e:
        log(f"✗ Error syncing {filename}: {e}")
        return False

def check_for_updates():
    """Check for new or updated files and sync them"""
    current_state = load_state()
    gdrive_files = get_gdrive_files()
    
    if not gdrive_files:
        log("No files found in Google Drive (or error occurred)")
        return
    
    updates_found = False
    
    for filename, info in gdrive_files.items():
        # Check if file is new or modified
        if filename not in current_state:
            log(f"New file detected: {filename}")
            if sync_file(filename):
                current_state[filename] = info
                updates_found = True
        elif info['modified'] != current_state[filename]['modified']:
            log(f"File updated: {filename}")
            if sync_file(filename):
                current_state[filename] = info
                updates_found = True
    
    if updates_found:
        save_state(current_state)
        log("✓ Sync complete")
    
    # Check for missing expected files
    missing = [f for f in EXPECTED_FILES if f not in gdrive_files]
    if missing:
        log(f"⚠ Missing expected files: {', '.join(missing)}")

def verify_setup():
    """Verify the setup is correct"""
    print("Verifying setup...")
    print()
    
    # Check rclone
    if not verify_rclone():
        return False
    print("✓ rclone installed and configured")
    
    # Check local directory
    if not os.path.exists(LOCAL_DIR):
        try:
            os.makedirs(LOCAL_DIR, exist_ok=True)
            print(f"✓ Created local directory: {LOCAL_DIR}")
        except Exception as e:
            print(f"✗ Cannot create local directory: {e}")
            return False
    else:
        print(f"✓ Local directory exists: {LOCAL_DIR}")
    
    # Check Google Drive folder accessibility
    try:
        cmd = ['rclone', 'lsd', f'{GDRIVE_REMOTE}{GDRIVE_FOLDER}']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✓ Google Drive folder accessible: {GDRIVE_FOLDER}")
        else:
            print(f"✗ Cannot access Google Drive folder: {GDRIVE_FOLDER}")
            print(f"  Create it with: rclone mkdir {GDRIVE_REMOTE}{GDRIVE_FOLDER}")
            return False
    except Exception as e:
        print(f"✗ Error checking Google Drive folder: {e}")
        return False
    
    return True

def main():
    """Main sync loop"""
    print("=" * 70)
    print("Steensma EOS Platform - Google Drive Sync")
    print("=" * 70)
    print(f"Google Drive: {GDRIVE_REMOTE}{GDRIVE_FOLDER}")
    print(f"Local Directory: {LOCAL_DIR}")
    print(f"Check Interval: {CHECK_INTERVAL} seconds")
    print()
    
    if not verify_setup():
        print("\n✗ Setup verification failed. Please fix the issues above.")
        return 1
    
    print()
    print("📊 Expected files:")
    for filename in EXPECTED_FILES:
        print(f"  - {filename}")
    print()
    print("💡 Workflow:")
    print("  1. Edit your EOS Google Sheets (Rocks, Scorecard, Issues, etc.)")
    print("  2. File → Download → CSV (.csv)")
    print("  3. Upload CSV to Google Drive 'eos' folder")
    print("  4. This script detects and syncs it automatically")
    print("  5. eos.coresteensma.com updates with new data")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    log("EOS Sync started")
    
    try:
        while True:
            check_for_updates()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n\nStopping sync...")
        log("EOS Sync stopped")
        return 0

if __name__ == '__main__':
    exit(main())
