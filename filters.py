"""Filtering rules parsed from filter intent summary.txt.
Each line of the text file is converted into a Python
condition. Rules are executed sequentially in the
order of appearance in the text file.
"""

import re
from typing import Callable, List

# mapping for mirror digits
MIRROR_MAP = {0:5, 1:6, 2:7, 3:8, 4:9,
              5:0, 6:1, 7:2, 8:3, 9:4}

def digit_sum(nums: List[int]) -> int:
    return sum(nums)

def mirror_number(n: int) -> int:
    return int(''.join(str(MIRROR_MAP[int(d)]) for d in str(n)))

def contains_digits(container: List[int], digits: List[int]) -> bool:
    return all(d in container for d in digits)

def shared_digit_count(a: List[int], b: List[int]) -> int:
    return sum(min(a.count(d), b.count(d)) for d in set(a))

def parse_rules(filename: str = "filter intent summary.txt") -> List[Callable[[List[int], List[int]], bool]]:
    rules: List[Callable[[List[int], List[int]], bool]] = []
    with open(filename, 'r') as f:
        for line in f:
            text = line.strip().lower()
            if not text:
                continue
            cond: Callable[[List[int], List[int]], bool] | None = None

            # digit sum equals n
            m = re.search(r'digit sum[^\d]*(\d+)', text)
            if m and "equals" in text:
                value = int(m.group(1))
                def _make(value=value):
                    return lambda combo, seed: digit_sum(combo) == value
                cond = _make()
            # seed contains digits -> eliminate even/odd sums
            elif "contains" in text and ("even" in text or "odd" in text):
                part = text.split('contains',1)[1].split('eliminate')[0]
                digits = [int(d) for d in re.findall(r'\d', part)]
                if digits:
                    parity = 0 if "even" in text else 1
                    def _make(digits=digits, parity=parity):
                        return lambda combo, seed: contains_digits(seed, digits) and digit_sum(combo) % 2 == parity
                    cond = _make()
            # seed sum end digit rule
            elif "seed sum end digit" in text and "combo sum end digit" in text:
                sm = re.search(r'seed sum end digit is (\d)', text)
                cm = re.search(r'combo sum end digit is (\d)', text)
                if sm and cm:
                    sdig, cdig = int(sm.group(1)), int(cm.group(1))
                    def _make(sdig=sdig, cdig=cdig):
                        return lambda combo, seed: digit_sum(seed) % 10 == sdig and digit_sum(combo) % 10 == cdig
                    cond = _make()
            # mirror of seed sum
            elif "mirror of the seed sum" in text:
                def _mirror():
                    return lambda combo, seed: digit_sum(combo) == mirror_number(digit_sum(seed))
                cond = _mirror()
            # combo contains both a digit and its mirror
            elif "both a digit and its mirror" in text:
                def _both_mirror():
                    return lambda combo, seed: any((d in combo and MIRROR_MAP[d] in combo) for d in range(10))
                cond = _both_mirror()
            # mirror of seed digits absent
            elif "mirror digit" in text and "not contain" in text:
                def _missing_mirror():
                    seed_mirrors = {MIRROR_MAP[d] for d in range(10)}
                    return lambda combo, seed, mirrors=seed_mirrors: not any(d in combo for d in [MIRROR_MAP[int(x)] for x in map(int, seed)])
                cond = _missing_mirror()

            if cond is None:
                cond = lambda combo, seed: False
            rules.append(cond)
    return rules

# Pre-parse rules on import
RULES = parse_rules()

def should_eliminate(combo: List[int], seed: List[int]) -> bool:
    """Return True if any rule triggers elimination."""
    for rule in RULES:
        if rule(combo, seed):
            return True
    return False
