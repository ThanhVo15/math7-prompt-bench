PROMPT_TAXONOMY = {
    # ===== LEVEL 1 · REMEMBERING (solve, but foreground recall) =====
    101: {
        "level": 1, "level_name": "Remembering",
        "name": "Direct Instruction (Zero-Shot)",
        "category": "Zero-Shot",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Recall the needed definition/formula, then solve the problem.",
        "template": (
            "Solve the problem below.\n"
            "First, state the exact definition/formula you will use (one line).\n"
            "Then substitute the given values and compute the result.\n"
            "Show minimal but correct working.\n\n"
            "Problem:\n{problem_text}\n\n"
            "Final Answer: <value with units if any>"
        ),
        "example": "Use the definition/formula, plug in values, and compute the numeric result."
    },
    102: {
        "level": 1, "level_name": "Remembering",
        "name": "Persona-Based Definition",
        "category": "Role",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Brief tutor voice: list key facts needed, then solve cleanly.",
        "template": (
            "You are a helpful 7th-grade math tutor. Solve the problem below.\n"
            "Step 1) Key facts needed (2–3 short bullets, no fluff).\n"
            "Step 2) Apply the facts to this problem with concise working.\n\n"
            "Problem:\n{problem_text}\n\n"
            "Final Answer: <value with units if any>"
        ),
        "example": "List the crucial fact(s) and immediately use them to get the result."
    },
    103: {
        "level": 1, "level_name": "Remembering",
        "name": "Constrained List Generation",
        "category": "Formatting",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Very constrained output: formula line + final result line.",
        "template": (
            "Solve the problem below.\n"
            "Return ONLY two lines in this exact format:\n"
            "Formula: <single formula you used>\n"
            "Final Answer: <numeric value with units if any>\n\n"
            "Problem:\n{problem_text}"
        ),
        "example": "Two lines only: the formula used and the computed answer."
    },

    # ===== LEVEL 2 · UNDERSTANDING (solve with conceptual explanation) =====
    201: {
        "level": 2, "level_name": "Understanding",
        "name": "Explanatory Paraphrasing",
        "category": "Explanation",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Explain the idea briefly while solving.",
        "template": (
            "Solve the problem below and explain the concept in your own words as you go.\n"
            "1) Brief concept check (1–2 sentences).\n"
            "2) Work the steps to the solution.\n"
            "3) Interpret the numeric result in one everyday sentence.\n\n"
            "Problem:\n{problem_text}\n\n"
            "Final Answer: <value with units if any>"
        ),
        "example": "Short conceptual note → steps → everyday interpretation + answer."
    },
    202: {
        "level": 2, "level_name": "Understanding",
        "name": "Analogical Mapping (Few-Shot)",
        "category": "Few-Shot",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Use a parallel analogy to clarify while solving.",
        "template": (
            "Here is an analogy example (for reference):\n"
            "[Example] {example_analogy}\n\n"
            "Now solve the problem below. While solving, craft a parallel analogy to explain why each key step makes sense to a 7th-grader.\n\n"
            "Problem:\n{problem_text}\n\n"
            "Final Answer: <value with units if any>"
        ),
        "example": "Use the new analogy to illuminate the critical step(s) and compute the result."
    },
    203: {
        "level": 2, "level_name": "Understanding",
        "name": "Flipped Interaction",
        "category": "Dialogue",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Ask to clarify if needed, then solve under explicit assumptions.",
        "template": (
            "Before solving, ask up to 3 short clarifying questions IF information is missing.\n"
            "If nothing is missing, explicitly state “No questions—solving now.”\n"
            "Then clearly state any assumptions and solve to get the numeric result.\n\n"
            "Problem:\n{problem_text}\n\n"
            "Final Answer: <value with units if any>"
        ),
        "example": "Diagnose info needs → state assumptions → compute the answer."
    },

    # ===== LEVEL 3 · APPLYING (procedural solving) =====
    301: {
        "level": 3, "level_name": "Applying",
        "name": "Step-by-Step CoT (Zero-Shot)",
        "category": "CoT",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Explicit steps and reasoning to a correct result.",
        "template": (
            "Solve the following problem. Show your work step-by-step with brief reasoning for each step.\n\n"
            "Problem:\n{problem_text}\n\n"
            "Final Answer: <value with units if any>"
        ),
        "example": "Clear, ordered steps ending in the computed result."
    },
    302: {
        "level": 3, "level_name": "Applying",
        "name": "Contextual Few-Shot CoT",
        "category": "Few-Shot CoT",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Mimic the structure of a worked example to solve.",
        "template": (
            "Here is a worked example to follow:\n{few_shot_example}\n\n"
            "Now solve this new problem using the SAME structure of steps and explanations:\n{problem_text}\n\n"
            "Final Answer: <value with units if any>"
        ),
        "example": "Mirror the example’s flow; compute the new answer."
    },
    303: {
        "level": 3, "level_name": "Applying",
        "name": "Program-Aided Logic (PAL)",
        "category": "Tool-Use",
        "ccss_domains": ["RP", "NS", "EE"],
        "description": "Translate to Python that prints only the final numeric answer.",
        "template": (
            "Translate the word problem into Python code that, when executed, prints ONLY the final numeric answer (no extra text).\n"
            "After the code block, include one sentence explaining why the computation is correct.\n\n"
            "Problem:\n{problem_text}"
        ),
        "example": "Produce minimal, correct code + a one-sentence rationale."
    },

    # ===== LEVEL 4 · ANALYZING (solve and analyze structure) =====
    401: {
        "level": 4, "level_name": "Analyzing",
        "name": "Compare Solution Methods",
        "category": "Analysis",
        "ccss_domains": ["RP", "NS", "EE", "G"],
        "description": "Solve by Method A and Method B; compare and conclude.",
        "template": (
            "Problem:\n{problem_text}\n\n"
            "Solve the problem twice:\n"
            "• Method A: {method_a}\n"
            "• Method B: {method_b}\n\n"
            "Show concise working for each, confirm both give the same result, then compare when each method is preferable.\n\n"
            "Final Answer: <value with units if any>"
        ),
        "example": "Two correct paths → same result → short comparison."
    },
    402: {
        "level": 4, "level_name": "Analyzing",
        "name": "Error Identification & Correction",
        "category": "Diagnostics",
        "ccss_domains": ["RP", "NS", "EE", "G", "SP"],
        "description": "Find the exact error, fix it, and solve correctly.",
        "template": (
            "A student attempted this problem but made a mistake.\n"
            "Problem:\n{problem_text}\n\n"
            "Student work:\n{student_work}\n\n"
            "1) Point to the exact step that is wrong.\n"
            "2) Explain the misconception briefly.\n"
            "3) Provide the correct step-by-step solution to the final result.\n\n"
            "Final Answer: <value with units if any>"
        ),
        "example": "Pinpoint the error → explain → correct solution + result."
    },
    403: {
        "level": 4, "level_name": "Analyzing",
        "name": "Generated-Knowledge Decomposition",
        "category": "Plan-and-Solve",
        "ccss_domains": ["G", "SP", "RP"],
        "description": "List required knowledge, decompose, then solve fully.",
        "template": (
            "Step 1 — Knowledge List: list all formulas/facts needed (bullets only).\n"
            "Step 2 — Decomposition: outline sub-problems in order (numbered list).\n"
            "Step 3 — Execute: solve each sub-problem and combine to get the final result.\n\n"
            "Problem:\n{problem_text}\n\n"
            "Final Answer: <value with units if any>"
        ),
        "example": "Knowledge → plan → execution → combined numeric result."
    },

    # ===== LEVEL 5 · EVALUATING & CREATING (solve + judge/design/create with solution) =====
    501: {
        "level": 5, "level_name": "Evaluating/Creating",
        "name": "Self-Consistency + Justification",
        "category": "SC-CoT",
        "ccss_domains": ["RP", "NS", "EE"],
        "description": "Propose 3 valid strategies, pick one, and solve with justification.",
        "template": (
            "For the problem below, do the following:\n"
            "1) Propose three different valid solution strategies (bulleted).\n"
            "2) Briefly evaluate them and choose the most efficient for this case.\n"
            "3) Solve the problem using the chosen strategy with clear steps.\n"
            "4) Give a one-line verification/check.\n\n"
            "Problem:\n{problem_text}\n\n"
            "Final Answer: <value with units if any>"
        ),
        "example": "List 3 ways → choose → solve → quick sanity check."
    },
    502: {
        "level": 5, "level_name": "Evaluating/Creating",
        "name": "Hypothesis Generation & Design (ReAct-style)",
        "category": "Reason+Act",
        "ccss_domains": ["SP"],
        "description": "Design the test AND compute/estimate the answer for the given context.",
        "template": (
            "You are a student scientist.\n"
            "Hypothesis: {hypothesis}\n\n"
            "Part A — Design: Describe a simulation/experiment to test the hypothesis (steps, data, decision rule).\n"
            "Part B — Solve: For the problem below, compute (or reasonably estimate) the probability/value implied by the context, showing key steps.\n\n"
            "Context / Problem:\n{problem_text}\n\n"
            "Final Answer: <numeric probability/value>"
        ),
        "example": "Design the test AND produce the numerical result for the stated context."
    },
    503: {
        "level": 5, "level_name": "Evaluating/Creating",
        "name": "Novel Problem Formulation (Meta-Prompting) + Solve",
        "category": "Creation",
        "ccss_domains": ["EE", "RP"],
        "description": "Create a word problem for the given equation/inequality AND solve it.",
        "template": (
            "Create an original, real-world word problem for a 7th-grader that can be modeled by the equation/inequality:\n"
            "{problem_text}\n"
            "State the problem you created, then solve the equation/inequality, interpret the solution in context, and give the final numeric answer.\n\n"
            "Final Answer: <value with units if any>"
        ),
        "example": "Write a short scenario matching the equation, solve it, and interpret the result."
    },
}
