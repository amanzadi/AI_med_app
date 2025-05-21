# DocSplain: Your AI Medical Appointment Assistant

DocSplain is an intelligent medical appointment assistant built with Streamlit and Agno. It helps patients find and book appointments within a simulated clinic, leveraging AI for smart interactions and web search for broader doctor discovery.

-----

## Features

  * **Patient Login:** Secure access for appointment booking.
  * **Smart Doctor Search:** Finds clinic doctors and can use web search to discover others.
  * **Appointment Booking:** Checks availability, books appointments, and handles emergencies.
  * **Billing Info:** Searches `dr-bill.ca` for billing details.
  * **AI-Powered Chat:** Understands your needs using Gemini or OpenAI models.

-----

## Setup & Run

Follow these quick steps to get DocSplain running:

### 1\. Prerequisites

  * **Python 3.8+**
  * **Git**
  * **API Key:**
      * **OpenAI:** Set `OPENAI_API_KEY` environment variable.

### 2\. Get the Code

```bash
git clone <repository_url> # Replace with your actual URL
cd <repository_name>
```

### 3\. Install Dependencies

It's best to use a virtual environment:

```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
# If you don't have requirements.txt, install manually:
# pip install streamlit agno-ai sqlalchemy beautifulsoup4 requests pandas openai duckduckgo-search
```

### 4\. Database (`db.py`)

Ensure you have a `db.py` file in your project. This file handles the clinic's database (doctors, patients, appointments) and includes sample data. If you don't have one, create it based on the example provided in previous responses.

```bash
python db.py
```

### 5\. Run the App

```bash
streamlit run app.py
```

Your browser will open to the DocSplain application. Log in with `john.doe@email.com` or `jane.smith@email.com` to start chatting\!
