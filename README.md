# DC-5 Filter Tracker

This repository contains a small Streamlit application for generating and filtering DC-5 combinations. The interface lets you enter a previous seed and choose how combinations are produced. Each generated combination is checked against hundreds of elimination rules.

## Running the application

1. Install Streamlit (and other optional testing tools):
   ```bash
   pip install streamlit pytest
   ```
2. Start the web app with:
   ```bash
   streamlit run dc_5_streamlit_app.py
   ```
   Streamlit will open a browser window where you can input the current and previous seeds to view remaining combinations.

## Running tests

Tests can be executed with `pytest` once they have been written:

```bash
pytest
```

## Filter rules

The file `filter intent summary.txt` contains the list of rules that determine which combinations are removed. Each line describes one rule in plain language. These rules have been parsed into the `should_eliminate` function within `dc_5_streamlit_app.py`, where each rule is applied in order.
