import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from rule_parser import parse_rules


def load_lines():
    with open('filter intent summary.txt') as f:
        return [ln.strip().strip('"') for ln in f if ln.strip()]


def test_rule_count():
    lines = load_lines()
    rules = parse_rules(lines)
    assert len(rules) == len(lines)


def find_rule(rules, text):
    for r in rules:
        if text.lower() in r.text.lower():
            return r
    raise AssertionError(f"rule containing '{text}' not found")


def test_digit_sum_equals():
    lines = load_lines()
    rules = parse_rules(lines)
    rule = find_rule(rules, 'digit sum of the combination equals 1')
    assert rule.evaluate([0,0,0,0,1], [1,2,3,4,5])
    assert not rule.evaluate([0,0,0,0,2], [1,2,3,4,5])


def test_seed_contains_even_sum():
    lines = load_lines()
    rules = parse_rules(lines)
    rule = find_rule(rules, '4, 5, 6, 8')
    assert rule.evaluate([1,1,1,1,2], [4,5,6,8,9])
    assert not rule.evaluate([1,1,1,1,1], [4,5,6,8,9])


def test_seed_includes_odd_sum():
    lines = load_lines()
    rules = parse_rules(lines)
    rule = find_rule(rules, '[1,2,6,8]')
    assert rule.evaluate([1,1,1,1,1], [1,2,6,8,0])
    assert not rule.evaluate([1,1,1,1,2], [1,2,6,8,0])


def test_sum_end_digits():
    lines = load_lines()
    rules = parse_rules(lines)
    rule = find_rule(rules, 'seed sum end digit is 7 and combo sum end digit is 8')
    assert rule.evaluate([1,1,1,1,4], [1,2,2,1,1])
    assert not rule.evaluate([1,1,1,1,4], [2,2,2,2,2])
