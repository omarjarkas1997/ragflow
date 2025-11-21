import click
import requests
import os
import json
import time

BASE_URL = os.getenv("RAGFLOW_BASE_URL", "https://rag-api.guardennes.ai")

def get_token():
    try:
        return open('.ragflow_token').read().strip()
    except FileNotFoundError:
        click.echo("❌ Not authenticated. Run: python cli.py login", err=True)
        exit(1)

def get_headers():
    return {"Authorization": f"Bearer {get_token()}"}

def sdk_url(path):
    return f"{BASE_URL}/api/v1{path}"

@click.group()
def cli():
    """RAGFlow CLI"""
    pass

@cli.command()
@click.option('--email', prompt=True)
@click.option('--password', prompt=True, hide_input=True)
@click.option('--nickname', prompt=True)
def register(email, password, nickname):
    """Register new account"""
    if len(password) < 9:
        click.echo("❌ Password must be at least 9 characters", err=True)
        return
    
    if not any(c in '!@#$%^&*(),.?":{}|<>' for c in password):
        click.echo("❌ Password must contain at least one symbol", err=True)
        return
    
    s = requests.Session()
    r = s.post(f"{BASE_URL}/v1/user/register", json={
        "email": email,
        "password": password,
        "nickname": nickname
    })
    
    if r.status_code != 200 or r.json()["code"] != 0:
        click.echo(f"❌ {r.json().get('message', 'Registration failed')}", err=True)
        return
    
    # Use the SAME session object (s)
    r = s.post(f"{BASE_URL}/v1/system/new_token", json={})
    
    if r.status_code == 200 and r.json()["code"] == 0:
        token = r.json()["data"]["token"]
        open('.ragflow_token', 'w').write(token)
        click.echo("✓ Registered & authenticated")
    else:
        click.echo("✓ Registered. Now run: python cli.py login")

@cli.command()
@click.option('--email', prompt=True)
@click.option('--password', prompt=True, hide_input=True)
def login(email, password):
    """Login and get token"""
    r = requests.post(f"{BASE_URL}/v1/user/login", json={
        "email": email,
        "password": password
    })
    
    if r.status_code == 200 and r.json()["code"] == 0:
        token = r.json()["data"]["token"]  # Token in login response!
        open('.ragflow_token', 'w').write(f"ragflow-{token}")
        click.echo("✓ Authenticated")
    else:
        click.echo(f"❌ {r.json().get('message', 'Login failed')}", err=True)

@cli.command()
@click.option('--name', prompt='Knowledge Base Name')
def create_kb(name):
    """Create a Knowledge Base"""
    headers = get_headers()
    url = sdk_url("/datasets")
    
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
@click.option('--kb-id', prompt='Knowledge Base ID')
@click.option('--file', prompt='File Path')
def upload(kb_id, file):
    """Upload a document"""
    headers = get_headers()
    url = sdk_url(f"/datasets/{kb_id}/documents")
    
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
@click.option('--kb-id', prompt='Knowledge Base ID')
@click.option('--graphrag', is_flag=True, help='Enable GraphRAG')
@click.option('--raptor', is_flag=True, help='Enable RAPTOR')
def configure_rag(kb_id, graphrag, raptor):
    """Enable Advanced RAG Features"""
    headers = get_headers()
    
    list_url = sdk_url("/datasets")
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
    
    update_url = sdk_url(f"/datasets/{kb_id}")
    update_payload = {"parser_config": parser_config}
    
    r = requests.put(update_url, headers=headers, json=update_payload)
    resp = r.json()
    
    if resp.get("code") == 0:
        click.echo(f"✓ Enabled: {', '.join(updates_made)}")
        click.echo(f"  ℹ Run: python cli.py run-task --kb-id {kb_id} --task [graphrag|raptor]")
    else:
        click.echo(f"❌ Update failed: {resp.get('message')}", err=True)

@cli.command()
@click.option('--kb-id', prompt='Knowledge Base ID')
@click.option('--task', type=click.Choice(['graphrag', 'raptor']), prompt='Task Type')
def run_task(kb_id, task):
    """Trigger GraphRAG or RAPTOR analysis"""
    headers = get_headers()
    
    if task == 'graphrag':
        url = sdk_url(f"/datasets/{kb_id}/run_graphrag")
    elif task == 'raptor':
        url = sdk_url(f"/datasets/{kb_id}/run_raptor")
    
    r = requests.post(url, headers=headers, json={})
    data = r.json()
    
    if data.get("code") == 0:
        click.echo(f"✓ {task.upper()} task started.")
        click.echo(f"  ℹ Check status: python cli.py check-task --kb-id {kb_id} --task {task}")
    else:
        click.echo(f"❌ Failed: {data.get('message')}", err=True)

@cli.command()
@click.option('--kb-id', prompt='Knowledge Base ID')
def start_parsing(kb_id):
    """Start parsing for all UNSTART documents"""
    headers = get_headers()
    
    list_url = sdk_url(f"/datasets/{kb_id}/documents")
    r = requests.get(list_url, headers=headers, params={"page": 1, "page_size": 1000})
    data = r.json()
    
    if data.get("code") != 0:
        click.echo(f"❌ Failed to list documents: {data.get('message')}", err=True)
        return
    
    docs = data.get("data", {}).get("docs", [])
    target_ids = [d["id"] for d in docs if d.get("run") in ["UNSTART", "0", "FAIL", "4"]]
    
    if not target_ids:
        click.echo("✓ No documents need parsing (all are running or done).")
        return
    
    click.echo(f"🚀 Starting parsing for {len(target_ids)} documents...")
    run_url = sdk_url(f"/datasets/{kb_id}/chunks")
    
    payload = {"document_ids": target_ids}
    
    r = requests.post(run_url, headers=headers, json=payload)
    data = r.json()
    
    if data.get("code") == 0:
        click.echo("✓ Parsing started successfully.")
        click.echo("  ℹ Use 'list-documents' to monitor progress.")
    else:
        click.echo(f"❌ Failed to start parsing: {data.get('message')}", err=True)

@cli.command()
@click.option('--kb-id', prompt='Knowledge Base ID')
@click.option('--task', type=click.Choice(['graphrag', 'raptor']), prompt='Task Type')
def check_task(kb_id, task):
    """Monitor Task Progress"""
    headers = get_headers()
    
    if task == 'graphrag':
        url = sdk_url(f"/datasets/{kb_id}/trace_graphrag")
    elif task == 'raptor':
        url = sdk_url(f"/datasets/{kb_id}/trace_raptor")
    
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
@click.option('--kb-id', prompt='Knowledge Base ID')
def list_documents(kb_id):
    """Check document parsing status"""
    headers = get_headers()
    url = sdk_url(f"/datasets/{kb_id}/documents")
    
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
            status = doc.get('run', 'UNKNOWN')
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
@click.option('--kb-id', prompt='Knowledge Base ID')
@click.option('--question', prompt='Question')
@click.option('--similarity', default=0.2, help='Similarity threshold (0.0-1.0)')
def test_retrieval(kb_id, question, similarity):
    """Test Retrieval (Search)"""
    headers = get_headers()
    url = sdk_url("/retrieval")
    
    payload = {
        "dataset_ids": [kb_id],
        "question": question,
        "similarity_threshold": similarity,
        "top_k": 5
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
            
            preview = content[:150].replace("\n", " ") + "..." if len(content) > 150 else content
            
            click.echo(f"{i+1}. [{score:.4f}] {doc_name}")
            click.echo(f"   \"{preview}\"\n")
    else:
        click.echo(f"❌ Retrieval failed: {data.get('message')}", err=True)

if __name__ == '__main__':
    cli()