
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

def apply_additional_filters(session_pool, label, logic, seed):
    removed = []
    if 'name type logic' in label.lower():
        return session_pool, []

    m_exact_sum = re.search(r'digit sum.*equals\s*(\d+)', logic, re.IGNORECASE)
    if m_exact_sum:
        target = int(m_exact_sum.group(1))
        keep = [c for c in session_pool if sum(int(d) for d in c) != target]
        removed = [c for c in session_pool if sum(int(d) for d in c) == target]
        return keep, removed

    m_exclusion = re.search(r'seed contains.*?(\d).*?combo.*?not contain.*?(\d).*?or.*?(\d)', logic, re.IGNORECASE)
    if m_exclusion:
        seed_digit = int(m_exclusion.group(1))
        exclude_1 = m_exclusion.group(2)
        exclude_2 = m_exclusion.group(3)
        seed_digits = [int(d) for d in seed if d.isdigit()]
        if seed_digit in seed_digits:
            keep = [c for c in session_pool if exclude_1 in c or exclude_2 in c]
            removed = [c for c in session_pool if exclude_1 not in c and exclude_2 not in c]
            return keep, removed

    m_consec = re.search(r'consecutive digits\s*[>=]+\s*(\d+)', logic, re.IGNORECASE)
    if m_consec:
        n = int(m_consec.group(1))
        keep, removed = [], []
        for c in session_pool:
            digits = sorted(int(d) for d in c)
            max_consec = max([len(list(g)) for k, g in groupby(enumerate(digits), lambda ix: ix[0] - ix[1])])
            if max_consec >= n:
                removed.append(c)
            else:
                keep.append(c)
        return keep, removed

    if LOGIPAR_AVAILABLE:
        try:
            parsed = logipar.parse(logic)
            keep = [c for c in session_pool if not parsed.evaluate({'combo': c})]
            removed = [c for c in session_pool if parsed.evaluate({'combo': c})]
            return keep, removed
        except:
            pass

    return session_pool, []

# Streamlit UI
st.title("DC-5 Midday Combo Filter App")

seed = st.sidebar.text_input("5-digit seed:")
method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])

uploaded = st.sidebar.file_uploader("Upload manual filters (.txt)", type=['txt'])
parsed_entries = []
if uploaded is not None:
    raw_text = uploaded.read().decode("utf-8", errors="ignore")
    parsed_entries, skipped = parse_manual_filters_txt(raw_text)
    st.sidebar.success(f"Loaded {len(parsed_entries)} filters")

if seed:
    combos_initial = generate_combinations(seed, method)
    session_pool = combos_initial.copy()
    elimination_history = []

    st.sidebar.markdown("## 🎯 Remaining Combos")
    st.sidebar.markdown(f"### `{len(session_pool)}` after filters")

    total_generated = len(combos_initial)
    total_eliminated = total_generated - len(session_pool)
    st.sidebar.markdown(f"**🔻 Eliminated:** `{total_eliminated}` ({round((total_eliminated / total_generated) * 100, 1)}%)")

    if parsed_entries:
        for idx, pf in enumerate(parsed_entries):
            label = pf['name']
            logic = pf.get('logic', '')
            show = st.sidebar.checkbox(f"{label}", key=f"filter_{idx}")
            if show:
                keep, removed = apply_additional_filters(session_pool, label, logic, seed)
                session_pool = keep
                elimination_history.append({
                    'Filter': label,
                    'Removed': len(removed),
                    'Remaining': len(session_pool)
                })

    if elimination_history:
        st.sidebar.markdown("### 📋 Filter-by-Filter Summary")
        for entry in elimination_history:
            st.sidebar.markdown(f"**{entry['Filter']}**: Removed `{entry['Removed']}`, Remaining `{entry['Remaining']}`")

    st.write(f"Final remaining combos: {len(session_pool)}")
    with st.expander("View remaining combinations"):
        for c in session_pool[:100]:
            st.write(c)
