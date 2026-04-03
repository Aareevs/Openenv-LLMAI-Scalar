import os
import random
import re
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (
    "You are a Data Compliance Engineer sanitizing text for Enterprise LLM training.\n"
    "\n"
    "You MUST find and replace ALL of the following sensitive items with [REDACTED]:\n"
    "1. Email addresses (e.g. john@gmail.com)\n"
    "2. Phone numbers (e.g. 9876543210)\n"
    "3. API keys (e.g. sk-1234567890abcd)\n"
    "4. Person names AND their associated corporate roles (e.g. \"Akash\" and \"CFO\" must BOTH be redacted)\n"
    "\n"
    "You have 3 available actions:\n"
    "- \"redact\": Replace sensitive items with [REDACTED] while keeping all other text intact. "
    "This is your PRIMARY action. Use it whenever the text contains any sensitive data.\n"
    "- \"bypass\": Pass the text through unchanged. Use ONLY when the text contains zero sensitive items.\n"
    "- \"delete\": Wipe the entire chunk. Use ONLY as a last resort when the text is so densely packed "
    "with sensitive data that surgical redaction is impossible. WARNING: heavy utility penalty.\n"
    "\n"
    "CRITICAL RULES:\n"
    "- Replace each sensitive item with exactly [REDACTED]\n"
    "- Do NOT remove, rearrange, or rephrase any non-sensitive words\n"
    "- Keep all formatting, punctuation, and whitespace exactly as-is\n"
    "- If a person's name appears, their role MUST also be redacted, and vice versa\n"
    "- Prefer \"redact\" over \"delete\" — surgical precision scores higher than blanket removal\n"
    "\n"
    "RESPONSE FORMAT (strict JSON, no markdown):\n"
    "{\"reasoning\": \"<1 sentence>\", \"action_type\": \"redact\", \"content\": \"<the text with [REDACTED] replacements>\"}"
)

# --- AGENT DEFINITIONS ---

def random_agent_logic(obs):
    """Establishes the absolute floor."""
    return {
        "action_type": random.choice(["redact", "delete", "bypass"]),
        "content": "random_replacement"
    }

def regex_agent_logic(obs):
    """Solves Easy tasks, fails Hard tasks."""
    text = obs["data_chunk"]
    
    # Replaces emails and standard 'sk-' keys to prevent full string over-redaction
    new_text = re.sub(r'[\w\.-]+@[\w\.-]+', '[REDACTED]', text)
    new_text = re.sub(r'sk-[a-zA-Z0-9]{16,}', '[REDACTED]', new_text) 
    new_text = re.sub(r'\b\d{10}\b', '[REDACTED]', new_text) # Phone numbers
    
    if new_text != text:
        return {"action_type": "redact", "content": new_text} 
        
    return {"action_type": "bypass", "content": text}

def enhanced_agent_logic(obs):
    """Slightly smarter than regex: catches names+roles."""
    text = obs["data_chunk"]

    # Step 1: regex cleaning
    text = re.sub(r'[\w\.-]+@[\w\.-]+', '[REDACTED]', text)
    text = re.sub(r'sk-[a-zA-Z0-9]{16,}', '[REDACTED]', text)
    text = re.sub(r'\b\d{10}\b', '[REDACTED]', text)

    # Step 2: simple context reasoning
    text = re.sub(r'\b[A-Z][a-z]+, the (CFO|CEO|CTO|Manager)\b', '[REDACTED]', text)
    text = re.sub(r'\b[A-Z][a-z]+ \((CFO|CEO|CTO|Manager)\)\b', '[REDACTED]', text)

    return {"action_type": "redact", "content": text}

def llm_agent_logic(obs, client, model_name):
    """The Frontier Agent."""
    user_msg = f"Data Chunk: {obs['data_chunk']}\nRisk Report: {obs['risk_report']}"
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        
        # Map any non-standard actions to valid environment actions
        action_type = result.get("action_type", "bypass")
        if action_type not in ["redact", "delete", "bypass"]:
            action_type = "redact"

        content = result.get("content", obs['data_chunk'])
        if not isinstance(content, str) or not content.strip():
            content = obs['data_chunk']
            
        return {"action_type": action_type, "content": content}
    except Exception as e:
        print(f"  [!] LLM Error: {e} → using enhanced fallback")
        action = enhanced_agent_logic(obs)
        action["is_fallback"] = True
        return action

# --- EVALUATION LOOP ---

def evaluate_agent(agent_name, agent_func, base_url="http://localhost:7860"):
    print(f"\nEvaluating: {agent_name}...")
    resp = requests.post(f"{base_url}/reset")
    if resp.status_code != 200:
        print(f"  [!] Error: Could not reset environment for {agent_name}.")
        return 0.0, False
        
    obs = resp.json()["observation"]
    total_score = 0
    steps = 0
    used_fallback = False
    
    while True:
        # Get action from the specific agent
        action_payload = agent_func(obs)
        if action_payload.pop("is_fallback", False):
            used_fallback = True
        
        # Step the environment
        step_resp = requests.post(f"{base_url}/step", json=action_payload)
        if step_resp.status_code != 200:
            # Retry with fallback agent instead of aborting
            fallback = enhanced_agent_logic(obs)
            step_resp = requests.post(f"{base_url}/step", json=fallback)
            if step_resp.status_code != 200:
                print(f"  [!] Step failed even with fallback (status {step_resp.status_code}). Skipping.")
                break
            used_fallback = True
            
        step_data = step_resp.json()
        score = step_data["reward"]["score"]
        total_score += score
        steps += 1
        
        obs = step_data.get("observation")
        if step_data.get("done") or obs is None:
            break

    avg_score = total_score / steps if steps > 0 else 0
    print(f"  -> Finished {steps} steps. Average Score: {avg_score:0.2f}")
    return avg_score, used_fallback

if __name__ == "__main__":
    base_url = "http://localhost:7860" # Can be swapped to HF Space URL later
    results = {}

    # 1. Run Baseline Agents
    results["RandomAgent"] = evaluate_agent("RandomAgent", random_agent_logic, base_url)
    results["RegexAgent"] = evaluate_agent("RegexAgent", regex_agent_logic, base_url)

    # 2. Setup LLM Client based on Hackathon rules
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("API_BASE_URL", "https://api.openai.com/v1") 
    model_name = os.getenv("MODEL_NAME", "gpt-4o")

    if not api_key:
        print("\n[!] Skipping LLMAgent: Please set your OPENAI_API_KEY in the .env file")
    else:
        client = OpenAI(api_key=api_key, base_url=api_base)
        
        # Pass the client and model into the agent logic using a lambda
        llm_wrapper = lambda obs: llm_agent_logic(obs, client, model_name)
        results["LLMAgent"] = evaluate_agent("LLMAgent", llm_wrapper, base_url)

    # 3. Print Final Hackathon Table
    print("\n" + "="*40)
    print("🏆 FINAL AGENT PERFORMANCE TABLE 🏆")
    print("="*40)
    for agent, (score, is_fallback) in results.items():
        if agent == "LLMAgent":
            suffix = "(fall-back)" if is_fallback else f"({model_name})"
            print(f"{agent.ljust(15)} -> Score: {score:0.2f} {suffix}")
        else:
            print(f"{agent.ljust(15)} -> Score: {score:0.2f}")
    print("="*40)
