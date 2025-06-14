# DC-5 Manual Filter Functions (Python Version for GitHub)

from collections import Counter

def is_quint(combo):
    """Eliminate if all 5 digits are the same."""
    return len(set(combo)) == 1

def is_quad(combo):
    """Eliminate if 4 digits are the same."""
    return sorted(Counter(combo).values()) == [1, 4]

def is_triple(combo):
    """Eliminate if 3 digits are the same and the other two are unique."""
    counts = list(Counter(combo).values())
    return 3 in counts and counts.count(3) == 1 and len(counts) == 3

def is_mild_double_double(combo):
    """Eliminate if one digit appears twice and two others once (4 total digits).
    Does NOT eliminate basic doubles (like AABCD).
    """
    c = Counter(combo)
    return sorted(c.values()) == [1, 1, 2] and len(set(combo)) == 4

def is_double_double(combo):
    """Eliminate if two digits appear twice and one other once (3 unique digits)."""
    return sorted(Counter(combo).values()) == [1, 2, 2]

def all_low_digits(combo):
    return all(int(d) <= 3 for d in combo)

def digit_spread_lt_4(combo):
    digits = list(map(int, combo))
    return max(digits) - min(digits) < 4

def two_or_more_primes(combo):
    primes = {'2', '3', '5', '7'}
    return sum(1 for d in combo if d in primes) >= 2

def sum_ends_in_0_or_5(combo):
    return sum(map(int, combo)) % 5 == 0

def has_3_consecutive(combo):
    digits = sorted(map(int, combo))
    for i in range(len(digits) - 2):
        if digits[i+1] == digits[i] + 1 and digits[i+2] == digits[i] + 2:
            return True
    return False

def two_or_more_high(combo):
    return sum(1 for d in combo if int(d) >= 8) >= 2

def mirror_count_lt_2(combo, mirror_digits):
    return sum(1 for d in combo if d in mirror_digits) < 2

def vtrac_group_saturation(combo, group_map):
    mapped = [group_map[d] for d in combo]
    return any(mapped.count(g) >= 4 for g in set(mapped))

def all_same_vtrac_group(combo, group_map):
    mapped = [group_map[d] for d in combo]
    return len(set(mapped)) == 1

def only_two_vtrac_groups(combo, group_map):
    mapped = [group_map[d] for d in combo]
    return len(set(mapped)) == 2

def trailing_digit_equals_mirror_sum(combo, mirror_sum):
    return combo[-1] == str(mirror_sum)[-1]

def sum_category_transition_filter(prev_sum_cat, current_sum_cat):
    transitions = {
        ("Mid", "Low"), ("Low", "High"), ("Very Low", "Mid"),
        ("Mid", "Very Low"), ("High", "Low")
    }
    return (prev_sum_cat, current_sum_cat) in transitions

def reversible_mirror_pair_block(prev_draw, curr_draw, mirror_map):
    prev_pairs = [prev_draw[i] + prev_draw[i+1] for i in range(4)]
    mirrors = [mirror_map[p[0]] + mirror_map[p[1]] for p in prev_pairs]
    mirrors += [m[::-1] for m in mirrors]
    curr_pairs = [curr_draw[i] + curr_draw[i+1] for i in range(4)]
    return any(p in curr_pairs for p in mirrors)

def strict_mirror_pair_block(prev_draw, curr_draw, mirror_map):
    prev_pairs = [prev_draw[i] + prev_draw[i+1] for i in range(4)]
    mirrors = [mirror_map[p[0]] + mirror_map[p[1]] for p in prev_pairs]
    curr_pairs = [curr_draw[i] + curr_draw[i+1] for i in range(4)]
    return any(m in curr_pairs for m in mirrors)

def loose_mirror_digit_block(prev_draw, curr_draw, mirror_map):
    mirror_digits = set(mirror_map[d] for pair in [prev_draw[i] + prev_draw[i+1] for i in range(4)] for d in pair)
    return any(d in mirror_digits for d in curr_draw)

def three_or_more_digits_gt_5(combo):
    return sum(1 for d in combo if int(d) > 5) >= 3
