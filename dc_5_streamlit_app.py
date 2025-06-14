import streamlit as st
import itertools
from collections import Counter

# --- Setup ---
st.set_page_config(page_title="DC-5 Prediction Tool", layout="wide")
st.title("🎯 DC-5 Midday Prediction App — 0-Series Model")

# --- Initialize session state ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'full_combos' not in st.session_state:
    st.session_state.full_combos = []
if 'filtered' not in st.session_state:
    st.session_state.filtered = []
if 'final_pool' not in st.session_state:
    st.session_state.final_pool = []
if 'formula_combos' not in st.session_state:
    st.session_state.formula_combos = []

# --- Step 1: User Inputs ---
seed = st.text_input("Enter 5-digit seed:", max_chars=5)
cold_digits = st.text_input("Enter 4 cold digits (comma-separated):")

if seed and cold_digits:
    try:
        seed_digits = list(seed)
        if len(seed_digits) != 5 or not all(d.isdigit() for d in seed_digits):
            st.error("Seed must be exactly 5 digits.")
        else:
            seed_pairs = list(set(
                ["".join(sorted([a, b])) for a, b in itertools.combinations(seed_digits, 2)]
            ))
            cold_digits_set = set(cold_digits.split(","))

            st.success(f"✅ Seed pairs: {seed_pairs}")
            st.success(f"✅ Cold digits: {cold_digits_set}")

            if st.session_state.step == 1:
                st.markdown("### Step 1: Full Enumeration")
                all_combos = [tuple(f"{i:05d}") for i in range(100000)]
                st.session_state.full_combos = all_combos

                # Formula-generated combos (must contain at least 2 seed digits)
                formula_combos = []
                for combo in all_combos:
                    if sum(d in seed_digits for d in combo) >= 2:
                        formula_combos.append(combo)
                st.session_state.formula_combos = formula_combos

                st.info(f"Generated full 5-digit space: {len(all_combos)} combos ✅")
                st.info(f"Formula-generated combos (≥2 seed digits): {len(formula_combos)} ✅")
                if st.button("Proceed to Percentile Filter"):
                    st.session_state.step = 2

            if st.session_state.step == 2:
                st.markdown("### Step 2: Percentile Filter")
                filtered = []
                for combo in st.session_state.full_combos:
                    digit_sum = sum(int(d) for d in combo)
                    if 7 <= digit_sum <= 33:
                        filtered.append(combo)
                st.session_state.filtered = filtered
                st.info(f"After Percentile Filter: {len(filtered)} combos remain ✅")
                if st.button("Proceed to Formula Comparison"):
                    st.session_state.step = 3

            if st.session_state.step == 3:
                st.markdown("### Step 3.5: Intersection with Formula-Generated Combos")
                intersected = [c for c in st.session_state.filtered if c in st.session_state.formula_combos]
                st.session_state.filtered = intersected
                st.info(f"After Intersection Step: {len(intersected)} combos remain ✅")
                if st.button("Proceed to Deduplication"):
                    st.session_state.step = 3.6

            if st.session_state.step == 3.6:
                st.markdown("### Step 3.6: Deduplication (Box Uniqueness)")
                seen = set()
                deduped = []
                for combo in st.session_state.filtered:
                    sorted_box = "".join(sorted(combo))
                    if sorted_box not in seen:
                        seen.add(sorted_box)
                        deduped.append(combo)
                st.session_state.filtered = deduped
                st.info(f"After Deduplication: {len(deduped)} unique box combos remain ✅")
                if st.button("Proceed to Cold Digit Trap"):
                    st.session_state.step = 4

    except Exception as e:
        st.error(f"Error: {e}")
