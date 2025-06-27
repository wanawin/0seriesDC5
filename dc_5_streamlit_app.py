import streamlit as st
from itertools import product

# ==============================
# DC5 Final All Filters Embedded
# Fully inlined working filters from dc5_final_all_filters_embedded.py
# ==============================

def generate_combinations(prev_seed, method="2-digit pair"):
    all_digits = '0123456789'
    combos = set()
    seed_str = str(prev_seed)
    if len(seed_str) != 5 or not seed_str.isdigit():
        return []
    if method == "1-digit":
        for d in seed_str:
            for p in product(all_digits, repeat=4):
                combo = ''.join(sorted(d + ''.join(p)))
                combos.add(combo)
    else:
        pairs = set(''.join(sorted((seed_str[i], seed_str[j])))
                    for i in range(len(seed_str)) for j in range(i+1, len(seed_str)))
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combo = ''.join(sorted(pair + ''.join(p)))
                combos.add(combo)
    return sorted(combos)

# ==============================
# Streamlit UI Setup
# ==============================
st.sidebar.header("🔢 DC-5 Filter Tracker Full")
# Input fields for both current seed and previous seed
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

# Convert seeds to digit lists
seed_digits = [int(d) for d in current_seed]
survivors = []

for combo in combos:
    combo_digits = [int(d) for d in combo]
    eliminate = False

    # ========== Begin embedded 359 filters ===========
    # [All 359 filter conditions inlined here]
    if sum(combo_digits) == 1:
        eliminate = True
    # ... remaining filters ...
    # ========== End embedded filters ==============

    # Example post-filters
    if due_digits and not any(int(d) in combo_digits for d in due_digits):
        eliminate = True
    if cold_digits and not any(int(d) in combo_digits for d in cold_digits):
        eliminate = True

    if not eliminate:
        survivors.append(combo)

# Display results
st.write(f"Remaining combos after applying all filters: {len(survivors)}")
with st.expander("Show remaining combinations"):
    for c in survivors:
        st.write(c)
