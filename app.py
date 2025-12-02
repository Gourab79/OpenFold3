import os
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# -------------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------------
# NEVER hardcode API keys in production code. 
# Export it in your terminal: export NVIDIA_API_KEY="nvapi-..."
API_KEY = ""
NVIDIA_URL = "https://health.api.nvidia.com/v1/biology/openfold/openfold3/predict"

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/predict", methods=["POST"])
def predict():
    if not API_KEY:
        return jsonify({"error": "Server missing API Key. Please set NVIDIA_API_KEY env var."}), 500

    # 1. Get dynamic payload from Frontend
    user_payload = request.json
    
    headers = {
        "content-type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "NVCF-POLL-SECONDS": "300",
    }

    print("⚡ Sending request to NVIDIA NIM...")
    
    try:
        # Increased timeout for large structures
        r = requests.post(NVIDIA_URL, headers=headers, json=user_payload, timeout=600)

        if not r.ok:
            print(f"❌ Error {r.status_code}: {r.text}")
            return jsonify({"error": r.text, "status_code": r.status_code}), r.status_code

        # 2. Parse Logic
        result = r.json()
        outputs = result.get("outputs", [])
        
        if not outputs:
            return jsonify({"error": "NVIDIA returned no outputs."}), 500

        # Depending on API version, data might be in 'data' or 'structures_with_scores'
        pdb_text = None
        
        # Strategy A: Direct data field
        if "data" in outputs[0]:
            pdb_text = outputs[0]["data"]
            
        # Strategy B: OpenFold3 specific structure
        elif "structures_with_scores" in outputs[0]:
            sws = outputs[0]["structures_with_scores"]
            for s in sws:
                if s.get("format") == "pdb":
                    pdb_text = s.get("structure")
                    break
        
        if not pdb_text:
             return jsonify({"error": "Could not extract PDB string from response.", "debug": result}), 500

        return jsonify({"pdb": pdb_text})

    except Exception as e:
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

if __name__ == "__main__":
    print(f"🚀 OpenFold3 Server running on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)