PROMPT_TAXONOMY = {
    0: {
        "level": 0,
        "name": "Zero-Shot",
        "description": "Hỏi trực tiếp, không có hướng dẫn.",
        "template": "{problem_text}"
    },
    1: {
        "level": 1,
        "name": "Instructional Prompt",
        "description": "Cung cấp vai trò và yêu cầu định dạng đầu ra.",
        "template": (
            "Bạn là một gia sư Toán học kiên nhẫn và tận tâm, đang giải thích cho một học sinh lớp 7.\n"
            "Hãy giải bài toán sau đây theo 3 phần rõ ràng: Phân tích đề bài, Trình bày lời giải, và Tóm tắt kiến thức.\n\n"
            "Đề bài:\n"
            "{problem_text}"
        )
    },
    2: {
        "level": 2,
        "name": "Chain-of-Thought (CoT)",
        "description": "Yêu cầu mô hình suy nghĩ từng bước.",
        "template": (
            "Hãy suy nghĩ từng bước một để giải quyết bài toán sau.\n\n"
            "Đề bài:\n"
            "{problem_text}"
        )
    },
    3: {
        "level": 3,
        "name": "Chain of Verification (CoVe)",
        "description": "Yêu cầu mô hình tự kiểm tra lại các bước giải.",
        "template": (
            "Giải bài toán sau. Sau khi có lời giải, hãy tự tạo ra 3 câu hỏi để kiểm tra lại các bước quan trọng trong lời giải của bạn và tự trả lời chúng. Cuối cùng, đưa ra đáp án cuối cùng.\n\n"
            "Đề bài:\n"
            "{problem_text}"
        )
    }
}