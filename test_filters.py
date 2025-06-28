import filters


def test_sum_equals_one_eliminated():
    combo = [0,0,0,0,1]
    seed = [1,2,3,4,5]
    assert filters.should_eliminate(combo, seed)


def test_even_sum_elimination_when_seed_has_4568():
    combo_even = [0,1,2,3,4]  # sum=10 even
    seed = [4,5,6,8,1]
    assert filters.should_eliminate(combo_even, seed)


def test_non_eliminated_pair_from_search():
    seed = [0,0,0,0,0]
    combo = [1,1,1,3,5]
    assert not filters.should_eliminate(combo, seed)


def test_mirror_pair_elimination():
    combo = [0,5,1,2,3]  # contains 0 and 5 mirrors
    seed = [1,2,3,4,5]
    assert filters.should_eliminate(combo, seed)
