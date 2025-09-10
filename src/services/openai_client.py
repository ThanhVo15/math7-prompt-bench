import streamlit as st
import openai
import time
import random
from datetime import datetime

# --- PHẦN MỚI: HÀM TẠO DỮ LIỆU GIẢ ---
def _generate_mock_solution(prompt_text: str) -> dict:
    """Tạo ra một lời giải giả lập để test khi không có API key."""
    st.warning("⚠️ Không tìm thấy API key của OpenAI. Đang tạo lời giải giả lập để kiểm tra.")
    
    # Giả lập một chút độ trễ
    time.sleep(1.5) 
    
    mock_text = (
        f"--- LỜI GIẢI MẪU (ĐỂ KIỂM TRA) ---\n"
        f"Đây là phản hồi được tạo tự động vào lúc: {datetime.now().strftime('%H:%M:%S')}.\n\n"
        f"Phân tích đề bài:\n"
        f"Đề bài yêu cầu tính toán dựa trên prompt đầu vào.\n\n"
        f"Các bước giải quyết:\n"
        f"1. Xác định các dữ kiện chính.\n"
        f"2. Áp dụng công thức phù hợp.\n"
        f"3. Đưa ra kết quả cuối cùng.\n\n"
        f"Đáp án: Đây là kết quả mẫu."
    )
    
    return {
        "text": mock_text,
        "tokens_in": len(prompt_text.split()), # Đếm token giả
        "tokens_out": len(mock_text.split()),
        "latency_ms": random.randint(1200, 2500),
        "error": None
    }

# --- HÀM GỐC ĐƯỢC CẬP NHẬT ---
def get_llm_solution(prompt_text: str, model: str = "gpt-3.5-turbo") -> dict:
    """
    Gọi API OpenAI nếu có key, ngược lại tạo dữ liệu giả.
    """
    try:
        # Kiểm tra xem API key có tồn tại và hợp lệ không
        api_key = st.secrets["openai"]["api_key"]
        if not api_key or "YOUR_OPENAI_API_KEY" in api_key:
            # Nếu key là rỗng hoặc là placeholder, dùng mock
            return _generate_mock_solution(prompt_text)
            
        openai.api_key = api_key
        
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
    except (KeyError, openai.error.AuthenticationError):
        # Nếu không có section [openai] hoặc key sai, dùng mock
        return _generate_mock_solution(prompt_text)
    except Exception as e:
        # Xử lý các lỗi khác
        st.error(f"Đã xảy ra lỗi không mong muốn: {e}")
        return {
            "text": f"Lỗi: {str(e)}",
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 0,
            "error": str(e)
        }