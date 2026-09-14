# Supervea FAQ Bot Caching Demo

This Streamlit application is built to demonstrate and independently measure the semantic caching capabilities of the Supervea AI Gateway. 

Instead of relying solely on the gateway's internal telemetry, this demo provides a client-side measurement harness. It compares direct-to-provider API calls against calls routed through the Supervea Gateway, logging wall-clock latency, token usage, and cost savings in real-time. 

## Features

* **Performance Benchmarking:** Directly compares Gateway cache HITs, Gateway cache MISSes, and Direct-to-Provider latencies.
* **Independent Telemetry:** Measures true client-side wall-clock latency, providing a reliable second opinion to the Supervea dashboard.
* **Cost & Token Tracking:** Calculates token usage and estimated cost savings based on provider rates.
* **Secure Key Management:** Supervea and Provider API keys are entered directly in the browser via a modal dialog and are never stored or hardcoded.

## File Structure

* `app.py`: The main Streamlit application containing the UI and benchmarking logic.
* `kb.py`: The knowledge base containing the test FAQ questions.
* `requirements.txt`: Python package dependencies (including Streamlit).
* `.gitignore`: Standard git ignore file.
* `README.md`: This documentation file.

## How to Run Locally

You don't need any complex setup or environment variables to run this locally. 

1. **Install Dependencies:**
   Ensure you have Python installed, then run:
   ```bash
   pip install -r requirements.txt
