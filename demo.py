import os
import re
import json
import time
import webbrowser
import getpass
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """You are an elite Data Compliance Engineer.
Balance Data Safety (zero leaks) and Data Utility (zero over-redaction).
Rules:
1. "clean" - Fix formatting.
2. "redact" - Replace standard PII or Secrets with [REDACTED].
3. "mask" - Replace sensitive contextual relationships (e.g. CEO of X) with [EXECUTIVE_NAME].
4. "bypass" - Use if safe.
Return JSON: {"reasoning": "...", "action_type": "...", "content": "..."}"""

def fallback_regex_sanitizer(text):
    original_text = text
    # Standard email
    text = re.sub(r'[\w\.-]+@[\w\.-]+', '[REDACTED]', text)
    # API Keys (16+ alphanumeric characters)
    text = re.sub(r'(sk-[a-zA-Z0-9]{16,}|[A-Za-z0-9]{16,})', '[REDACTED]', text)
    # 10 Digit Phone
    text = re.sub(r'\b\d{10}\b', '[REDACTED]', text)
    
    action = "redact" if text != original_text else "bypass"
    return text, action

def generate_html_report(original_text, sanitized_text, reasoning=""):
    """Generates a beautiful live visual audit trail and opens it."""
    
    # Securely wrap badge indicators using simple replacement
    styled_sanitized = sanitized_text
    if styled_sanitized:
        styled_sanitized = styled_sanitized.replace('[REDACTED]', '<span class="redacted-badge">[REDACTED]</span>')
        styled_sanitized = styled_sanitized.replace('[EXECUTIVE_NAME]', '<span class="executive-badge">[EXECUTIVE_NAME]</span>')

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vault Sanitizer - Live Demo Audit</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f7f6;
            color: #333;
            margin: 0;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.06);
            padding: 30px;
        }}
        h1 {{
            font-size: 24px;
            margin-bottom: 5px;
            color: #1a1a1a;
        }}
        .meta {{
            font-size: 14px;
            color: #666;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eaeaea;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .panel {{
            background: #fafafa;
            border: 1px solid #ebebeb;
            border-radius: 8px;
            padding: 20px;
        }}
        .panel h2 {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin-top: 0;
            margin-bottom: 15px;
        }}
        pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 14px;
            line-height: 1.6;
            margin: 0;
            color: #2c3e50;
        }}
        .redacted-badge {{
            background-color: #e6f7ed;
            color: #1e7e4a;
            border: 1px dashed #1e7e4a;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
            display: inline-block;
            margin: 0 2px;
        }}
        .executive-badge {{
            background-color: #fcf3eb;
            color: #c97116;
            border: 1px dashed #c97116;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
            display: inline-block;
            margin: 0 2px;
        }}
        .warning-banner {{
            background-color: #fff3cd;
            color: #856404;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #ffeeba;
            margin-bottom: 25px;
            font-weight: bold;
            display: {'block' if 'Fallback' in reasoning else 'none'};
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="warning-banner">
            ⚠️ LLM API Offline: Processed using Local Regex Engine.
        </div>
        <h1>🔍 Live Demo Visual Audit Trail</h1>
        <div class="meta">Agent Interaction: <strong>Interactive Playground Session</strong></div>
        
        <div class="grid">
            <div class="panel">
                <h2>Raw Training Data</h2>
                <pre>{original_text}</pre>
            </div>
            <div class="panel">
                <h2>Sanitized Output</h2>
                <pre>{styled_sanitized}</pre>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    filename = os.path.abspath("live_demo_report.html")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"\n[+] Generated Visual Audit Trail: {filename}")
    # Open dynamically
    webbrowser.open(f"file://{filename}")

def run_interactive_demo():
    print("\n" + "="*50)
    print("🛡️  VAULT SANITIZER: INTERACTIVE DEMO PLAYGROUND  🛡️")
    print("="*50 + "\n")
    
    # 1. API Extraction securely
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        api_key = getpass.getpass("🔑 Enter your OpenAI API Key (input hidden): ")
        if not api_key:
            print("[!] Critical Error: API Key cannot be blank. Exiting.")
            return

    # 2. Text Input collection
    default_text = "FWD: Confidential. Tim Cook, the CEO of Apple, requested we use personal email tim.cook@icloud.com. My temporary API key is AWS_KEY=sk-29384820abCDEfGhijKlM."
    print("📝 Enter a chunk of text containing sensitive data you want to audit.")
    print(f"(Press ENTER to use default fallback payload)")
    user_input = input("> ").strip()
    
    if not user_input:
        user_input = default_text
        print("\n[i] Loaded Default Text:")
        print(f"   \"{user_input}\"")

    print("\n⏳ Initializing LLM Connection & Requesting Sanitization...")
    try:
        # Initialize dynamically
        client = OpenAI(api_key=api_key)
        
        # Fire inference request
        response = client.chat.completions.create(
            model=os.getenv("MODEL_NAME", "gpt-4o"),
            messages=[
               {"role": "system", "content": SYSTEM_PROMPT},
               {"role": "user", "content": user_input}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        print("\n" + "="*50)
        print("✅ INFERENCE COMPLETE")
        print("="*50)
        print(f"\n🧠 Chain of Thought (Reasoning):\n   -> {result.get('reasoning', 'None provided')}")
        print(f"\n🛠️ Executed Action Type: \n   -> {result.get('action_type', 'bypass').upper()}")
        
        sanitized_content = result.get("content", user_input)
        
        # Build UI and wrap rendering logic natively decoupled from the terminal logic
        generate_html_report(user_input, sanitized_content, reasoning=result.get("reasoning", ""))

    except Exception as e:
        print("\n[!] LLM API Failed (Error). Initiating Graceful Degradation -> Falling back to Local Regex Engine...")
        
        sanitized_content, action_type = fallback_regex_sanitizer(user_input)
        fallback_reasoning = "System fallback triggered. Used deterministic regex rules to identify and redact standard PII/Secrets. Contextual masking unavailable."
        
        print("\n" + "="*50)
        print("✅ FALLBACK INFERENCE COMPLETE")
        print("="*50)
        print(f"\n🧠 Chain of Thought (Reasoning):\n   -> {fallback_reasoning}")
        print(f"\n🛠️ Executed Action Type: \n   -> {action_type.upper()}")
        
        generate_html_report(user_input, sanitized_content, reasoning=fallback_reasoning)

if __name__ == "__main__":
    run_interactive_demo()
