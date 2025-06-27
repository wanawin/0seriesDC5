
# ==============================
# Sidebar Combo Count Ribbon (Top)
# ==============================
if seed:
    st.sidebar.markdown("## 🎯 Remaining Combos")
    st.sidebar.markdown(f"### `{len(session_pool)}` remaining after filters")

import streamlit as st
import os, unicodedata, re
from itertools import product, combinations, groupby

# Optional: logipar import (placeholder)
try:
    import logipar
    LOGIPAR_AVAILABLE = True
except ImportError:
    LOGIPAR_AVAILABLE = False

# Helper functions for parsing, normalizing, applying filters...
# (Use your original helper functions unchanged here)

# Example extended filter logic inside your main app:
def apply_additional_filters(session_pool, label, logic, seed):
    removed = []
    if 'name type logic' in label.lower():
        return session_pool, []

    # Handle digit sum equals X
    m_exact_sum = re.search(r'digit sum.*equals\s*(\d+)', logic, re.IGNORECASE)
    if m_exact_sum:
        target = int(m_exact_sum.group(1))
        keep = [c for c in session_pool if sum(int(d) for d in c) != target]
        removed = [c for c in session_pool if sum(int(d) for d in c) == target]
        return keep, removed

    # Handle: seed contains digit X and combo must contain Y or Z
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

    # Handle consecutive digits >= N
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

    # Optional: try logipar to evaluate logic expressions
    if LOGIPAR_AVAILABLE:
        try:
            parsed = logipar.parse(logic)
            keep = [c for c in session_pool if not parsed.evaluate({'combo': c})]
            removed = [c for c in session_pool if parsed.evaluate({'combo': c})]
            return keep, removed
        except:
            pass

    return session_pool, []

# In the filter loop section of your app:
# session_pool is your active list of combos
# Replace st.warning(...) fallback with:

keep, removed = apply_additional_filters(session_pool, label, logic, seed)
if len(removed) > 0:
    session_pool = keep
    st.write(f"Filter '{label}' removed {len(removed)} combos.")
else:
    st.warning(f"Could not automatically apply filter logic for: '{label}'")

# End of app logic...

# ==============================
# Track and Display Per-Filter Eliminations
# ==============================
elimination_history = []

# In your filter loop (replace or extend logic as needed):
# After applying a filter and updating session_pool:
elimination_history.append({
    'Filter': label,
    'Removed': len(removed),
    'Remaining': len(session_pool)
})

# At the bottom or in a sidebar expander
if elimination_history:
    st.sidebar.markdown("### 📋 Filter-by-Filter Summary")
    for entry in elimination_history:
        st.sidebar.markdown(
            f"**{entry['Filter']}**: Removed `{entry['Removed']}`, Remaining `{entry['Remaining']}`"
        )
