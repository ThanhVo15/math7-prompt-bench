PROMPT_TAXONOMY = {
    0: {
        "level": 0,
        "name": "Zero-Shot Prompting",
        "category": "Zero-Shot",
        "description": "A direct question without any context or examples.",
        "template": "Solve this problems",
        "example": "A rectangle has a length of 15 cm and a width of 8 cm. What is its area?"
    },
    1: {
        "level": 1,
        "name": "Instructional Prompting",
        "category": "Few-Shot",
        "description": "Provides a specific role, audience, and output format.",
        "template": (
            "You are a patient math tutor explaining a concept to a 7th-grade student.\n"
            "Please solve the following problem in three distinct parts: 1. Problem Analysis, 2. Detailed Solution, 3. Key Concepts Summary.\n\n"
            "Problem:\n{problem_text}"
        ),
        "example": (
            "You are a patient math tutor explaining a concept to a 7th-grade student.\n"
            "Please solve the following problem in three distinct parts: 1. Problem Analysis, 2. Detailed Solution, 3. Key Concepts Summary.\n\n"
            "Problem:\n"
            "A rectangle has a length of 15 cm and a width of 8 cm. What is its area?"
        )
    },
    2: {
        "level": 2,
        "name": "Zero-Shot Chain-of-Thought",
        "category": "Thought Generation",
        "description": "Uses a simple trigger phrase to elicit step-by-step reasoning.",
        "template": (
            "Let's think step by step to solve the following problem:\n\n"
            "{problem_text}"
        ),
        "example": (
            "Let's think step by step to solve the following problem:\n\n"
            "A rectangle has a length of 15 cm and a width of 8 cm. What is its area?"
        )
    },
    3: {
        "level": 1,
        "name": "Few-Shot Example Prompting",
        "category": "Few-Shot",
        "description": "Provide the AI with an example of how you solve a problem and ask it to apply a similar style.",
        "template": (
            "This is my current problem and the way I solve it:\n[Paste your solution style here]\n\n"
            "Based on my style, could you solve the following problem:\n{problem_text}"
        ),
        "example": (
            "This is my current problem and the way I solve it:\n"
            "Problem: Area of a 10x5 rectangle.\nSolution: Area = length * width = 10 * 5 = 50 sq cm.\n\n"
            "Based on my style, could you solve the following problem:\n"
            "A rectangle has a length of 15 cm and a width of 8 cm. What is its area?"
        )
    },
    4: {
        "level": 2,
        "name": "Chain-of-Verification",
        "category": "Chain-of-Thought (CoT)",
        "description": "Asks the model to solve a problem and then self-verify its own answer.",
        "template": (
            "Follow these steps:\n"
            "1. Solve the following problem in detail: {problem_text}\n"
            "2. After you have the answer, create a list of 3 questions to verify your answer.\n"
            "3. Answer those verification questions.\n"
            "4. Draw a final conclusion about the answer."
        ),
        "example": (
            "Follow these steps:\n"
            "1. Solve the following problem in detail: A rectangle has a length of 15 cm and a width of 8 cm. What is its area?\n"
            "2. After you have the answer, create a list of 3 questions to verify your answer. (e.g., 'Is the unit of area correct?')\n"
            "3. Answer those verification questions.\n"
            "4. Draw a final conclusion about the answer."
        )
    },
    5: {
        "level": 2,
        "name": "Thread of Thought",
        "category": "Chain-of-Thought (CoT)",
        "description": "Asks the AI to synthesize knowledge according to a specific thinking process after solving the problem.",
        "template": (
            "Problem: {problem_text}\n\n"
            "After solving, synthesize all knowledge related to [Field, e.g., geometry]. Follow this thinking process:\n"
            "- Step 1: Analyze the problem.\n"
            "- Step 2: Evaluate with knowledge.\n"
            "- Step 3: Propose a solution."
        ),
        "example": (
            "Problem: A rectangle has a length of 15 cm and a width of 8 cm. What is its area?\n\n"
            "After solving, synthesize all knowledge related to geometry. Follow this thinking process:\n"
            "- Step 1: Analyze the problem.\n"
            "- Step 2: Evaluate with knowledge.\n"
            "- Step 3: Propose a solution."
        )
    },
    6: {
        "level": 2,
        "name": "Graph-of-Thoughts (GoT) Prompting",
        "category": "Chain-of-Thought (CoT)",
        "description": "Asks the AI to explore multiple solution paths, evaluate them, and choose the optimal one.",
        "template": (
            "Analyze and brainstorm multiple solutions to the problem: {problem_text}. "
            "Then, evaluate those solutions, choose the best one, and implement it."
        ),
        "example": (
            "Analyze and brainstorm multiple solutions to the problem: A rectangle has a length of 15 cm and a width of 8 cm. What is its area?. "
            "Then, evaluate those solutions, choose the best one, and implement it."
        )
    },
    7: {
        "level": 3,
        "name": "HTML-like Prompting",
        "category": "HTML",
        "description": "Uses HTML-like tags to clearly structure different parts of the prompt.",
        "template": (
            "<instruction>\n"
            "Solve this problem and explain it step-by-step for a seventh-grade student.\n"
            "</instruction>\n\n"
            "<problem>\n"
            "{problem_text}\n"
            "</problem>\n\n"
            "<constraint>\n"
            "Before solving, please summarize all relevant math knowledge for a seventh-grade student to understand easily.\n"
            "</constraint>"
        ),
        "example": (
            "<instruction>\n"
            "Solve this problem and explain it step-by-step for a seventh-grade student.\n"
            "</instruction>\n\n"
            "<problem>\n"
            "A rectangle has a length of 15 cm and a width of 8 cm. What is its area?\n"
            "</problem>\n\n"
            "<constraint>\n"
            "Before solving, please summarize all relevant math knowledge for a seventh-grade student to understand easily.\n"
            "</constraint>"
        )
    },
    8: {
        "level": 3,
        "name": "Meta-Reasoning over Multiple CoTs",
        "category": "Ensembling",
        "description": "Uses a sequence of prompts to make the AI refine and select the most suitable solution method.",
        "template": (
            "Prompt 1: List all possible solutions to {problem_text} and related knowledge.\n"
            "Prompt 2: Based on the above solutions, choose the best solution for [Audience, e.g., 7th graders] and solve it."
        ),
        "example": (
            "Prompt 1: List all possible solutions to 'Area of 15x8 rectangle' and related knowledge.\n"
            "Prompt 2: Based on the above solutions, choose the best solution for 7th graders and solve it."
        )
    }
}

