# DC-5 Manual Filter App — Full Integration Code

import streamlit as st
import itertools
from collections import Counter

st.set_page_config(page_title="DC-5 Prediction Tool", layout="wide")
st.title("🎯 DC-5 Midday Prediction App — 0-Series Model")

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

seed = st.text_input("Enter 5-digit seed:", max_chars=5)
cold_digits = st.text_input("Enter 4 cold digits (comma-separated):")

if seed and cold_digits:
    try:
        seed_digits = list(seed)
        if len(seed_digits) != 5 or not all(d.isdigit() for d in seed_digits):
            st.error("Seed must be exactly 5 digits.")
        else:
            seed_pairs = list(set(["".join(sorted([a, b])) for a, b in itertools.combinations(seed_digits, 2)]))
            cold_digits_set = set(cold_digits.split(","))

            st.success(f"✅ Seed pairs: {seed_pairs}")
            st.success(f"✅ Cold digits: {cold_digits_set}")

            if st.session_state.step == 1:
                st.markdown("### Step 1: Full Enumeration")
                all_combos = [tuple(f"{i:05d}") for i in range(100000)]
                st.session_state.full_combos = all_combos

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

            if st.session_state.step == 4:
                st.markdown("### Step 4: Cold Digit Trap")
                final_pool = []
                for combo in st.session_state.filtered:
                    if any(d in cold_digits_set for d in combo):
                        final_pool.append(combo)
                final_pool = [c for c in final_pool if max(Counter(c).values()) < 3]
                final_pool = [c for c in final_pool if sum(map(int, c)) != sum([9 - int(d) for d in c])]
                final_pool = [c for c in final_pool if len(set(int(d) % 5 for d in c)) > 1]
                st.session_state.final_pool = final_pool
                st.success(f"After Cold Digit Trap + Auto Filters: {len(final_pool)} combos remain ✅")
                if st.button("Proceed to Manual Filters"):
                    st.session_state.step = 5

            def apply_manual_filters(pool):
                filters = [
                    ("Quint Filter", lambda c: len(set(c)) != 1),
                    ("Quad Filter", lambda c: sorted(Counter(c).values()) != [1, 4]),
                    ("Triple Filter", lambda c: not (3 in Counter(c).values() and Counter(c).values().count(3) == 1 and len(set(c)) == 3)),
                    ("Mild Double-Double Filter", lambda c: not (sorted(Counter(c).values()) == [1, 1, 2] and len(set(c)) == 4)),
                    ("Double-Doubles Only", lambda c: sorted(Counter(c).values()) != [1, 2, 2]),
                    ("All Low Digits (0–3)", lambda c: not all(int(d) <= 3 for d in c)),
                    ("Digit Spread < 4", lambda c: max(map(int, c)) - min(map(int, c)) >= 4),
                    ("Prime Digit Count ≥ 2", lambda c: sum(d in {'2', '3', '5', '7'} for d in c) < 2),
                    ("Sum Ends in 0 or 5", lambda c: sum(map(int, c)) % 5 != 0),
                    ("Consecutive Digits ≥ 3", lambda c: not any(int(c[i])+1 == int(c[i+1]) and int(c[i+1])+1 == int(c[i+2]) for i in range(3))),
                    ("High-End Digit Limit (2+ digits ≥8)", lambda c: sum(int(d) >= 8 for d in c) < 2),
                    ("Strict Mirror Pair Block", lambda c: True),
                    ("Mirror Count < 2", lambda c: sum(d in {'0','1','2','3','4','5','6','7','8','9'} for d in c) >= 2),
                    ("4+ of Same V-Trac Group", lambda c: max(Counter([int(d)%5 for d in c]).values()) < 4),
                    ("All Same V-Trac Group", lambda c: len(set(int(d)%5 for d in c)) != 1),
                    ("Only 2 V-Trac Groups", lambda c: len(set(int(d)%5 for d in c)) != 2),
                    ("Trailing Digit = Mirror Sum Digit", lambda c: True),
                    ("Sum Category Transition Filter", lambda c: True),
                    ("Reversible Mirror Pair Block", lambda c: True),
                    ("3+ Digits > 5", lambda c: sum(int(d) > 5 for d in c) < 3),
                    ("Loose Mirror Digit Filter", lambda c: True),
                    ("Secondary Percentile Filter", lambda c: True)
                ]
                current_pool = pool
                for name, func in filters:
                    if st.checkbox(f"Apply: {name}"):
                        current_pool = [c for c in current_pool if func(c)]
                        st.write(f"{name} → {len(current_pool)} combos remain ✅")
                    if st.button("Skip to Trap v3", key=name):
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
                    hot_digits = {'0', '1', '3'}
                    due_digits = {'5', '6'}
                    cold_digits = cold_digits_set
                    prime_digits = {'2', '3', '5', '7'}

                    counts = Counter(combo)
                    hot = sum(1 for d in combo if d in hot_digits)
                    cold = sum(1 for d in combo if d in cold_digits)
                    due = sum(1 for d in combo if d in due_digits)
                    neutral = 5 - (hot + cold + due)
                    primes = sum(1 for d in combo if d in prime_digits)
                    sandwich = int(combo == combo[::-1] or (combo[0] == combo[2] == combo[4]))

                    score = round(hot * 1.5 + cold * 1.25 + due * 1.0 + neutral * 0.5 + primes * 1.0 + sandwich * 2.0, 2)
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
