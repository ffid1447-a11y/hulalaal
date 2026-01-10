from flask import Flask, request, jsonify
import requests
import threading
import time
import os

app = Flask(__name__)

# CONFIGURATION - Use environment variables for security
OFFICIAL_API_HOST = "https://westeros.famapp.in"
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "eyJlbmMiOiJBMjU2Q0JDLUhTNTEyIiwiZXBrIjp7Imt0eSI6Ik9LUCIsImNydiI6Ilg0NDgiLCJ4IjoiMEZZTUJ3M3ZGMGc5M2IyR2h5U3Uza3cyVk9aTzB3QmhqV01kdlE2eXN6X3Q3RFJURWloYmQ1eVVxRnYxTnhhVmNVdlMwdzB2eUdvIn0sImFsZyI6IkVDREgtRVMifQ..0Z5mFl44icnJBVN9f_EWOg.dld4MibLbyxwYWGljR-gT0Yyc4EMIY8bd92pNhydkHf2xYcimmKVGSz6WEVe3cU2tLMLxQV6yf_3Tbv1W5WElJ8cWKJh_Fs45-Ny2B6oulONX0Sm47dogwthqgpi1RbP6WRJ-P9soBetdU4lPgluM0-QX-A0Vwfcv5GpNcxSB8S3TQMElmwrR1qDkEV6mfxa7Eq707KyMyUrcTvu4ZjG8Y_U02g_TvVbPVcrA1TGdKp-goEA8gttrsGz_xZaFAJ8VBzHwBWJJ5H2FIVUDZrZ9HSzF8cJLz9LHJbVx53sSyj5ONJflZvEUjRrtWVxJ_0Rlin1-236qHlTqygI1HckBLuIQ-T52Anzma5kAu0ySuNfx14uxAq_QICiGPgT6lbf.Me_ZBBzs5Ry9HBMkJjyk5xzSXcn-huf5XgECvGfN6iY")
DEVICE_ID = os.environ.get("DEVICE_ID", "adb84e9925c4f17a")
USER_AGENT = os.environ.get("USER_AGENT", "2312DRAABI | Android 15 | Dalvik/2.1.0 | gold | 2EF4F924D8CD3764269BD3548C4E7BF4FA070E7B | 3.11.5 (Build 525) | U78TN5J23U")

# Initialize session
SESSION = None
FAM_ID_MAPPING = {}

def init_session():
    """Initialize session with headers"""
    global SESSION
    if SESSION is None:
        SESSION = requests.Session()
        SESSION.headers.update({
            "host": "westeros.famapp.in",
            "user-agent": USER_AGENT,
            "x-device-details": USER_AGENT,
            "x-app-version": "525",
            "x-platform": "1",
            "device-id": DEVICE_ID,
            "authorization": f"Token {AUTH_TOKEN}",
            "accept-encoding": "gzip",
            "content-type": "application/json; charset=UTF-8"
        })

def fetch_blocked_list():
    """Fetch blocked list"""
    init_session()
    try:
        response = SESSION.get(
            f"{OFFICIAL_API_HOST}/user/blocked_list/",
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def find_user_in_list(fam_id, blocked_data):
    """Find user in blocked list"""
    if not blocked_data or 'results' not in blocked_data:
        return None
    
    fam_id_clean = fam_id.replace('@fam', '').lower()
    
    # Check cache first
    if fam_id in FAM_ID_MAPPING:
        phone = FAM_ID_MAPPING[fam_id]
        for user in blocked_data['results']:
            if user and user.get('contact'):
                contact = user['contact']
                if contact.get('phone_number') == phone:
                    return user
    
    # Search in list
    for user in blocked_data['results']:
        if user and user.get('contact'):
            contact = user['contact']
            name = contact.get('name', '').lower()
            
            if fam_id_clean in name:
                phone = contact.get('phone_number', '')
                FAM_ID_MAPPING[fam_id] = phone
                return user
            
            if 'send' in fam_id_clean:
                name_part = fam_id_clean.replace('send', '').replace('2', '').replace('3', '').strip()
                if name_part and name_part in name:
                    phone = contact.get('phone_number', '')
                    FAM_ID_MAPPING[fam_id] = phone
                    return user
    
    return None

def instant_unblock(fam_id):
    """INSTANT unblock in background thread"""
    def unblock_task():
        try:
            # Small delay to ensure API got the block
            time.sleep(0.5)
            init_session()
            
            unblock_payload = {"block": False, "vpa": fam_id}
            response = SESSION.post(
                f"{OFFICIAL_API_HOST}/user/vpa/block/",
                json=unblock_payload,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"[AUTO-UNBLOCK] ✓ Instantly unblocked: {fam_id}")
            else:
                print(f"[AUTO-UNBLOCK] ✗ Failed: {fam_id} - {response.status_code}")
        except Exception as e:
            print(f"[AUTO-UNBLOCK ERROR] {fam_id}: {e}")
    
    # Start unblock in background
    thread = threading.Thread(target=unblock_task, daemon=True)
    thread.start()

@app.route('/')
def home():
    return jsonify({
        "message": "Fam ID to Number API",
        "endpoint": "/get-number?id=username@fam",
        "status": "active",
        "version": "1.0"
    })

@app.route('/get-number', methods=['GET'])
def get_number():
    """MAIN ENDPOINT - Instant auto-unblock"""
    fam_id = request.args.get('id')
    
    if not fam_id:
        return jsonify({"error": "Missing 'id' parameter"}), 400
    
    if not fam_id.endswith('@fam'):
        return jsonify({"error": "Invalid Fam ID format"}), 400
    
    # Step 1: Check if already in blocked list
    blocked_data = fetch_blocked_list()
    
    if blocked_data and 'results' in blocked_data:
        user = find_user_in_list(fam_id, blocked_data)
        
        if user:
            contact = user['contact']
            phone = contact.get('phone_number')
            FAM_ID_MAPPING[fam_id] = phone
            
            # INSTANT AUTO-UNBLOCK (background)
            instant_unblock(fam_id)
            
            return jsonify({
                "status": True,
                "fam_id": fam_id,
                "name": contact.get('name'),
                "phone": phone,
                "type": user.get('type'),
                "source": "local"
            })
    
    # Step 2: Block to get info
    block_payload = {"block": True, "vpa": fam_id}
    
    try:
        init_session()
        block_response = SESSION.post(
            f"{OFFICIAL_API_HOST}/user/vpa/block/",
            json=block_payload,
            timeout=10
        )
        
        if block_response.status_code != 200:
            return jsonify({
                "error": f"Block failed: {block_response.status_code}"
            }), 500
        
        # Step 3: Get updated list
        updated_data = fetch_blocked_list()
        
        if not updated_data or 'results' not in updated_data:
            return jsonify({"error": "Failed to fetch updated list"}), 500
        
        # Step 4: Find newest user
        if updated_data['results']:
            newest_user = updated_data['results'][0]
            
            if newest_user and newest_user.get('contact'):
                contact = newest_user['contact']
                phone = contact.get('phone_number')
                FAM_ID_MAPPING[fam_id] = phone
                
                # INSTANT AUTO-UNBLOCK (background)
                instant_unblock(fam_id)
                
                return jsonify({
                    "status": True,
                    "fam_id": fam_id,
                    "name": contact.get('name'),
                    "phone": phone,
                    "type": newest_user.get('type'),
                    "source": "original"
                })
        
        return jsonify({
            "status": True,
            "fam_id": fam_id,
            "error": "No contact info found"
        })
        
    except Exception as e:
        return jsonify({"error": f"Request failed: {str(e)}"}), 500

@app.route('/blocked', methods=['GET'])
def blocked_list():
    """View blocked list"""
    data = fetch_blocked_list()
    
    if not data:
        return jsonify({"error": "Failed to fetch"}), 500
    
    users = []
    if 'results' in data:
        for user in data['results']:
            if user and user.get('contact'):
                contact = user['contact']
                users.append({
                    "name": contact.get('name'),
                    "phone": contact.get('phone_number'),
                    "type": user.get('type')
                })
    
    return jsonify({
        "count": len(users),
        "users": users
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time()
    })

# Vercel requires this
if __name__ == '__main__':
    app.run(debug=False)
else:
    # For Vercel serverless
    application = app