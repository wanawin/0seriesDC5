import streamlit as st
import itertools

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
                digits = [str(i) for i in range(10)]
                full_combos = set()
                for triplet in itertools.product(digits, repeat=3):
                    for pair in seed_pairs:
                        combo = tuple(sorted([*pair, *triplet]))
                        if combo.count(combo[0]) <= 2:
                            full_combos.add(combo)

                st.session_state.full_combos = list(set(full_combos))
                st.info(f"Generated {len(st.session_state.full_combos)} 5-digit combinations (box unique). ✅")
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
                if st.button("Proceed to Cold Digit Trap"):
                    st.session_state.step = 3

            if st.session_state.step == 3:
                st.markdown("### Step 3: Cold Digit Trap")
                final_pool = []
                for combo in st.session_state.filtered:
                    if any(d in cold_digits_set for d in combo):
                        final_pool.append(combo)
                st.session_state.final_pool = final_pool
                st.success(f"After Cold Digit Trap: {len(final_pool)} combos remain ✅")
                if st.button("Finish and Show Trap v3 Candidates"):
                    st.session_state.step = 4

            if st.session_state.step == 4:
                st.markdown("### Final Trap v3 Candidate Combos")
                for combo in st.session_state.final_pool:
                    st.code("".join(combo))

                st.download_button(
                    label="Download Combos as TXT",
                    data="\n".join("".join(c) for c in st.session_state.final_pool),
                    file_name="trapv3_candidates.txt"
                )
    except Exception as e:
        st.error(f"Error: {e}")
