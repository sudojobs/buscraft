import rsa
import json
import base64
from pathlib import Path

def generate_keys():
    print("Generating RSA-2048 keypair...")
    (pubkey, privkey) = rsa.newkeys(2048)
    
    pub_path = Path("public.pem")
    priv_path = Path("private.pem")
    
    with open(pub_path, "wb") as f:
        f.write(pubkey.save_pkcs1())
    with open(priv_path, "wb") as f:
        f.write(privkey.save_pkcs1())
        
    print(f"Saved {pub_path} and {priv_path}")
    print("WARNING: Keep private.pem offline and secure!")

def sign_license(license_file: str, privkey_path: str):
    with open(privkey_path, "rb") as f:
        privkey = rsa.PrivateKey.load_pkcs1(f.read())
        
    with open(license_file, "r") as f:
        data = json.load(f)
        
    # Remove existing signature if present
    if "signature" in data:
        del data["signature"]
        
    # Serialize canonically
    payload = json.dumps(data, sort_keys=True).encode("utf-8")
    
    # Sign
    signature = rsa.sign(payload, privkey, "SHA-256")
    b64_sig = base64.b64encode(signature).decode("utf-8")
    
    data["signature"] = b64_sig
    
    out_file = Path(license_file).with_suffix(".signed.json")
    with open(out_file, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        
    print(f"Signed license saved to {out_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="BusCraft License Tool")
    parser.add_argument("action", choices=["keygen", "sign"])
    parser.add_argument("--license", help="Path to JSON license file to sign")
    parser.add_argument("--key", default="private.pem", help="Path to private key")
    
    args = parser.parse_args()
    
    if args.action == "keygen":
        generate_keys()
    elif args.action == "sign":
        if not args.license:
            print("Error: --license is required for signing")
            exit(1)
        sign_license(args.license, args.key)
