import random
import unittest

from synpyg.tree.linked3 import Base, Node, End


class LinkedTreeTest(unittest.TestCase):
    def check(self, root: Node):
        """Assert every structural invariant of the tree rooted at `root`."""
        tail = root._tail

        # forward walk: must reach tail, no cycles
        seq, seen, cur = [], set(), root
        while True:
            self.assertNotIn(id(cur), seen, "cycle in _next chain")
            seen.add(id(cur))
            seq.append(cur)
            if cur is tail:
                break
            self.assertIsNotNone(cur._next, "_next chain broken before tail")
            cur = cur._next

        # backward walk must mirror the forward walk
        back, cur = [], tail
        while cur is not root:
            back.append(cur)
            self.assertIsNotNone(cur._prev, "_prev chain broken")
            self.assertIs(cur._prev._next, cur, "prev/next mismatch")
            cur = cur._prev
        back.append(root)
        self.assertEqual(len(back), len(seq))
        self.assertTrue(all(a is b for a, b in zip(back[::-1], seq)))

        # parent bookkeeping matches nesting
        stack = [root]
        for item in seq[1:-1]:
            if isinstance(item, End):
                self.assertIs(item._parent, stack[-1])
                stack.pop()
            else:
                self.assertIs(item._parent, stack[-1])
                if isinstance(item, Node):
                    stack.append(item)
        self.assertEqual(len(stack), 1)
        self.assertIs(stack[0], root)

    def test_empty(self):
        p = Node()
        self.assertEqual(list(p), [])
        self.assertIsNone(p.first_child())
        self.assertIsNone(p.last_child())
        self.check(p)

    def test_append_multiple(self):
        p, a, b, c = Node(), Base(), Base(), Base()
        p.append_child(a, b, c)
        self.assertEqual(list(p), [a, b, c])
        self.check(p)

    def test_append_multiple_nodes_with_subtrees(self):
        p, a, b = Node(), Node(), Node()
        x, y = Base(), Base()
        a.append_child(x)
        b.append_child(y)
        p.append_child(a, b)
        self.assertEqual(list(p), [a, b])
        self.assertEqual(list(a), [x])
        self.assertEqual(list(b), [y])
        self.check(p)

    def test_insert_before_and_first_last(self):
        p, a, b, c = Node(), Base(), Base(), Base()
        p.append_child(a, c)
        p.insert_before(c, b)
        self.assertEqual(list(p), [a, b, c])
        self.assertIs(p.first_child(), a)
        self.assertIs(p.last_child(), c)
        self.check(p)

    def test_insert_before_true_nonempty_and_empty(self):
        p, a, b = Node(), Base(), Base()
        p.insert_before(True, a)  # empty: should just append
        p.insert_before(True, b)  # before first child
        self.assertEqual(list(p), [b, a])
        self.check(p)

    def test_move_before_immediate_next_sibling_leaf(self):
        p, a, b = Node(), Base(), Base()
        p.append_child(a, b)
        p.insert_before(b, a)  # a is already right before b
        self.assertEqual(list(p), [a, b])
        self.check(p)

    def test_move_before_immediate_next_sibling_node(self):
        p, a, b = Node(), Node(), Base()
        p.append_child(a, b)
        p.insert_before(b, a)
        self.assertEqual(list(p), [a, b])
        self.check(p)

    def test_reorder_existing_children(self):
        p, a, b, c = Node(), Base(), Base(), Base()
        p.append_child(a, b, c)
        p.append_child(a)
        self.assertEqual(list(p), [b, c, a])
        self.check(p)

    def test_move_between_parents(self):
        p, q, a = Node(), Node(), Node()
        x = Base()
        a.append_child(x)
        p.append_child(a)
        q.append_child(a)
        self.assertEqual(list(p), [])
        self.assertEqual(list(q), [a])
        self.assertEqual(list(a), [x])
        self.check(p)
        self.check(q)

    def test_cycle_self(self):
        a = Node()
        with self.assertRaises(RuntimeError):
            a.append_child(a)
        self.check(a)

    def test_cycle_descendant(self):
        a, b, c = Node(), Node(), Node()
        a.append_child(b)
        b.append_child(c)
        with self.assertRaises(RuntimeError):
            c.append_child(a)
        self.check(a)

    def test_wrong_parent_rejected(self):
        p, q, a = Node(), Node(), Base()
        q.append_child(a)
        with self.assertRaises(RuntimeError):
            p.insert_before(a, Base())

    def test_remove_and_remove_children(self):
        p, a, b, c = Node(), Base(), Node(), Base()
        p.append_child(a, b, c)
        b.remove()
        self.assertEqual(list(p), [a, c])
        self.assertIsNone(b._parent)
        self.check(p)
        p.remove_children()
        self.assertEqual(list(p), [])
        self.check(p)

    def test_siblings(self):
        p, a, b, c = Node(), Base(), Node(), Base()
        p.append_child(a, b, c)
        self.assertIs(a.next_sibling(), b)
        self.assertIs(b.next_sibling(), c)
        self.assertIsNone(c.next_sibling())
        self.assertIsNone(a.previous_sibling())
        self.assertIs(b.previous_sibling(), a)
        self.assertIs(c.previous_sibling(), b)

    def test_ancestors_and_root(self):
        r, m, leaf = Node(), Node(), Base()
        r.append_child(m)
        m.append_child(leaf)
        self.assertEqual(list(leaf.ancestors()), [m, r])
        self.assertIs(leaf.root_ancestor(), r)

    def test_iteration_tolerates_removing_current(self):
        p = Node()
        kids = [Base() for _ in range(5)]
        p.append_child(*kids)
        for k in p:
            k.remove()
        self.assertEqual(list(p), [])
        self.check(p)

    def test_random_operations(self):
        for seed in range(25):
            with self.subTest(seed=seed):
                self._random_operations(seed)

    def _random_operations(self, seed):
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
            self.check(root)
            for c in containers:
                if c is not root and c._parent is None:
                    self.check(c)


if __name__ == "__main__":
    unittest.main()
