import os
import json
import re

def extract_json(text):
    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    raise ValueError(f"Could not parse JSON from response: {text[:300]}")

def call_llm(prompt, gemini_model="gemini-flash-latest", groq_model="llama-3.3-70b-versatile"):
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(gemini_model)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini failed ({e}), falling back to Groq...")

    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        raise RuntimeError("Both Gemini and Groq are unavailable.")

    from groq import Groq
    client = Groq(api_key=groq_key)
    response = client.chat.completions.create(
        model=groq_model,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
