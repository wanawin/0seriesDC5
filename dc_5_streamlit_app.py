import streamlit as st
from itertools import product
import dc5_final_all_filters_embedded as mod

# ==============================
# DC5 Final All Filters Embedded
# Using logic directly from dc5_final_all_filters_embedded.py
# ==============================

def generate_combinations(prev_seed, method="2-digit pair"):
    return mod.generate_combinations(prev_seed, method)

# ==============================
# Streamlit UI Setup
# ==============================
st.sidebar.header("🔢 DC-5 Filter Tracker Full")
def input_seed(prompt):
    value = st.sidebar.text_input(prompt).strip()
    if not value:
        st.sidebar.error(f"Please enter {prompt.lower()} to continue.")
        st.stop()
    if len(value) != 5 or not value.isdigit():
        st.sidebar.error("Seed must be exactly 5 digits (0–9).")
        st.stop()
    return value

current_seed = input_seed("Current 5-digit seed (required):")
prev_seed = input_seed("Previous 5-digit seed (required):")

hot_digits = [d for d in st.sidebar.text_input("Hot digits (comma-separated):").replace(' ', '').split(',') if d]
cold_digits = [d for d in st.sidebar.text_input("Cold digits (comma-separated):").replace(' ', '').split(',') if d]
due_digits = [d for d in st.sidebar.text_input("Due digits (comma-separated):").replace(' ', '').split(',') if d]
method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])  

# Generate combos using previous seed
combos = generate_combinations(prev_seed, method)
if not combos:
    st.write("No combinations generated. Check previous seed format.")
    st.stop()

# Convert current seed digits
seed_digits = [int(d) for d in current_seed]
survivors = []

for combo in combos:
    combo_digits = [int(d) for d in combo]
    # Use the original module's elimination logic
    eliminate = mod.should_eliminate(combo_digits, seed_digits)
    if not eliminate:
        survivors.append(combo)

# Display results
st.write(f"Remaining combos after applying all filters: {len(survivors)}")
with st.expander("Show remaining combinations"):
    for c in survivors:
        st.write(c)
