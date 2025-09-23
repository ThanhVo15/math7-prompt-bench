# 🎓 PromptOptima: An Experimental Framework for Educational Prompt Engineering

PromptOptima is an interactive web application built to research and discover the principles of effective prompt engineering in an educational context, with a specific focus on 7th-grade mathematics.

[](https://www.google.com/search?q=https://your-streamlit-app-url.com) ---

## 📖 Table of Contents

  - [About The Project]
  - [Core Research Framework]
      - [Key Hypotheses]
      - [Research Questions]
  - [✨ Features]
  - [🛠️ Tech Stack]
  - [🚀 Getting Started]
      - [Prerequisites]
      - [Installation]
  - [👨‍💻 Usage]
  - [🔬 Methodology]
  - [🤝 Contributing]
  - [📝 License]

-----

## 📌 About The Project & Research Problem

Large Language Models (LLMs) have demonstrated significant potential in solving complex problems. However, the quality of their output is highly dependent on the quality of the input prompt. For non-expert users like educators and students, constructing an effective prompt that elicits a correct, clear, and pedagogically sound solution remains a major challenge.

**PromptOptima** was created to address this gap. It is not a teaching tool but a dynamic research environment that allows us to observe how users discover and refine prompting techniques when provided with detailed analytical feedback. By collecting and analyzing thousands of user-model interactions, we aim to identify patterns of effective prompt structures and develop data-driven guidelines.

-----

## 🧠 Core Research Framework

Our research is guided by the following hypotheses and questions:

### Key Hypotheses

  - **H1: The Prompt Quality-Performance Correlation Hypothesis**

      - A prompt with higher linguistic quality (measured by lexical diversity via **MATTR** and readability via **LIX**) will correlate with a higher probability of the LLM generating a mathematically correct and pedagogically superior solution.

  - **H2: The Optimal Structure Hypothesis**

      - Prompt effectiveness is not a monotonic function of length. Well-structured prompts (e.g., using Chain-of-Thought principles, specifying an output format) will outperform longer, unstructured prompts.

### Research Questions

  - **RQ1: Efficacy of Prompt Structures Across Contexts**

      - How do different prompt structures affect LLM performance across various mathematical `Content Domains` and `Cognitive Demand Levels`?

  - **RQ2: The LLM's Interpretive Framework**

      - What linguistic factors does the LLM itself identify as contributing to a prompt's effectiveness? How do these qualitative insights align with our quantitative metrics?

  - **RQ3: The Impact of Metric-Driven Feedback**

      - To what extent does providing users with targeted, metric-driven feedback accelerate their ability to discover and adopt more effective prompt structures?

-----

## ✨ Features

  - **Interactive Chat Interface:** An intuitive interface for users to input problems and experiment with different prompts.
  - **Problem Classification:** Allows users to provide metadata for each problem (domain, cognitive level) to enable deeper, segmented analysis.
  - **Real-time AI Feedback:**
      - **Solver AI (`gpt-3.5-turbo`):** Solves the problem and provides a qualitative analysis of the user's prompt.
      - **Judger AI (`gpt-4o`):** Assesses the pedagogical quality of the solution against a detailed rubric.
  - **Empirical Consistency Check:** Automatically runs each prompt three times to measure the stability and reliability of the generated answer.
  - **Intelligent Suggestion System:** Provides prompt templates and suggestions to help users improve their skills.
  - **Automated Data Logging:** All interactions, metrics, and results are automatically logged to Google Sheets for analysis.

-----

## 🛠️ Tech Stack

  - **Backend & Frontend:** Python, Streamlit
  - **AI Models:** OpenAI (GPT-3.5-Turbo, GPT-4o)
  - **Data Storage:** Google Sheets
  - **Data Handling:** Pydantic, Pandas

-----

## 🚀 Getting Started

To run this project on your local machine, follow the steps below.

### Prerequisites

  - Python 3.9+
  - `pip` (Python package installer)

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/promptoptima.git
    cd promptoptima
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your secrets:**
    Create a file at `.streamlit/secrets.toml` and add your credentials. This is a critical step for connecting to the OpenAI and Google Sheets APIs.

    ```toml
    # .streamlit/secrets.toml

    # OpenAI API Key
    [openai]
    api_key = "sk-..."

    # Google Sheets (GCP Service Account credentials)
    [gcp_service_account]
    type = "service_account"
    project_id = "your-gcp-project-id"
    private_key_id = "..."
    private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
    client_email = "...@...iam.gserviceaccount.com"
    client_id = "..."
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    token_uri = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url = "..."

    [google_sheets]
    spreadsheet_name = "Your Google Sheet Name"
    ```

    **Note:** Make sure you have shared editor permissions for your Google Sheet with the `client_email` from your service account.

4.  **Run the Streamlit app:**

    ```bash
    streamlit run app.py
    ```

    Open your browser and navigate to `http://localhost:8501`.

-----

## 👨‍💻 Usage

1.  **Set up the Problem:** In the left sidebar, enter your Name/ID and classify the problem by `Content Domain`, `Cognitive Level`, and `Problem Context`. Click **Confirm Setup**.
2.  **Enter the Problem:** In the main area, enter the text of the math problem you want to solve.
3.  **Test Prompts:**
      - Use the **Default Prompt** for a baseline result.
      - Alternatively, enter your own **Custom Prompt** in the chat input and press Enter.
4.  **Analyze the Results:**
      - Review the solution generated by the AI.
      - Check the **AI's Feedback** section for analysis of your prompt and the generated solution.
5.  **Grade and Iterate:**
      - Grade the response as **Correct** or **Incorrect** and click **Save Grade**.
      - After grading, click the **Suggestion** button to receive a new prompt template and continue experimenting.

-----

## 🔬 Methodology

This project employs a rigorous methodology to ensure the objectivity and reliability of its findings. A core component is the dual-model architecture:

  - **Solver Model (`gpt-3.5-turbo`):** Acts as the subject of the study, generating solutions.
  - **Evaluator Model (`gpt-4o`):** Acts as the expert adjudicator, scoring the Solver's output.

This approach mitigates **self-assessment bias** and ensures that solution quality is graded as objectively as possible.

For a complete overview of the research design, variables, and data analysis plan, please see the [**METHODOLOGY.md**](https://www.google.com/search?q=METHODOLOGY.md) document.

-----

## 🤝 Contributing

Contributions are welcome to improve the project. Please fork the repository, create a new branch for your feature, and open a Pull Request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

-----

## 📝 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.