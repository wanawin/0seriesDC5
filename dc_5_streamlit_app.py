
import streamlit as st
import os, unicodedata, re
from itertools import product, combinations, groupby

try:
    import logipar
    LOGIPAR_AVAILABLE = True
except ImportError:
    LOGIPAR_AVAILABLE = False

def strip_prefix(raw_name: str) -> str:
    return re.sub(r'^\s*\d+[\.\)]\s*', '', raw_name).strip()

def normalize_name(raw_name: str) -> str:
    s = unicodedata.normalize('NFKC', raw_name)
    s = s.replace('≥', '>=').replace('≤', '<=').replace('→', '->').replace('–', '-').replace('—', '-')
    s = s.replace('\u200B', '').replace('\u00A0', ' ')
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def parse_manual_filters_txt(raw_text: str):
    entries = []
    skipped = []
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    current = None
    raw_block = []
    for raw_ln in lines:
        ln = raw_ln.strip()
        if not ln:
            if current:
                if current.get('name'):
                    entries.append(current)
                else:
                    skipped.append({'block': '\n'.join(raw_block)})
                current = None
                raw_block = []
            continue
        raw_block.append(raw_ln)
        norm_ln = unicodedata.normalize('NFKC', ln)
        low = norm_ln.lower()
        if low.startswith('type:'):
            if current is None:
                current = {'name': '', 'type': '', 'logic': '', 'action': ''}
            current['type'] = norm_ln.split(':', 1)[1].strip()
        elif low.startswith('logic:'):
            if current is None:
                current = {'name': '', 'type': '', 'logic': '', 'action': ''}
            current['logic'] = norm_ln.split(':', 1)[1].strip()
        elif low.startswith('action:'):
            if current is None:
                current = {'name': '', 'type': '', 'logic': '', 'action': ''}
            current['action'] = norm_ln.split(':', 1)[1].strip()
        else:
            if current:
                if current.get('name'):
                    entries.append(current)
                else:
                    skipped.append({'block': '\n'.join(raw_block[:-1])})
            clean = strip_prefix(norm_ln)
            name_norm = normalize_name(clean)
            current = {'name': name_norm, 'type': '', 'logic': '', 'action': ''}
            raw_block = [raw_ln]
    if current:
        if current.get('name'):
            entries.append(current)
        else:
            skipped.append({'block': '\n'.join(raw_block)})
    return entries, skipped

def generate_combinations(seed, method="2-digit pair"):
    all_digits = '0123456789'
    combos = set()
    seed_str = str(seed)
    if len(seed_str) < 2:
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

def apply_additional_filters(session_pool, label, logic, seed_digits):
    removed = []
    m_exact_sum = re.search(r'digit sum.*equals\s*(\d+)', logic, re.IGNORECASE)
    if m_exact_sum:
        target = int(m_exact_sum.group(1))
        keep = [c for c in session_pool if sum(int(d) for d in c) != target]
        removed = [c for c in session_pool if sum(int(d) for d in c) == target]
        return keep, removed
    m_seed_block = re.search(r'seed.*\[([0-9, ]+)\].*eliminate.*(even|odd)', logic, re.IGNORECASE)
    if m_seed_block:
        digits_needed = [int(x.strip()) for x in m_seed_block.group(1).split(',')]
        target_parity = m_seed_block.group(2).lower()
        if all(d in seed_digits for d in digits_needed):
            if target_parity == "even":
                keep = [c for c in session_pool if sum(int(d) for d in c) % 2 != 0]
                removed = [c for c in session_pool if sum(int(d) for d in c) % 2 == 0]
            elif target_parity == "odd":
                keep = [c for c in session_pool if sum(int(d) for d in c) % 2 == 0]
                removed = [c for c in session_pool if sum(int(d) for d in c) % 2 != 0]
            return keep, removed
    m_old = re.search(r'seed.*?(\d.*?)(?:->|→).*?(even|odd)', logic, re.IGNORECASE)
    if m_old:
        digits_needed = [int(x.strip()) for x in re.findall(r'\d+', m_old.group(1))]
        target_parity = m_old.group(2).lower()
        if all(d in seed_digits for d in digits_needed):
            if target_parity == "even":
                keep = [c for c in session_pool if sum(int(d) for d in c) % 2 != 0]
                removed = [c for c in session_pool if sum(int(d) for d in c) % 2 == 0]
            elif target_parity == "odd":
                keep = [c for c in session_pool if sum(int(d) for d in c) % 2 == 0]
                removed = [c for c in session_pool if sum(int(d) for d in c) % 2 != 0]
            return keep, removed
    return session_pool, []

st.title("🎯 DC-5 Midday Full Combo Filter App")

st.sidebar.header("🔢 Required Inputs")
seed = st.sidebar.text_input("5-digit previous seed (required):").strip()
hot_digits = [d for d in st.sidebar.text_input("Hot digits (comma-separated):").replace(' ', '').split(',') if d]
cold_digits = [d for d in st.sidebar.text_input("Cold digits (comma-separated):").replace(' ', '').split(',') if d]
due_digits = [d for d in st.sidebar.text_input("Due digits (comma-separated):").replace(' ', '').split(',') if d]
method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])

uploaded = st.sidebar.file_uploader("Upload manual filters (.txt)", type=['txt'])
parsed_entries = []
if uploaded is not None:
    raw_text = uploaded.read().decode("utf-8", errors="ignore")
    parsed_entries, skipped = parse_manual_filters_txt(raw_text)
    st.sidebar.success(f"Loaded {len(parsed_entries)} filters")

if seed:
    seed_digits = [int(d) for d in seed if d.isdigit()]
    combos_initial = generate_combinations(seed, method)
    session_pool = combos_initial.copy()
    elimination_history = []

    st.sidebar.markdown("## 🎯 Remaining Combos")
    st.sidebar.markdown(f"### `{len(session_pool)}` after filters")
    total_generated = len(combos_initial)
    total_eliminated = total_generated - len(session_pool)
    st.sidebar.markdown(f"**🔻 Eliminated:** `{total_eliminated}` ({round((total_eliminated / total_generated) * 100, 1)}%)")

    if parsed_entries:
            for combo in session_pool:
        combo_digits = [int(d) for d in combo]
        eliminate = False

        if sum(combo_digits) == 1:
        eliminate = True
        if all(d in seed_digits for d in [4, 5, 6, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 4, 7]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 6, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [5, 7, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [4, 6, 7, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [4, 5, 6, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 6, 7, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 5, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 4, 5, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 6, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 6, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 4, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 5, 7, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 3, 4, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 5, 7, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 4, 5, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 6, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 4, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 4, 5, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 5, 6, 7]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 5, 6, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 5, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 3, 6, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 5, 7]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 2, 4]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 7, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 5, 6, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 5, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 4, 5]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 4, 5, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 5, 6, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 6, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 5, 8, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 3, 5]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 6, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 7, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 7, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 5, 7]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 3, 4]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 3, 5, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 3, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [3, 4, 5, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 6, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 3, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [4, 6, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 7, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 4, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 3, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 7, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 3, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        # Could not parse: "If the seed's digit structure is a FullHouse (three of one digit and a pair of another), eliminate combos whose digit sum is even."
        # Could not parse: Eliminate combo if it does not contain at least one digit which is present in the seed but was not present in the draw preceding the seed.
        # Could not parse: Eliminate combo if it contains at least 2 digits which appeared in both of the previous 2 draws (including seed).
        # Could not parse: Eliminate combo if it does not contain at least 2 distinct digits which were present in at least one of the previous 2 draws (including seed).
        # Could not parse: Eliminate combo if it contains at least 2 distinct digits which each appeared in at least one of the previous 2 draws (including seed).
        # Could not parse: Eliminate combo if it does NOT include at least one digit not present in the previous 2 draws (including seed).
        # Could not parse: "if seed sum end digit is 7 and combo sum end digit is 8, eliminate combo"
        # Could not parse: "if seed sum end digit is 4 and combo sum end digit is 8, eliminate combo
        # Could not parse: "if seed sum end digit is 1 and combo sum end digit is 7, eliminate combo
        # Could not parse: "if seed sum end digit is 4 and combo sum end digit is 7, eliminate combo
        # Could not parse: "if seed sum end digit is 4 and combo sum end digit is 6, eliminate combo
        # Could not parse: "if seed sum end digit is 5 and combo sum end digit is 6, eliminate combo
        # Could not parse: "if seed sum end digit is 8 and combo sum end digit is 5, eliminate combo
        # Could not parse: "if seed sum end digit is 0 and combo sum end digit is 4, eliminate combo
        if all(d in seed_digits for d in [0, 2, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 4, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 3, 5, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 3, 7, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [4, 6, 7, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [4, 5, 6, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 6, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 4, 6, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 4, 6, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 7, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 6, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 4, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 4, 5, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 5, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 7, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 5, 6, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 4, 7, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 4, 6, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 4, 6, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 6, 7, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 3, 7, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 3, 6, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        # Could not parse: "if seed sum end digit is 3 and combo sum end digit is 3, eliminate combo
        if all(d in seed_digits for d in [0, 4, 5, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 8, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 3, 4]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 4, 5, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 2, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 6, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 6, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [6, 7, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 6, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [5, 6, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 3, 4, 5]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 7, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 4, 5, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 4, 5, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 5, 7, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 4, 6, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 4, 5, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 5, 7, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 4, 6, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 4, 5, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 4, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 6, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 3, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 4, 5, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [4, 7, 8, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 4, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 5, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 4, 7, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 5, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 6, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 4, 7, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 3, 7]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 3, 5]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 3, 5, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 4, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [3, 4, 6, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 5, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 5, 6, 7]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 6, 7, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 5, 6]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 4, 5]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 6, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 4, 5, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 7, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 5, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 4, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [4, 6, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 3, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 4, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [4, 6, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 3, 5]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 5, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 4, 7]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 3, 7]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 5, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 5, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 6, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 4, 6, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 4, 7]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 2, 4, 6]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [3, 5, 8, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 4, 6]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 3, 6, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [4, 5, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [3, 6, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 4, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 5, 7]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 7, 8, 9]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 5, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 3, 4, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [2, 4, 5, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 6, 8]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 4]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 1, 2]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 8, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [0, 4, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 5]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [4, 5, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 7, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 7, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [2, 3, 5]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        if all(d in seed_digits for d in [4, 5, 6]) and sum(combo_digits) % 2 == 1:
        eliminate = True
        if all(d in seed_digits for d in [1, 2, 5, 9]) and sum(combo_digits) % 2 == 0:
        eliminate = True
        # Could not parse: "if seed sum end digit is 3 and combo digit sum end digit is 1, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 22, eliminate combo"
        # Could not parse: eliminate combo if seed sum is 16-24 and combo sum is 25-33
        # Could not parse: eliminate combo if seed sum is 25-33 and combo sum is 0-15
        # Could not parse: Prime Digits ≥4,"Eliminate combos with ≥4 prime digits (2,3,5,7)"
        # Could not parse: eliminate combos which include a digit as well as thst digit's mirror
        # Could not parse: "eliminate combos containing  exactly 3 digits: two twice, one once."
        # Could not parse: eliminate combos in which 3 digits are identical
        # Could not parse: eliminate combos which contain 4 identical digits
        # Could not parse: eliminate combos whose digit sum matches seed mirror sum.,eliminate combo if combo digit sum = seed sum mirror
        # Could not parse: eliminate combo if combo contains no due digits
        # Could not parse: eliminate combo if combo sum last digit = seed sum first digit (e.g. 21, 18)
        # Could not parse: eliminate combo if seed contains (in any order)  both '0' and '7' and combo sum < 8 or > 28
        # Could not parse: eliminate combo if seed contains (in any order)  both '0' and '6' and combo sum < 8 or > 29
        # Could not parse: eliminate combo if seed contains (in any order)  both '0' and '5' and combo sum < 10 or > 30
        # Could not parse: eliminate combo if seed contains (in any order)  '00' and combo sum < 11 or > 33
        # Could not parse: seed digit exclusion 29,eliminate combo if seed contains (in any order)  1 and combo contains neither 4 nor 2
        # Could not parse: seed digit exclusion 28,"eliminate combo if seed contains (in any order)  5 and combo contains neither 2, 3, nor 1"
        # Could not parse: seed digit exclusion 27,eliminate combo if seed contains (in any order)  6 and combo contains neither 3 nor 4
        # Could not parse: cold digit trap - requires at least 1 digit from the coldest digits.,eliminate combo if no digit = 1 digit from cold digits
        # Could not parse: mirror count = 0 - eliminate combos that do not contain any mirror digit from the seed.,eliminate combo if combo does not contain the mirror of any digts in the seeed
        # Could not parse: combo contains last digit of mirror sum - manual filter.,"if any digit in the combo is =seed sum last digit mirror, eliminate mirror"
        # Could not parse: if seed contains (in any order)  0 -> combo must contain 1, 2, or 3.","if any digit in the seed is  0 and combo does not contain either 1, 2, or 3, eliminate combo"
        # Could not parse: all low digits (0-3) - eliminates if all 5 digits are from 0 to 3.,eliminate combos if all five digits are >/=3
        # Could not parse: high-end digit limit - eliminates if 2 or more digits >= 8.,eliminate combo if combo contains 2 or more digits >/= 8
        # Could not parse: digit spread < 4 - eliminates combos with low spread between digits.,eliminate combo if combo digit spread is <4
        # Could not parse: if Seed contains (in any order) 07 and sum <8 or >28.,eliminate combo if seed contains (in any order)  0 and 7 in any order and combo digit sum is <8 or >28
        # Could not parse: if Seed contains (in any order) 06 and sum <8 or >29.,eliminate combo if seed contains (in any order)  0 and 6  in any order and  combo digit sum is <8 or >29
        # Could not parse: sum > 40 - eliminates combos where digit sum is over 40.,"if combo digit sum is >40, eliminate combo"
        # Could not parse: if Seed contains (in any order) 05 and sum <10 or >30.,"if seed contains (in any order)  0 and 5 in any order and combo digit sum is <10 or >30, eliminate combo"
        # Could not parse: if Seed contains (in any order) 04 and sum <10 or >29.,"if seed contains (in any order)  0 and 4 in any order and combo digit sum is <10 or >29, eliminate combo"
        # Could not parse: if Seed contains (in any order) 03 and sum <13 or >35.,"if seed contains (in any order)  0 and 3 in any order and combo digit sum is <13 and >35, eliminate combo"
        # Could not parse: if Seed contains (in any order) 02 and sum <7 or >26.,"if seed contains (in any order)  0 and 2 in any order and combo sum is <7 or >26, eliminate combo"
        # Could not parse: if Seed contains (in any order) 00 and sum <11 or >33.,"if seed contains (in any order)  00 and combo digit sum is <11 or >33, eliminte combo"
        # Could not parse: repeating digit filter (3+ shared & sum < 25) - for singles only.,"if combo is a single ( 5 unique digits), is <25 and shares >/=3 digits with seed, eliminate combo"
        # Could not parse: v-trac: none of seed v-tracs present - eliminates if no seed v-tracs in combo.,eliminate combo if none of the v-trac groups from the seed is present in the combo
        # Could not parse: v-trac: all seed v-tracs present - eliminates if all v-trac groups from seed are in combo.,eliminate combo if all v-trac groups from seed are in combo.
        # Could not parse: v-trac: all 5 groups present - eliminates if all 5 v-trac groups used.,"If each of the 5 digits in the combo is from a different v trac group, 5 different v-trac groups in combo, eliminate combo"
        # Could not parse: v-trac: only 2 groups present - eliminates if only 2 v-trac groups used.,"if all five combo digits represent </=2 v-trac groups, eliminate combo"
        # Could not parse: v-trac: all digits same group - eliminates if all digits share the same v-trac group.,"if all digits in combo share a single v-trac group, eliminate combo"
        # Could not parse: if Seed contains (in any order) 2 -> combo must contain 4 or 5.,"if any digit in the seed is 2 and combo does not contain either 4 nor 5, eliminate combo"
        # Could not parse: if seed contains (in any order)  1 -> combo must contain 2, 3, or 4.","if any digit in the seed is 1 and combo does not contain either 2, 3, or 4, eliminate combo"
        # Could not parse: seed digit exclusion 26,"eliminate combo if seed contains (in any order)  8 and combo contains neither 1, 3, nor 2"
        # Could not parse: seed digit exclusion 25,eliminate combo if seed contains (in any order)  7 and combo contains neither 2 nor 1
        # Could not parse: seed digit exclusion 24,eliminate combo if seed contains (in any order)  4 and combo contains neither 5 nor 6
        # Could not parse: seed digit exclusion 23,"eliminate combo if seed contains (in any order)  9 and combo contains neither 3, 5, nor 1"
        if sum(combo_digits) == 37:
        eliminate = True
        if sum(combo_digits) == 10:
        eliminate = True
        if sum(combo_digits) == 39:
        eliminate = True
        if sum(combo_digits) == 40:
        eliminate = True
        if sum(combo_digits) == 38:
        eliminate = True
        if sum(combo_digits) == 9:
        eliminate = True
        if sum(combo_digits) == 8:
        eliminate = True
        if sum(combo_digits) == 7:
        eliminate = True
        if sum(combo_digits) == 6:
        eliminate = True
        if sum(combo_digits) == 36:
        eliminate = True
        if sum(combo_digits) == 45:
        eliminate = True
        if sum(combo_digits) == 44:
        eliminate = True
        if sum(combo_digits) == 43:
        eliminate = True
        if sum(combo_digits) == 42:
        eliminate = True
        if sum(combo_digits) == 41:
        eliminate = True
        if sum(combo_digits) == 5:
        eliminate = True
        if sum(combo_digits) == 4:
        eliminate = True
        if sum(combo_digits) == 3:
        eliminate = True
        if sum(combo_digits) == 2:
        eliminate = True
        if sum(combo_digits) == 34:
        eliminate = True
        # Could not parse: consecutive digits >= 4 - eliminates clusters of consecutive digits.,"eliminate combos with </=4 digits which follow one another in consecutive numerical order, despite how they are ordered in combo"
        # Could not parse: seed digit exclusion 1,Action: eliminate combo if seed contains (in any order)  2 and combo contains neither 5 nor 4.
        # Could not parse: "if seed sum =16, and combo digit sum is <12 and >20, eliminate combo","if seed sum =16, a combo digit sum is <12 and >20, eliminate combo"
        # Could not parse: seed digit exclusion 22,eliminate combo if seed contains (in any order)  3 and combo contains neither 5 nor 4
        # Could not parse: seed digit exclusion 21,"eliminate combo if seed contains (in any order)  0 and combo contains neither 1, 2, nor 3"
        # Could not parse: seed digit exclusion 20,"eliminate combo if seed contains (in any order)  1 and combo contains neither 2, 3, nor 4"
        # Could not parse: seed digit exclusion 19,eliminate combo if seed contains (in any order)  2 and combo contains neither 5 nor 4
        # Could not parse: seed sum range 18,Keep only combinations where the digit sum is between 20 and 28 (inclusive) if the seed sum is 26 or higher.
        # Could not parse: seed sum range 17,Keep only combinations where the digit sum is between 19 and 25 (inclusive) if the seed sum is 17
        # Could not parse: seed sum range 16,Keep only combinations where the digit sum is between 16 and 25 (inclusive) if the seed sum is between 22 and 23
        # Could not parse: seed sum range 15,Keep only combinations where the digit sum is between 14 and 24 (inclusive) if the seed sum is between 19 and 21
        # Could not parse: seed sum range 14,Keep only combinations where the digit sum is between 14 and 22 (inclusive) if the seed sum is between 13 and 15
        # Could not parse: seed sum range 13,Keep only combinations where the digit sum is between 12 and 25 (inclusive) if the seed sum is  12
        # Could not parse: seed sum range 12,Keep only combinations where the digit sum is between 12 and 20 (inclusive) if the seed sum is 16.
        # Could not parse: seed sum range 11,Keep only combinations where the digit sum is between 11 and 26 (inclusive) if the seed sum is 17 or 18.
        # Could not parse: "If digit 2 appears in the seed, then the combomust contain either digit 5 or digit 4 or else , eliminate comboIf digit 2 appears in the seed, then the combomust contain either digit 5 or digit 4 or else , eliminate combo",
        # Could not parse: "If digit 2 appears in the seed, then the combomust contain either digit 5 or digit 4 or else , eliminate combo"
        # Could not parse: " If seed sum is 24–25 and combo digit sum is <19 or >25, eliminate combo."," If seed sum is 24–25 and combo digit sum is <19 or >25, eliminate combo."
        # Could not parse: "if seed sum = 22or 23 and combo digit sum is <16 or >25, eliminate  combo",eliminate combo if sum <16 or >25
        # Could not parse: "if seed sum = 19, 20 or 21 and combo digit sum is <14 or >24, eliminate combo","if seed sum = 19, 20 or 21 and combo digit sum is <14 or >24, eliminate combo"
        # Could not parse: "if seed sum =13, 14 or 15 and combo digit sum is <14 and >22, eliminate combo","if seed sum =13, 14 or 15 and combo digit sum is <14 and >22, eliminate combo"
        # Could not parse: "if seed sum is </= 12 and combo digit sum <12 or >25, eliminate combo","if seed sum is </= 12 and combo digit sum <12 or >25, eliminate combo"
        # Could not parse: "if seed sum =17 or =18 and combo digit sum is <11 or >26, eliminate combo","if seed sum =17or seed sum =18 and combo digit sum is <11 or >26, eliminate combo"
        # Could not parse: "if seed sum end digit is 2 and combo digit sum end digit is 0, eliminate combo","if seed sum end digit is 2 and combo digit sum end digit is 0, eliminate combo"
        # Could not parse: seed sum = 13-15,"if seed sum is between 13 and 15 and combo digit sum is <14 and >22, eliminate combo"
        # Could not parse: seed sum = 17-18,"if seed sum =17-18 and combo digit sum is <11 or >26, eliminate combo"
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 34, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 34, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 33, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 33, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 32, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 32, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 31, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 31, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 30, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 30, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 29, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 29, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 28, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 28, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 27, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 27, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 35, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 35, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 26, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 26, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 24, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 24, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 22, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 22, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 21, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 21, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 20, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 20, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 19, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 19, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 18, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 18, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 17, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 17, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 16, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 16, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 25, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 25, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 36, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 36, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 37, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 37, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 38, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 38, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 21, eliminate combo  ","if combo has ≥5 shared digits with seed and combo digit sum < 21, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 20, eliminate combo  ","if combo has ≥5 shared digits with seed and combo digit sum < 20, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 19, eliminate combo  ","if combo has ≥5 shared digits with seed and combo digit sum < 19, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 18, eliminate combo  ","if combo has ≥5 shared digits with seed and combo digit sum < 18, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 17, eliminate combo  ","if combo has ≥5 shared digits with seed and combo digit sum < 17, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 16, eliminate combo  ","if combo has ≥5 shared digits with seed and combo digit sum < 16, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 15, eliminate combo  ","if combo has ≥5 shared digits with seed and combo digit sum < 15, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 14, eliminate combo  ","if combo has ≥5 shared digits with seed and combo digit sum < 14, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 13, eliminate combo  ","if combo has ≥5 shared digits with seed and combo digit sum < 13, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 12, eliminate combo  ","if combo has ≥5 shared digits with seed and combo digit sum < 12, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 11, eliminate combo  ","if combo has ≥5 shared digits with seed and combo digit sum < 11, eliminate combo  "
        # Could not parse: "if combo has ≥5 shared digits with seed and combo digit sum < 10, eliminate combo  ","if combo has ≥5 shared digits with seed and combo digit sum < 10, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 45, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 45, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 44, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 44, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 43, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 43, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 42, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 42, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 41, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 41, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 40, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 40, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 39, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 39, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 15, eliminate combo  ","if combo has ≥4 shared digits with seed and combo digit sum < 15, eliminate combo  "
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 13, eliminate combo","if combo has ≥4 shared digits with seed and combo digit sum < 13, eliminate combo"
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 12, elimiate combo","if combo has ≥4 shared digits with seed and combo digit sum < 12, elimiate combo"
        # Could not parse: "if combo has ≥4 shared digits with seed andcombo digit sum < 11, eliminate  combo","if combo has ≥4 shared digits with seed andcombo digit sum < 11, eliminate  combo"
        # Could not parse: eliminate combo if total digit sum is  ±15 from seed sum,eliminate combo if total digit sum is  ±15 from seed sum
        # Could not parse: eliminate combo if total digit sum is  ±14 from seed sum,eliminate combo if total digit sum is  ±14 from seed sum
        # Could not parse: eliminate combo if total digit sum is  ±13 from seed sum,eliminate combo if total digit sum is  ±13 from seed sum
        # Could not parse: Eliminate combos with same root sum as seed,Eliminate combos with same root sum as seed
        # Could not parse: "if combo contains same odd number of digits as seed, eliminate combo","if combo contains same odd number of digits as seed, eliminate combo"
        # Could not parse: "if combo contains same number of even digits as seed, eliminate combo","if combo contains same number of even digits as seed, eliminate combo"
        # Could not parse: "if combo contains 5 unique digits and total digit sum >25, 3 digits must match seed or else eliminate combo","if combo contains 5 unique digits and total digit sum >25, 3 digits must match seed or else eliminate combo"
        # Could not parse: "if combo contains more than 3 unique digits, it must also contain at least 1 cold digt, or else eliminate combo","if combo contains more than 3 unique digits, it must also contain at least 1 cold digt, or else eliminate combo"
        # Could not parse: the spread (max digit – min digit) difference from seed must be > 3 or eliminate combo, the spread (max digit – min digit) difference from seed must be > 3 or eliminate combo
        # Could not parse: "if all 5 digits in combo are >/=5, eliminate combo ","if all 5 digits in combo are >/=5, eliminate combo "
        # Could not parse: "if all five digits in combo are< /=4, eliminate combo","if all five digits in combo are< /=4, eliminate combo"
        # Could not parse: "if all 5 digits in combo are odd, eliminate combo","if all 5 digits in combo are odd, eliminate combo"
        # Could not parse: "if all 5 digits in combo are even, eliminate combo","if all 5 digits in combo are even, eliminate combo"
        # Could not parse: " If seed sum is 24 or 25 and combo digit sum is <19 or >25, eliminate combo."," If seed sum is 24 or 25 and combo digit sum is <19 or >25, eliminate combo."
        # Could not parse: seed sum >=26,"if seed sum is >/=26 and combo digit sum is <20 or >28, eliminate combo"
        # Could not parse: seed sum <=12,"if seed sum is </= 12 and combo digit sum <12 or >25, eliminate combo"
        # Could not parse: seed sum = 24-25,"if seed sum is 24-25 and combo digit sum is >19 or >25, eliminate combo"
        # Could not parse: seed sum = 22-23,"if seed sum = 22-23 and combo digit sum is <16 or >25, eliminate  combo"
        # Could not parse: seed sum = 19-21,"if seed sum = 19-21 and combo digit sum is <14 or >24, eliminate combo"
        # Could not parse: "If the digit sum of the combo equals the mirror of the seed sum, eliminate combo.","If the digit sum of the combo equals the mirror of the seed sum, eliminate combo."
        # Could not parse: seed sum = 16,"if seed sum =16, a combo digit sum is <12 and >20, eliminate combo"
        # Could not parse: "If no digit in the combo is a mirror of any digit in the seed, eliminate combo."
        # Could not parse: "If the digit sum of the combo equals the mirror of the seed sum, eliminate combo","If the digit sum of the combo equals the mirror of the seed sum, eliminate combo"
        # Could not parse: "if combo has ≥4 shared digits with seed and combo digit sum < 10, eliminate combo","if combo has ≥4 shared digits with seed and combo digit sum < 10, eliminate combo"
        # Could not parse: "if combo has  ≥3 shared digits with seed and combo digit  sum < 18, eliminate combo","if combo has  ≥3 shared digits with seed and combo digit  sum < 18, eliminate combo"
        # Could not parse: "if combo has ≥3 shared digits with seed and combo digit sum < 17, eliminate combo","if combo has ≥3 shared digits with seed and combo digit sum < 17, eliminate combo"
        # Could not parse: "if combo has ≥3 shared digits with seed and combo digit sum < 16, eliminate combo ","if combo has ≥3 shared digits with seed and combo digit sum < 16, eliminate combo "
        # Could not parse: "if combo has ≥3 shared digits with seed and combo digit sum < 15, eliminate combo ","if combo has ≥3 shared digits with seed and combo digit sum < 15, eliminate combo "
        # Could not parse: "if combo has ≥3 shared digits with seed and combo digit sum < 14, eliminate combo","if combo has ≥3 shared digits with seed and combo digit sum < 14, eliminate combo"
        # Could not parse: "if combo has  ≥3 shared digits with seed and combo digit sum < 13, eliminate combo ","if combo has  ≥3 shared digits with seed and combo digit sum < 13, eliminate combo "
        # Could not parse: "If combo has  ≥3 shared digits with seed and combo digit  sum < 12, eliminate combo","If combo has  ≥3 shared digits with seed and combo digit  sum < 12, eliminate combo"
        # Could not parse: "if combo has ≥3 shared digits with seed and combo digit sum < 11, eliminate combo","if combo has ≥3 shared digits with seed and combo digit sum < 11, eliminate combo"
        # Could not parse: "if combo has ≥3 shared digits with seed and combo digit sum < 10, eliminate combo","if combo has ≥3 shared digits with seed and combo digit sum < 10, eliminate combo"
        # Could not parse: "if combo has ≥2 shared digits with seed and combo digit sum < 14, eliminate combo","if combo has ≥2 shared digits with seed and combo digit sum < 14, eliminate combo"
        # Could not parse: "if combo has ≥2 shared digits with seed and combo digit sum < 13, eliminate combo","if combo has ≥2 shared digits with seed and combo digit sum < 13, eliminate combo"
        # Could not parse: "if combo has ≥2 shared digits with seed and combo digit sum < 12, eliminate combo ","if combo has ≥2 shared digits with seed and combo digit sum < 12, eliminate combo "
        # Could not parse: "if combo has ≥2 shared digits with seed and combo digit sum < 11, eliminate combo","if combo has ≥2 shared digits with seed and combo digit sum < 11, eliminate combo"
        # Could not parse: "if combo has ≥2 shared digits with seed and combo digit  sum < 10, eliminate combo","if combo has ≥2 shared digits with seed and combo digit  sum < 10, eliminate combo"
        # Could not parse: "if combo has ≥1 shared digits with seed and combo digit sum < 12, eliminate combo","if combo has ≥1 shared digits with seed and combo digit sum < 12, eliminate combo"
        # Could not parse: "if combo has ≥1 shared digits with seed and combo digit sum < 11, eliminate combo","if combo has ≥1 shared digits with seed and combo digit sum < 11, eliminate combo"
        # Could not parse: "if combo has ≥1 shared digits with seed and combo digit  sum < 10, eliminate combo"
        # Could not parse: "If a combo contains both a digit and its mirror (0/5, 1/6, 2/7, 3/8, 4/9), eliminate it."
        # Could not parse: "If any digit in combo equals the mirror of the last digit of the seed sum, eliminate combo.
        if all(d in seed_digits for d in [0, 8]) and sum(combo_digits) % 2 == 0:
        eliminate = True

        if not eliminate:
            survivors.append(combo)

    st.sidebar.markdown("### 📋 Filter-by-Filter Summary")
        for entry in elimination_history:
            st.sidebar.markdown(f"**{entry['Filter']}**: Removed `{entry['Removed']}`, Remaining `{entry['Remaining']}`")

    st.write(f"Final remaining combos: {len(session_pool)}")
    with st.expander("View remaining combinations"):
        for c in session_pool[:100]:
            st.write(c)
