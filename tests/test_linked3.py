import random
import pytest
from synpyg.tree.linked3 import Base, Node, End


def check(root: Node):
    """Assert every structural invariant of the tree rooted at `root`."""
    tail = root._tail
    # forward walk: must reach tail, no cycles
    seq, seen, cur = [], set(), root
    while True:
        assert id(cur) not in seen, "cycle in _next chain"
        seen.add(id(cur))
        seq.append(cur)
        if cur is tail:
            break
        assert cur._next is not None, "_next chain broken before tail"
        cur = cur._next
    # backward walk must mirror the forward walk
    back, cur = [], tail
    while cur is not root:
        back.append(cur)
        assert cur._prev is not None, "_prev chain broken"
        assert cur._prev._next is cur, "prev/next mismatch"
        cur = cur._prev
    back.append(root)
    assert back[::-1] == seq or all(a is b for a, b in zip(back[::-1], seq))
    assert len(back) == len(seq)
    # parent bookkeeping matches nesting
    stack = [root]
    for item in seq[1:-1]:
        if isinstance(item, End):
            assert item._parent is stack[-1]
            stack.pop()
        else:
            assert item._parent is stack[-1]
            if isinstance(item, Node):
                stack.append(item)
    assert stack == [root]


def test_empty():
    p = Node()
    assert list(p) == [] and p.first_child() is None and p.last_child() is None
    check(p)


def test_append_multiple():
    p, a, b, c = Node(), Base(), Base(), Base()
    p.append_child(a, b, c)
    assert list(p) == [a, b, c]
    check(p)


def test_append_multiple_nodes_with_subtrees():
    p, a, b = Node(), Node(), Node()
    x, y = Base(), Base()
    a.append_child(x)
    b.append_child(y)
    p.append_child(a, b)
    assert list(p) == [a, b] and list(a) == [x] and list(b) == [y]
    check(p)


def test_insert_before_and_first_last():
    p, a, b, c = Node(), Base(), Base(), Base()
    p.append_child(a, c)
    p.insert_before(c, b)
    assert list(p) == [a, b, c]
    assert p.first_child() is a and p.last_child() is c
    check(p)


def test_insert_before_true_nonempty_and_empty():
    p, a, b = Node(), Base(), Base()
    p.insert_before(True, a)  # empty: should just append
    p.insert_before(True, b)  # before first child
    assert list(p) == [b, a]
    check(p)


def test_move_before_immediate_next_sibling_leaf():
    p, a, b = Node(), Base(), Base()
    p.append_child(a, b)
    p.insert_before(b, a)  # a is already right before b
    assert list(p) == [a, b]
    check(p)


def test_move_before_immediate_next_sibling_node():
    p, a, b = Node(), Node(), Base()
    p.append_child(a, b)
    p.insert_before(b, a)
    assert list(p) == [a, b]
    check(p)


def test_reorder_existing_children():
    p, a, b, c = Node(), Base(), Base(), Base()
    p.append_child(a, b, c)
    p.append_child(a)
    assert list(p) == [b, c, a]
    check(p)


def test_move_between_parents():
    p, q, a = Node(), Node(), Node()
    x = Base()
    a.append_child(x)
    p.append_child(a)
    q.append_child(a)
    assert list(p) == [] and list(q) == [a] and list(a) == [x]
    check(p)
    check(q)


def test_cycle_self():
    a = Node()
    with pytest.raises(RuntimeError):
        a.append_child(a)
    check(a)


def test_cycle_descendant():
    a, b, c = Node(), Node(), Node()
    a.append_child(b)
    b.append_child(c)
    with pytest.raises(RuntimeError):
        c.append_child(a)
    check(a)


def test_wrong_parent_rejected():
    p, q, a = Node(), Node(), Base()
    q.append_child(a)
    with pytest.raises(RuntimeError):
        p.insert_before(a, Base())


def test_remove_and_remove_children():
    p, a, b, c = Node(), Base(), Node(), Base()
    p.append_child(a, b, c)
    b.remove()
    assert list(p) == [a, c] and b._parent is None
    check(p)
    p.remove_children()
    assert list(p) == []
    check(p)


def test_siblings():
    p, a, b, c = Node(), Base(), Node(), Base()
    p.append_child(a, b, c)
    assert a.next_sibling() is b and b.next_sibling() is c
    assert c.next_sibling() is None
    assert a.previous_sibling() is None
    assert b.previous_sibling() is a and c.previous_sibling() is b


def test_ancestors_and_root():
    r, m, leaf = Node(), Node(), Base()
    r.append_child(m)
    m.append_child(leaf)
    assert list(leaf.ancestors()) == [m, r]
    assert leaf.root_ancestor() is r


def test_iteration_tolerates_removing_current():
    p = Node()
    kids = [Base() for _ in range(5)]
    p.append_child(*kids)
    for k in p:
        k.remove()
    assert list(p) == []
    check(p)


@pytest.mark.parametrize("seed", range(25))
def test_random_operations(seed):
    rng = random.Random(seed)
    root = Node()
    nodes = [root] + [Node() if rng.random() < 0.5 else Base() for _ in range(15)]
    containers = [n for n in nodes if isinstance(n, Node)]
    for _ in range(200):
        parent = rng.choice(containers)
        n = rng.choice(nodes[1:])
        op = rng.random()
        if op < 0.15:
            n.remove()
        else:
            kids = list(parent)
            which = rng.choice(kids) if kids and rng.random() < 0.6 else None
            batch = [n] + ([rng.choice(nodes[1:])] if rng.random() < 0.3 else [])
            if len({id(x) for x in batch}) < len(batch):
                batch = [n]
            try:
                parent.insert_before(which, *batch)
            except RuntimeError:
                pass  # cycle / not-a-child are legal rejections
        # only check the tree reachable from root; detached subtrees are checked too
        check(root)
        for c in containers:
            if c is not root and c._parent is None:
                check(c)
