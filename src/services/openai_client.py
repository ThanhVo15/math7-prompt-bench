import streamlit as st
import openai
import time
from typing import Dict, Any

def get_llm_solution(prompt_text: str, model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
    """Calls the OpenAI API and returns a structured response."""
    try:
        openai.api_key = st.secrets["openai"]["api_key"]
        
        start_time = time.time()
        
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.5,
        )
        
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        return {
            "text": response.choices[0].message['content'].strip(),
            "tokens_in": response.usage['prompt_tokens'],
            "tokens_out": response.usage['completion_tokens'],
            "latency_ms": latency_ms,
            "error": None
        }
    except Exception as e:
        return {
            "text": f"Lỗi API: {str(e)}",
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 0,
            "error": str(e)
        }