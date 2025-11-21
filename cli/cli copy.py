import click
import requests
import base64
import os
import json
import time
from dotenv import load_dotenv
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

load_dotenv()

# Default points to the v1 root. We will handle SDK path adjustments in the commands.
BASE_URL = os.getenv("RAGFLOW_BASE_URL", "https://rag-api.guardennes.ai/v1")
PUB_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArq9XTUSeYr2+N1h3Afl/z8Dse/2yD0ZGrKwx+EEEcdsBLca9Ynmx3nIB5obmLlSfmskLpBo0UACBmB5rEjBp2Q2f3AG3Hjd4B+gNCG6BDaawuDlgANIhGnaTLrIqWrrcm4EMzJOnAOI1fgzJRsOOUEfaS318Eq9OVO3apEyCCt0lOQK6PuksduOjVxtltDav+guVAA068NrPYmRNabVKRNLJpL8w4D44sfth5RvZ3q9t+6RTArpEtc5sh5ChzvqPOzKGMXW83C95TxmXqpbK6olN4RevSfVjEAgCydH6HN6OhtOQEcnrU97r9H0iZOWwbw3pVrZiUkuRD1R56Wzs2wIDAQAB
-----END PUBLIC KEY-----"""

def encrypt_password(pwd):
    pub = serialization.load_pem_public_key(PUB_KEY.encode(), default_backend())
    b64_pwd = base64.b64encode(pwd.encode()).decode()
    encrypted = pub.encrypt(b64_pwd.encode(), padding.PKCS1v15())
    return base64.b64encode(encrypted).decode()

def get_token():
    try:
        return open('.ragflow_token').read().strip()
    except FileNotFoundError:
        click.echo("❌ Not authenticated. Run: python cli.py auth", err=True)
        exit(1)

def get_headers():
    return {"Authorization": f"Bearer {get_token()}"}

def get_sdk_url(endpoint):
    """
    Converts the base /v1 URL to the SDK /api/v1 URL structure.
    Example: https://.../v1 -> https://.../api/v1/datasets
    """
    root = BASE_URL.replace("/v1", "")
    return f"{root}/api/v1{endpoint}"

@click.group()
def cli():
    """RAGFlow CLI"""
    pass

@cli.command()
@click.option('--email', default=lambda: os.getenv('RAGFLOW_EMAIL', 'omar@auto.com'))
@click.option('--password', default=lambda: os.getenv('RAGFLOW_PASSWORD', '123456789!'))
@click.option('--nickname', default=lambda: os.getenv('RAGFLOW_NICKNAME', 'Omar'))
def auth(email, password, nickname):
    """Step 1: Authenticate and get API token"""
    s = requests.Session()
    enc_pwd = encrypt_password(password)
    
    # Internal API for login/register still uses BASE_URL
    r = s.post(f"{BASE_URL}/user/register", json={"email": email, "password": enc_pwd, "nickname": nickname})
    
    if r.status_code == 200:
        data = r.json()
        if data["code"] == 0:
            click.echo(f"✓ Registered: {data['message']}")
        elif "already registered" in data.get("message", "").lower():
            r = s.post(f"{BASE_URL}/user/login", json={"email": email, "password": enc_pwd})
            data = r.json()
            if data["code"] == 0:
                click.echo(f"✓ Logged in: {data['message']}")
            else:
                click.echo(f"❌ Login failed: {data['message']}", err=True)
                exit(1)
        else:
            click.echo(f"❌ Registration failed: {data['message']}", err=True)
            exit(1)
        
        session_cookie = s.cookies.get('session')
        if not session_cookie:
            click.echo("❌ Failed to retrieve session cookie.", err=True)
            exit(1)
            
        cookies = {'session': session_cookie}
        # Internal API to generate token
        r = requests.post(f"{BASE_URL}/system/new_token", json={}, cookies=cookies)
        
        if r.status_code == 200 and r.json()["code"] == 0:
            token = r.json()["data"]["token"]
            with open('.ragflow_token', 'w') as f:
                f.write(token)
            click.echo(f"✓ API Token saved to .ragflow_token")
        else:
            click.echo(f"⚠ Could not generate API token automatically.")

@cli.command()
@click.option('--name', prompt='Knowledge Base Name', help='Name of the dataset')
def create_kb(name):
    """Step 2: Create a Knowledge Base (Dataset)"""
    headers = get_headers()
    # SDK Endpoint: /api/v1/datasets
    url = get_sdk_url("/datasets")
    
    payload = {
        "name": name, 
        "permission": "me",
        "chunk_method": "naive"
    }
    
    r = requests.post(url, headers=headers, json=payload)
    data = r.json()
    
    if data.get("code") == 0:
        kb_id = data["data"]["id"]
        click.echo(f"✓ Knowledge Base Created. ID: {kb_id}")
        click.echo(f"  Next: python cli.py upload --kb-id {kb_id} --file <path>")
    else:
        click.echo(f"❌ Failed: {data.get('message', r.text)}", err=True)

@cli.command()
@click.option('--kb-id', prompt='Knowledge Base ID', help='ID of the knowledge base')
@click.option('--file', prompt='File Path', help='Path to the file to upload')
def upload(kb_id, file):
    """Step 3: Upload a document"""
    headers = get_headers()
    # SDK Endpoint: /api/v1/datasets/{id}/documents
    url = get_sdk_url(f"/datasets/{kb_id}/documents")
    
    if not os.path.exists(file):
        click.echo(f"❌ File not found: {file}", err=True)
        return

    click.echo(f"Uploading {file}...")
    with open(file, 'rb') as f:
        files = {'file': (os.path.basename(file), f)}
        r = requests.post(url, headers=headers, files=files)
        
    try:
        data = r.json()
        if data.get("code") == 0:
            click.echo(f"✓ Uploaded successfully")
        else:
            click.echo(f"❌ Upload failed: {data.get('message')}", err=True)
    except Exception as e:
        click.echo(f"❌ Error parsing response: {r.text}", err=True)

@cli.command()
@click.option('--kb-id', prompt='Knowledge Base ID', help='ID of the knowledge base')
@click.option('--graphrag', is_flag=True, help='Enable GraphRAG')
@click.option('--raptor', is_flag=True, help='Enable RAPTOR')
def configure_rag(kb_id, graphrag, raptor):
    """Step 4: Enable Advanced RAG Features"""
    headers = get_headers()
    
    # 1. Get current config via SDK List/Get
    list_url = get_sdk_url("/datasets")
    r = requests.get(list_url, headers=headers, params={"id": kb_id, "page": 1, "page_size": 1})
    data = r.json()
    
    if data.get("code") != 0 or not data.get("data"):
        click.echo(f"❌ Failed to fetch KB details: {data.get('message', 'KB not found')}", err=True)
        return

    kb_info = data["data"][0]
    parser_config = kb_info.get("parser_config", {})
    
    updates_made = []
    if graphrag:
        parser_config.setdefault("graphrag", {})["use_graphrag"] = True
        updates_made.append("GraphRAG")
    
    if raptor:
        parser_config.setdefault("raptor", {})["use_raptor"] = True
        updates_made.append("RAPTOR")

    if not updates_made:
        click.echo("⚠ No options selected.")
        return

    # 2. Update via SDK PUT
    update_url = get_sdk_url(f"/datasets/{kb_id}")
    
    update_payload = {
        "parser_config": parser_config
    }
    
    r = requests.put(update_url, headers=headers, json=update_payload)
    resp = r.json()
    
    if resp.get("code") == 0:
        click.echo(f"✓ Enabled: {', '.join(updates_made)}")
        click.echo("  ℹ Run: python cli.py run-task --kb-id {kb_id} --task [graphrag|raptor]")
    else:
        click.echo(f"❌ Update failed: {resp.get('message')}", err=True)

@cli.command()
@click.option('--kb-id', prompt='Knowledge Base ID', help='ID of the knowledge base')
@click.option('--task', type=click.Choice(['graphrag', 'raptor']), prompt='Task Type', help='Task to run')
def run_task(kb_id, task):
    """Step 5: Trigger GraphRAG or RAPTOR analysis"""
    headers = get_headers()
    
    if task == 'graphrag':
        url = get_sdk_url(f"/datasets/{kb_id}/run_graphrag")
    elif task == 'raptor':
        url = get_sdk_url(f"/datasets/{kb_id}/run_raptor")
    
    r = requests.post(url, headers=headers, json={})
    data = r.json()
    
    if data.get("code") == 0:
        click.echo(f"✓ {task.upper()} task started.")
        click.echo(f"  ℹ Check status: python cli.py check-task --kb-id {kb_id} --task {task}")
    else:
        click.echo(f"❌ Failed: {data.get('message')}", err=True)

@cli.command()
@click.option('--kb-id', prompt='Knowledge Base ID', help='ID of the knowledge base')
def start_parsing(kb_id):
    """Step 5.5: Start parsing for all UNSTART documents"""
    headers = get_headers()
    
    # 1. Get list of all documents in the KB
    list_url = get_sdk_url(f"/datasets/{kb_id}/documents")
    r = requests.get(list_url, headers=headers, params={"page": 1, "page_size": 1000})
    data = r.json()
    
    if data.get("code") != 0:
        click.echo(f"❌ Failed to list documents: {data.get('message')}", err=True)
        return

    docs = data.get("data", {}).get("docs", [])
    # Filter for documents that haven't started or failed
    # 0: UNSTART, 4: FAIL
    target_ids = [d["id"] for d in docs if d.get("run") in ["UNSTART", "0", "FAIL", "4"]]
    
    if not target_ids:
        click.echo("✓ No documents need parsing (all are running or done).")
        return

    click.echo(f"🚀 Starting parsing for {len(target_ids)} documents...")

    # 2. Trigger the run endpoint via SDK
    # SDK Path: POST /api/v1/datasets/{dataset_id}/chunks
    # Payload: {"document_ids": [...]}
    run_url = get_sdk_url(f"/datasets/{kb_id}/chunks")
    
    payload = {
        "document_ids": target_ids
    }
    
    r = requests.post(run_url, headers=headers, json=payload)
    data = r.json()
    
    if data.get("code") == 0:
        click.echo("✓ Parsing started successfully.")
        click.echo("  ℹ Use 'list-documents' to monitor progress.")
    else:
        click.echo(f"❌ Failed to start parsing: {data.get('message')}", err=True)

@cli.command()
@click.option('--kb-id', prompt='Knowledge Base ID', help='ID of the knowledge base')
@click.option('--task', type=click.Choice(['graphrag', 'raptor']), prompt='Task Type', help='Task to monitor')
def check_task(kb_id, task):
    """Step 6: Monitor Task Progress (Advanced RAG)"""
    headers = get_headers()
    
    if task == 'graphrag':
        url = get_sdk_url(f"/datasets/{kb_id}/trace_graphrag")
    elif task == 'raptor':
        url = get_sdk_url(f"/datasets/{kb_id}/trace_raptor")
    
    r = requests.get(url, headers=headers)
    data = r.json()
    
    if data.get("code") == 0:
        task_info = data.get("data", {})
        if not task_info:
            click.echo(f"⚠ No active {task} task found for this KB.")
            return

        progress = task_info.get("progress", 0) * 100
        status_msg = task_info.get("progress_msg", "Processing...")
        
        bar_length = 20
        filled_length = int(bar_length * progress / 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        click.clear()
        click.echo(f"Task: {task.upper()} | ID: {task_info.get('id')}")
        click.echo(f"Progress: [{bar}] {progress:.1f}%")
        click.echo(f"Status: {status_msg}")
        
        if progress >= 100:
            click.echo("\n✅ Task Complete!")
    else:
        click.echo(f"❌ Error checking status: {data.get('message')}", err=True)

@cli.command()
@click.option('--kb-id', prompt='Knowledge Base ID', help='ID of the knowledge base')
def list_documents(kb_id):
    """Step 6b: Check document parsing status"""
    headers = get_headers()
    # SDK Endpoint: /api/v1/datasets/{id}/documents
    url = get_sdk_url(f"/datasets/{kb_id}/documents")
    
    params = {"page": 1, "page_size": 20}
    r = requests.get(url, headers=headers, params=params)
    data = r.json()
    
    if data.get("code") == 0:
        docs = data.get("data", {}).get("docs", [])
        if not docs:
            click.echo("No documents found.")
            return

        click.echo(f"{'Name':<40} | {'Status':<10} | {'Tokens':<10} | {'Chunks':<10}")
        click.echo("-" * 80)
        
        all_done = True
        for doc in docs:
            name = (doc['name'][:37] + '...') if len(doc['name']) > 37 else doc['name']
            status = doc.get('run', 'UNKNOWN') # RUNNING, DONE, FAIL, UNSTART
            tokens = doc.get('token_count', 0)
            chunks = doc.get('chunk_count', 0)
            
            click.echo(f"{name:<40} | {status:<10} | {tokens:<10} | {chunks:<10}")
            
            if status != 'DONE':
                all_done = False
        
        if all_done:
            click.echo("\n✅ All documents parsed successfully. Retrieval is ready.")
        else:
            click.echo("\n⏳ Some documents are still processing. Please wait.")
            
    else:
        click.echo(f"❌ Failed to fetch documents: {data.get('message')}", err=True)

@cli.command()
@click.option('--kb-id', prompt='Knowledge Base ID', help='ID of the knowledge base')
@click.option('--question', prompt='Question', help='Query to test retrieval')
@click.option('--similarity', default=0.2, help='Similarity threshold (0.0-1.0)')
def test_retrieval(kb_id, question, similarity):
    """Step 7: Test Retrieval (Search)"""
    headers = get_headers()
    url = get_sdk_url("/retrieval")
    
    payload = {
        "dataset_ids": [kb_id],
        "question": question,
        "similarity_threshold": similarity,
        "top_k": 5  # Return top 5 results
    }
    
    click.echo(f"🔍 Searching: '{question}'...")
    r = requests.post(url, headers=headers, json=payload)
    data = r.json()
    
    if data.get("code") == 0:
        res = data.get("data", {})
        chunks = res.get("chunks", [])
        
        if not chunks:
            click.echo("⚠ No results found.")
            return

        click.echo(f"✓ Found {len(chunks)} matching chunks:\n")
        for i, chunk in enumerate(chunks):
            score = chunk.get("similarity", 0)
            content = chunk.get("content_with_weight", chunk.get("content", ""))
            doc_name = chunk.get("document_name", "Unknown Document")
            
            # Truncate content for display
            preview = content[:150].replace("\n", " ") + "..." if len(content) > 150 else content
            
            click.echo(f"{i+1}. [{score:.4f}] {doc_name}")
            click.echo(f"   \"{preview}\"\n")
    else:
        click.echo(f"❌ Retrieval failed: {data.get('message')}", err=True)

if __name__ == '__main__':
    cli()