PROMPT_TAXONOMY = {
    # =======================
    # BEGINNER (level = 1)
    # =======================
    110: {
        "level": 1,
        "level_name": "Beginner",
        "name": "Zero-Shot CoT",
        "category": "CoT",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Zero-shot chain-of-thought: khuyến khích suy luận từng bước.",
        "template": (
            "Think step by step to solve the following problem carefully.\n"
            "Problem: {problem_text}"
        ),
        "example": "Write brief steps of reasoning and compute the final answer."
    },
    120: {
        "level": 1,
        "level_name": "Beginner",
        "name": "Instruction Prompting",
        "category": "Instruction",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Yêu cầu giải thích như cho học sinh lớp 7 và hiển thị tính toán.",
        "template": (
            "I have the following problem: {problem_text}\n"
            "Please solve it by:\n"
            "• Explaining the reasoning steps in a way that a 7th-grade student could understand.\n"
            "• Showing each calculation."
        ),
        "example": "Explain simply and show intermediate computations."
    },
    130: {
        "level": 1,
        "level_name": "Beginner",
        "name": "Zero-Shot Baseline",
        "category": "Baseline",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Baseline: chỉ yêu cầu giải.",
        "template": (
            "Solve this problem:\n"
            "{problem_text}"
        ),
        "example": "Return the numerical result with minimal working."
    },

    # =======================
    # INTERMEDIATE (level = 2)
    # =======================
    210: {
        "level": 2,
        "level_name": "Intermediate",
        "name": "Practice Real-World Scenarios",
        "category": "Real-World",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Mô phỏng tình huống đời sống, chỉ ra nơi áp dụng khái niệm và phản hồi từng bước.",
        "template": (
            "Simulate a real-world scenario where the mathematical concept in this problem is applied in daily life.\n"
            "Problem: {problem_text}\n\n"
            "Present the problem step by step, explain where the math concept is applied (theoretical vs. practical),\n"
            "and give feedback or reflection at each step of reasoning."
        ),
        "example": "Scenario → stepwise reasoning → feedback/reflection."
    },
    220: {
        "level": 2,
        "level_name": "Intermediate",
        "name": "Self-Consistency with Justification",
        "category": "SC+Justification",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Đề xuất 3 chiến lược, so sánh, chọn cách tối ưu rồi giải.",
        "template": (
            "For the problem: {problem_text},\n"
            "Propose three different valid strategies to solve it.\n"
            "For each strategy: briefly outline the steps.\n"
            "Then, compare all strategies, justify which is the most efficient, and solve the problem completely."
        ),
        "example": "List 3 strategies → compare → choose → full solution."
    },
    230: {
        "level": 2,
        "level_name": "Intermediate",
        "name": "Thread of Thought",
        "category": "ToT",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "ToT: phân luồng Phân tích → Giải → Tổng hợp & tự đánh giá.",
        "template": (
            "Problem: {problem_text}\n"
            "After solving it, summarize all related knowledge about the field (e.g., geometry, algebra).\n"
            "Follow the Thread of Thought process below:\n\n"
            "Thread 1: Analysis & Sub-Problems — Identify what is known and what must be found.\n\n"
            "Thread 2: Problem Solving — Solve each sub-problem step by step.\n\n"
            "Thread 3: Synthesis & Evaluation — Combine all results, provide the final answer, and self-evaluate the reasoning."
        ),
        "example": "Three distinct sections with analysis, solving, synthesis."
    },

    # =======================
    # ADVANCE (level = 3)
    # =======================
    310: {
        "level": 3,
        "level_name": "Advance",
        "name": "Real-Time Peer Review and Feedback",
        "category": "Peer-Review",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Phản biện lời giải học sinh: điểm mạnh, lỗi, cách đúng, chiến lược tự kiểm.",
        "template": (
            "Review a student’s solution to the problem: {problem_text}.\n"
            "The student answered or expected answer: \"{student_answer}\"  \n\n"
            "Provide constructive feedback by:\n"
            "1. Identifying strengths in the solution.\n"
            "2. Pinpointing the specific error or misunderstanding.\n"
            "3. Explaining the correct reasoning and answer.\n"
            "4. Suggesting strategies for checking or improving reasoning in similar problems."
        ),
        "example": "Rubric-style review + corrected solution."
    },
    320: {
        "level": 3,
        "level_name": "Advance",
        "name": "Hypothesis Generation and Solution Design (ReAct Pattern)",
        "category": "ReAct",
        "ccss_domains": ["SP", "RP", "EE"],
        "description": "Đặt giả thuyết phân tích và giải bài theo từng bước (ReAct-style).",
        "template": (
            "Role: Researcher or Analyst.\n"
            "Context: You are researching a mathematical system or concept related to the following problem: {problem_text}.\n"
            "Hypothesis: {hypothesis}\n"
            "Task: Based on the analytical hypothesis, solve the problem step by step."
        ),
        "example": "State hypothesis → reason & act in steps → final result."
    },
    330: {
        "level": 3,
        "level_name": "Advance",
        "name": "Personalized Learning Pathway Creation",
        "category": "Debate",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Mô phỏng tranh luận giữa 2 học sinh dùng 2 cách khác nhau; tổng kết & câu hỏi tiếp nối.",
        "template": (
            "Problem: {problem_text}\n\n"
        "Simulate a debate between two students, Alex and Ben, solving this problem.\n"
        "1. **Assign distinct methods**: Have Alex use one type of method (e.g., an algebraic approach) and Ben use another (e.g., a visual or logical approach).\n"
        "2. **Present their arguments**: Write out each student's step-by-step solution and their reasoning for why their method is good.\n"
        "3. **Conclude with a summary**: Summarize the debate, compare the efficiency and applicability of both methods, and pose a final question that encourages deeper thinking."
        ),
        "example": "Two-method comparison + meta-learning questions."
    },
}
