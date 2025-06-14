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

            

            if st.session_state.step == 4:
                st.markdown("### Step 4: Cold Digit Trap")
                final_pool = []
                for combo in st.session_state.filtered:
                    if any(d in cold_digits_set for d in combo):
                        final_pool.append(combo)
                st.session_state.final_pool = final_pool
                st.success(f"After Cold Digit Trap: {len(final_pool)} combos remain ✅")
                if st.button("Proceed to Manual Filters"):
                    st.session_state.step = 5

            def apply_manual_filters(pool):
                filters = [
                    ("Mild Double-Double Elim", lambda c: len(set(c)) > 3),
                    ("Sum Ends in 0 or 5", lambda c: sum(map(int, c)) % 5 != 0),
                    ("Consecutive Digits ≥ 3", lambda c: not any(int(c[i])+1 == int(c[i+1]) and int(c[i+1])+1 == int(c[i+2]) for i in range(3))),
                    ("Digit 9 Count ≥ 2", lambda c: c.count('9') < 2),
                    ("All 5 V-Trac Groups Present", lambda c: len(set(int(d)%5 for d in c)) < 5),
                    ("Only 2 V-Trac Groups Present", lambda c: len(set(int(d)%5 for d in c)) > 2),
                    ("4+ of Same V-Trac Group", lambda c: max(Counter([int(d)%5 for d in c]).values()) < 4),
                    ("Digit 4 Repeats", lambda c: c.count('4') < 2),
                    ("Three of Same Digit", lambda c: max(Counter(c).values()) < 3),
                    ("Triple Double Structure (A×3, B×2)", lambda c: not (sorted(Counter(c).values()) == [2, 3])),
                    ("Sum = 8, 7, 9, 10, 32", lambda c: sum(map(int, c)) not in {7, 8, 9, 10, 32}),
                    ("Palindromes", lambda c: list(c) != list(c)[::-1]),
                    ("Root Sum in Mirror of Combo Sum Digits", lambda c: str(sum(map(int, c)) % 9 or 9) not in [str(int(d)%10) for d in str(45-sum(map(int, c)))]),
                    ("Mirror Pair Block (e.g., 1 & 6)", lambda c: not any(set(p).issubset(set(c)) for p in [('1','6'),('2','7'),('3','8'),('4','9'),('0','5')])),
                    ("All 3 Least Frequent Digits", lambda c: not set(cold_digits_set).issubset(set(c))),
                    ("No Repeats of 0, 2, or 3", lambda c: not any(c.count(d) > 1 for d in ['0','2','3'])),
                    ("Digit 4 in Position 5", lambda c: c[4] != '4')
                ]
                current_pool = pool
                for name, func in filters:
                    if st.checkbox(f"Apply: {name}"):
                        current_pool = [c for c in current_pool if func(c)]
                        st.write(f"{name} → {len(current_pool)} combos remain ✅")
                    if st.button("Skip to Trap v3"):
                        st.session_state.step = 6
                        break
                return current_pool

            if st.session_state.step == 5:
                st.markdown("### Step 5: Manual Filters")
                manual_filtered = apply_manual_filters(st.session_state.final_pool)
                st.session_state.final_pool = manual_filtered
                st.success(f"After Manual Filters: {len(manual_filtered)} combos remain ✅")
                if st.button("Finish and Show Trap v3 Candidates"):
                    st.session_state.step = 6

            if st.session_state.step == 6:
                st.markdown("### Final Trap v3 Candidate Combos + Trap v3 Scores")

                def trapv3_score(combo):
                    hot_digits = {'0', '1', '3'}  # Example
                    due_digits = {'5', '6'}       # Example
                    cold_digits = cold_digits_set
                    prime_digits = {'2', '3', '5', '7'}

                    counts = Counter(combo)
                    hot = sum(1 for d in combo if d in hot_digits)
                    cold = sum(1 for d in combo if d in cold_digits)
                    due = sum(1 for d in combo if d in due_digits)
                    neutral = 5 - (hot + cold + due)
                    primes = sum(1 for d in combo if d in prime_digits)
                    sandwich = int(combo == combo[::-1] or (combo[0] == combo[2] == combo[4]))

                    score = round(
                        hot * 1.5 +
                        cold * 1.25 +
                        due * 1.0 +
                        neutral * 0.5 +
                        primes * 1.0 +
                        sandwich * 2.0,
                        2
                    )
                    return score

                scored = [("".join(c), trapv3_score(c)) for c in st.session_state.final_pool]
                scored.sort(key=lambda x: x[1], reverse=True)

                for combo, score in scored:
                    st.write(f"{combo} → Trap v3 Score: {score}")

                st.download_button(
                    label="Download Scored Combos",
                    data="\n".join(f"{combo} → Score: {score}" for combo, score in scored),
                    file_name="trapv3_scored_combos.txt"
                )
    except Exception as e:
        st.error(f"Error: {e}")
