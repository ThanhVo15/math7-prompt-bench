import streamlit as st
import pandas as pd
import uuid

# Import các module tự định nghĩa
from src.core.tokenizer import AdvancedTokenizer
from src.core.metrics import BasicMetrics
from src.services.openai_client import get_llm_solution
from src.services.google_sheets import get_gsheet_manager
from src.prompts.taxonomy import PROMPT_TAXONOMY
from src.models.schemas import Run, Suggestion

# --- KHỞI TẠO CÁC ĐỐI TƯỢNG TOÀN CỤC ---
st.set_page_config(layout="wide", page_title="GA Prompting Tool")
tokenizer = AdvancedTokenizer()
metrics_service = BasicMetrics()
gsheet_manager = get_gsheet_manager()

# --- KHỞI TẠO SESSION STATE ---
def init_session_state():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.user_id = "user_" + str(uuid.uuid4())[:8] # Giả lập user ID
        
    if 'problem_text' not in st.session_state:
        st.session_state.problem_text = "Một hình chữ nhật có chu vi là 100m. Chiều dài hơn chiều rộng 10m. Tính diện tích của hình chữ nhật."

    if 'current_level' not in st.session_state:
        st.session_state.current_level = 0
        
    if 'current_prompt' not in st.session_state:
        st.session_state.current_prompt = PROMPT_TAXONOMY[0]['template'].format(
            problem_text=st.session_state.problem_text
        )

    # Dùng để lưu trữ kết quả của lần chạy gần nhất
    if 'last_run' not in st.session_state:
        st.session_state.last_run = {
            "solution": None,
            "metrics": None,
            "run_id": None
        }
        
    # Dùng để lưu trữ baseline để so sánh
    if 'baseline' not in st.session_state:
        st.session_state.baseline = {
            "metrics": None,
            "run_id": None
        }

init_session_state()

# --- HÀM XỬ LÝ LOGIC ---
def handle_prompt_submission():
    """Xử lý khi người dùng nhấn nút 'Gửi Prompt'."""
    prompt_text = st.session_state.current_prompt
    if not prompt_text or not prompt_text.strip():
        st.warning("Prompt không được để trống.")
        return

    with st.spinner("🤖 AI đang suy nghĩ..."):
        # 1. Gọi LLM để lấy lời giải
        solution_data = get_llm_solution(prompt_text)
        if solution_data["error"]:
            st.error(solution_data["text"])
            return

        # 2. Tạo đối tượng Run để lưu trữ
        run_record = Run(
            session_id=st.session_state.session_id,
            user_id=st.session_state.user_id,
            problem_text=st.session_state.problem_text,
            prompt_text=prompt_text,
            prompt_level=st.session_state.current_level,
            model_name="gpt-3.5-turbo",
            response_text=solution_data["text"],
            latency_ms=solution_data["latency_ms"],
            tokens_in=solution_data["tokens_in"],
            tokens_out=solution_data["tokens_out"]
        )
        
        # 3. Tính toán Metrics
        metrics_record = metrics_service.compute(prompt_text, tokenizer, run_id=run_record.run_id)

        # 4. Lưu vào Google Sheets
        gsheet_manager.append_data("runs", [run_record])
        gsheet_manager.append_data("metrics", [metrics_record])

        # 5. Cập nhật session state
        st.session_state.last_run = {
            "solution": solution_data["text"],
            "metrics": metrics_record,
            "run_id": run_record.run_id
        }

        # 6. Thiết lập baseline nếu đây là lần chạy đầu tiên
        if not st.session_state.baseline["metrics"]:
            st.session_state.baseline = {
                "metrics": metrics_record,
                "run_id": run_record.run_id
            }

def apply_suggestion(level):
    """Áp dụng template prompt từ taxonomy."""
    st.session_state.current_level = level
    st.session_state.current_prompt = PROMPT_TAXONOMY[level]['template'].format(
        problem_text=st.session_state.problem_text
    )
    # Ghi lại sự kiện chấp nhận gợi ý
    suggestion_record = Suggestion(
        session_id=st.session_state.session_id,
        user_id=st.session_state.user_id,
        run_id=st.session_state.last_run['run_id'] or "N/A",
        suggested_level=level,
        accepted=True,
    )
    gsheet_manager.append_data("suggestions", [suggestion_record])


# --- GIAO DIỆN NGƯỜI DÙNG (UI) ---
st.title("🚀 GA Prompting Gamification Tool (MVP)")
st.caption(f"Session ID: `{st.session_state.session_id}` | User ID: `{st.session_state.user_id}`")

# Cột chính: Input và Output
col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Đề bài")
    st.text_area(
        "Nhập đề bài toán tại đây", 
        key="problem_text",
        height=150,
    )
    
    st.subheader(f"💬 Prompt (Level {st.session_state.current_level}: {PROMPT_TAXONOMY[st.session_state.current_level]['name']})")
    st.text_area(
        "Chỉnh sửa prompt của bạn",
        key="current_prompt",
        height=250
    )
    st.button("Gửi Prompt", type="primary", on_click=handle_prompt_submission)

with col2:
    st.subheader("💡 Lời giải từ AI")
    solution_container = st.container(height=500, border=True)
    if st.session_state.last_run["solution"]:
        solution_container.markdown(st.session_state.last_run["solution"])
    else:
        solution_container.info("Lời giải sẽ xuất hiện ở đây sau khi bạn gửi prompt.")

st.divider()

# Hàng thứ hai: Metrics và Gợi ý
col3, col4 = st.columns([0.6, 0.4])

with col3:
    st.subheader("📊 Phân tích Metrics")
    if st.session_state.baseline["metrics"]:
        baseline_metrics = st.session_state.baseline["metrics"]
        current_metrics = st.session_state.last_run["metrics"]

        # Tính toán delta
        mattr_delta = current_metrics.mattr - baseline_metrics.mattr
        reading_ease_delta = current_metrics.reading_ease - baseline_metrics.reading_ease
        token_delta = current_metrics.token_count - baseline_metrics.token_count

        # Tạo DataFrame để hiển thị
        data = {
            "Metric": ["Đa dạng từ (MATTR)", "Độ dễ đọc (Reading Ease)", "Số Tokens"],
            "Baseline": [
                f"{baseline_metrics.mattr:.3f}",
                f"{baseline_metrics.reading_ease:.1f}/100",
                baseline_metrics.token_count
            ],
            "Hiện tại": [
                f"{current_metrics.mattr:.3f} ({mattr_delta:+.3f})",
                f"{current_metrics.reading_ease:.1f}/100 ({reading_ease_delta:+.1f})",
                f"{current_metrics.token_count} ({token_delta:+,d})"
            ]
        }
        st.table(pd.DataFrame(data))
    else:
        st.info("Gửi prompt đầu tiên để tạo baseline và xem phân tích.")

with col4:
    st.subheader("✨ Gợi ý cải tiến")
    next_level = st.session_state.current_level + 1
    if next_level in PROMPT_TAXONOMY:
        suggestion = PROMPT_TAXONOMY[next_level]
        st.markdown(f"**Cấp độ tiếp theo: {suggestion['name']}**")
        st.info(suggestion['description'])
        
        with st.expander("Xem cấu trúc gợi ý"):
            st.code(suggestion['template'], language='text')

        st.button(
            f"🚀 Nâng cấp lên Level {next_level}",
            on_click=apply_suggestion,
            args=(next_level,)
        )
    else:
        st.success("🎉 Bạn đã ở cấp độ cao nhất! Hãy thử nghiệm với các đề bài khác.")