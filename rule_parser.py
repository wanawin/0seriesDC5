import re
from dataclasses import dataclass
from typing import Callable, List

@dataclass
class Rule:
    text: str
    func: Callable[[List[int], List[int]], bool]

    def evaluate(self, combo: List[int], seed: List[int]) -> bool:
        return self.func(combo, seed)

def parse_rules(lines: List[str]) -> List[Rule]:
    """Parse textual rules into executable Rule objects."""
    rules: List[Rule] = []
    for line in lines:
        raw = line.strip().strip('"')
        if not raw:
            continue
        rule = None
        # Pattern: digit sum equals N
        m = re.search(r"digit sum of (?:the )?combination equals (\d+)", raw, re.I)
        if m:
            target = int(m.group(1))
            rule = Rule(raw, lambda c, s, t=target: sum(c) == t)
        # Pattern: seed contains digits -> eliminate even sums
        if rule is None:
            m = re.search(r"seed contains.*?([0-9, ]+).*eliminate all even sum", raw, re.I)
            if m:
                digits = [int(d) for d in re.findall(r"\d", m.group(1))]
                rule = Rule(raw, lambda c, s, d=digits: all(x in s for x in d) and sum(c) % 2 == 0)
        # Pattern: seed includes digits -> eliminate odd sums
        if rule is None:
            if "odd-sum" in raw.lower():
                m = re.search(r"\[(\d+(?:,\d+)*)\]", raw)
                if m:
                    digits = [int(d) for d in m.group(1).split(',')]
                    rule = Rule(
                        raw,
                        lambda c, s, d=digits: all(x in s for x in d) and sum(c) % 2 == 1,
                    )
        # Pattern: seed sum end digit and combo sum end digit
        if rule is None:
            m = re.search(r"seed sum end digit is (\d).*combo sum end digit is (\d)", raw, re.I)
            if m:
                sd, cd = int(m.group(1)), int(m.group(2))
                rule = Rule(raw, lambda c, s, sd=sd, cd=cd: sum(s) % 10 == sd and sum(c) % 10 == cd)
        # Pattern: combo has >=N shared digits with seed and sum < M
        if rule is None:
            m = re.search(r"combo has .*?(\d+) shared digits.*sum < ?(\d+)", raw, re.I)
            if m:
                n, mval = int(m.group(1)), int(m.group(2))
                rule = Rule(raw, lambda c, s, n=n, mval=mval: len(set(c) & set(s)) >= n and sum(c) < mval)
        # Default rule if no pattern matched
        if rule is None:
            rule = Rule(raw, lambda c, s: False)
        rules.append(rule)
    return rules
