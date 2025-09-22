# MATH 7 PROMPT BENCH

This project is an interactive Streamlit application designed to help users improve their prompt engineering skills for mathematical problems. It provides real-time feedback, a structured leveling system, and data logging to guide users toward creating more effective, diverse, and readable prompts.

## ✨ Core Features

  * **Interactive UI:** A dual-pane interface to write prompts and see AI-generated solutions instantly.
  * **Real-time Metrics:** Automatic calculation of academic metrics for each prompt:
      * **MATTR (Moving Average Type-Token Ratio):** Measures lexical diversity.
      * **Reading Ease (LIX-based):** Measures the readability and complexity of the prompt.
      * **Token Count:** Provides the token length of the prompt.
  * **Gamified Improvement Loop:** A system that compares a user's current prompt against their initial "baseline" to visualize improvements in metrics.
  * **Structured Prompt Taxonomy:** A leveling system (from Level 0 Zero-Shot to Level 3 advanced techniques) that suggests better prompt structures.
  * **Serverless Data Logging:** All user interactions, prompts, AI responses, and calculated metrics are automatically logged to Google Sheets for later analysis.
  * **API Mocking:** A built-in "mock mode" that generates fake AI responses, allowing for full testing of the application's UI and data pipeline without needing a valid OpenAI API key.

-----

## ⚙️ How It Works: A Technical Overview

This application follows a modern, stateful frontend architecture powered by Streamlit, with a serverless backend for data persistence.

### Architecture

The system is composed of three main layers:

1.  **Frontend (UI & State Management):**

      * Built entirely in **Streamlit**.
      * Streamlit's `session_state` is used to manage the user's entire journey, including their current prompt, the baseline metrics for comparison, the latest AI solution, and their current prompt level. This ensures that each user has a unique, persistent experience during their session.

2.  **Backend Services (Logic & Integration):**

      * A collection of Python modules in the `src/` directory responsible for all core logic.
      * **OpenAI Client (`services/openai_client.py`):** A dedicated module to handle all interactions with the GPT-3.5-Turbo API. It includes error handling and the API mocking logic.
      * **Metrics Service (`core/metrics.py`):** Contains the business logic for calculating MATTR and Reading Ease based on the prompt text and a custom tokenizer.
      * **Google Sheets Manager (`services/google_sheets.py`):** Acts as the data persistence layer. It authenticates using a GCP Service Account and writes structured data (using Pydantic models) to designated tabs in a Google Sheet.

3.  **Database (Data Persistence):**

      * **Google Sheets** is used as a simple, effective, and serverless database. This is ideal for a prototype/MVP as it requires no database setup or maintenance. Each table in the data model corresponds to a tab in the sheet.

### The User Workflow & Gamification Loop

The core of the application is the iterative improvement loop.

1.  **Initialization:** A user starts a session. A sample problem is loaded, and a basic Level 0 ("Zero-Shot") prompt is generated.
2.  **The Baseline Run:** The user submits their first prompt. This action triggers:
      * A call to the OpenAI API.
      * The calculation of metrics for this initial prompt.
      * The creation of a `Run` and a `Metrics` record.
      * This first set of metrics is saved in `st.session_state` as the **"Baseline"**.
3.  **Feedback & Suggestion:** The UI displays the AI's solution and a metrics table comparing "Baseline" vs. "Current" (which are identical at this stage). The system then suggests an upgrade to the next prompt level (e.g., from Level 0 to Level 1).
4.  **Iterative Improvement:** The user applies the suggested prompt structure, manually refines it, and submits again.
5.  **The Comparison Run:** This new submission triggers the same process (API call, metrics calculation), but with a key difference:
      * The new metrics are now displayed in the "Current" column.
      * The UI calculates and displays the **delta** (e.g., +0.15 MATTR, +10.5 Reading Ease) between the Baseline and the Current prompt, providing instant, quantitative feedback on the improvement.
6.  **Data Logging:** Every single run, suggestion event, and metric calculation is logged as a new row in Google Sheets, linked by unique IDs (`run_id`, `session_id`), allowing for rich data analysis later on.

\!

### Data Model

The application uses Pydantic models (`models/schemas.py`) to ensure data is structured and validated before being sent to Google Sheets. The main tables are:

  * **`Runs`:** Logs every prompt submission, including the prompt text, the full AI response, user/session info, and performance data like latency and token usage.
  * **`Metrics`:** Stores the calculated MATTR, Reading Ease, and Token Count for each run, linked by `run_id`.
  * **`Suggestions`:** Records every time a prompt suggestion is shown to a user and whether they accepted it.

-----

## 📂 Project Structure

```
ga-prompting-mvp/
├── .streamlit/
│   └── secrets.toml         # Local secrets configuration
├── src/
│   ├── core/                # Core business logic (metrics, tokenizer)
│   │   ├── metrics.py
│   │   └── tokenizer.py
│   ├── models/              # Pydantic data schemas
│   │   └── schemas.py
│   ├── services/            # External service integrations
│   │   ├── google_sheets.py
│   │   └── openai_client.py
│   └── prompts/             # Prompt templates and taxonomy
│       └── taxonomy.py
├── app.py                     # Main Streamlit application file
├── requirements.txt           # Python dependencies
└── .gitignore                 # Git ignore file
```

-----

## 🛠️ Setup and Local Development

Follow these steps to run the application on your local machine.

### 1\. Prerequisites

  * Python 3.10+
  * A Google Cloud Platform account
  * An OpenAI API account

### 2\. Clone the Repository

```bash
git clone <your-repository-url>
cd ga-prompting-mvp
```

### 3\. Set up Python Environment

It is highly recommended to use a virtual environment.

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 4\. Configure Secrets

1.  **Create the secrets file:** Create a file at `.streamlit/secrets.toml`.
2.  **Set up Google Credentials:**
      * Go to the Google Cloud Console and create a new project.
      * Enable the "Google Drive API" and "Google Sheets API".
      * Create a "Service Account", grant it the "Editor" role, and download the JSON key file.
3.  **Populate `secrets.toml`:** Open the downloaded JSON key and your local `secrets.toml` file. Copy the values into the TOML file as shown below. **Use triple single quotes (`'''`) for the `private_key`**.
4.  **Add your OpenAI key.**
5.  **Create a Google Sheet** and share it with the `client_email` from your service account, giving it "Editor" permissions.

Your final `.streamlit/secrets.toml` file should look like this:

```toml
[openai]
api_key = "sk-YOUR_OPENAI_API_KEY"

[gcp_service_account]
type = "service_account"
project_id = "your-gcp-project-id"
private_key_id = "your-private-key-id"
private_key = '''-----BEGIN PRIVATE KEY-----\n...YOUR_PRIVATE_KEY...\n-----END PRIVATE KEY-----\n'''
client_email = "your-service-account-email@..."
client_id = "your-client-id"
# ... other fields from JSON ...

[google_sheets]
spreadsheet_name = "Your Google Sheet Name"
```

### 5\. Run the Application

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`.

-----

## ☁️ Deployment

This application is designed for easy deployment on **Streamlit Community Cloud**.

1.  **Push to GitHub:** Ensure your project is pushed to a public GitHub repository. Your `.gitignore` file should prevent the `secrets.toml` file from being uploaded.
2.  **Sign Up:** Sign up for [Streamlit Community Cloud](https://share.streamlit.io/) using your GitHub account.
3.  **Deploy:**
      * Click "New app" and select your repository.
      * Ensure the "Main file path" is set to `app.py`.
      * Click "Advanced settings..." and go to the "Secrets" section.
      * **Copy the entire content** of your local `.streamlit/secrets.toml` file and paste it into the secrets text box.
      * Click "Deploy\!". Your application will be live in a few minutes.