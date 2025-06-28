import streamlit as st
from itertools import product

# ==============================
# DC-5 Filter Tracker Full
# Filter rules parsed from filter intent summary.txt
# ==============================

def generate_combinations(prev_seed, method="2-digit pair"):
    all_digits = '0123456789'
    combos = set()
    seed_str = prev_seed
    if method == "1-digit":
        for d in seed_str:
            for p in product(all_digits, repeat=4):
                combo = ''.join(sorted(d + ''.join(p)))
                combos.add(combo)
    else:
        pairs = { ''.join(sorted((seed_str[i], seed_str[j])))
                  for i in range(len(seed_str)) for j in range(i+1, len(seed_str)) }
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combo = ''.join(sorted(pair + ''.join(p)))
                combos.add(combo)
    return sorted(combos)

# ==============================
# Streamlit UI Setup
# ==============================
st.sidebar.header("🔢 DC-5 Filter Tracker Full")

# Input for current and previous seeds
def input_seed(label):
    value = st.sidebar.text_input(label).strip()
    if not value:
        st.sidebar.error(f"Please enter {label.lower()}")
        st.stop()
    if len(value) != 5 or not value.isdigit():
        st.sidebar.error("Seed must be exactly 5 digits (0–9)")
        st.stop()
    return value

current_seed = input_seed("Current 5-digit seed (required):")
prev_seed    = input_seed("Previous 5-digit seed (required):")

hot_digits  = [d for d in st.sidebar.text_input("Hot digits (comma-separated):").replace(' ', '').split(',') if d]
cold_digits= [d for d in st.sidebar.text_input("Cold digits (comma-separated):").replace(' ', '').split(',') if d]
due_digits = [d for d in st.sidebar.text_input("Due digits (comma-separated):").replace(' ', '').split(',') if d]
method      = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])

# Generate all combinations
combos = generate_combinations(prev_seed, method)
if not combos:
    st.sidebar.error("No combinations generated. Check previous seed.")
    st.stop()

# Inline filter function with 359 rules
from typing import List
from filters import should_eliminate

# Apply filters and track counts
seed_digits = [int(d) for d in current_seed]
eliminated_counts = 0
survivors = []
for combo_str in combos:
    combo = [int(c) for c in combo_str]
    if should_eliminate(combo, seed_digits):
        eliminated_counts += 1
    else:
        survivors.append(combo_str)

# Sidebar summary
st.sidebar.markdown(f"**Total combos generated:** {len(combos)}")
st.sidebar.markdown(f"**Total eliminated:** {eliminated_counts}")
st.sidebar.markdown(f"**Remaining combos:** {len(survivors)}")

# Main page results
st.write(f"Remaining combos after all filters: **{len(survivors)}**")
with st.expander("Show remaining combinations"):
    for c in survivors:
        st.write(c)
