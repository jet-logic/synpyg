from typing import Generator, Union, Any, Self


class Node:

    _next: Union["Self", None] = None
    _parent: Union["Self", None] = None
    # Node
    _first: Union["Self", None]

    def __init__(self):
        self._first = None
        self._next = None
        self._parent = None

    def detach(self):
        parent = self._parent
        if parent is not None:
            cur = parent._first
            prev = None
            while cur:
                if cur is self:
                    if prev:
                        prev._next = cur._next
                    else:
                        parent._first = cur._next
                    break
                prev = cur
                cur = cur._next
        self._parent = self._next = None
        return self

    def parent(self):
        return self._parent

    def next_sibling(self):
        return self._next

    def previous_sibling(self):
        p = self._parent
        if p is not None:
            return p.prior_child(self)

    def root_ancestor(self):
        top = self._parent
        while top:
            if cur := top._parent:
                top = cur
            else:
                return top

    def ancestors(self):
        top = self._parent
        while top:
            yield top
            top = top._parent

    def self_and_ancestors(self):
        top: Node | None = self
        while top:
            yield top
            top = top._parent

    def place_after(self, node: "Self"):
        assert self is not node
        next = self.next_sibling()
        node.detach()
        node._parent = self._parent
        node._next = next
        self._next = node

    def place_before(self, node: "Self"):
        prev = self.previous_sibling()
        if prev:
            prev.place_after(node)
        else:
            parent = self._parent
            if parent:
                parent.prepend_child(node)

    def replace_with(self, node: "Self"):
        parent = self._parent
        if parent:
            parent.replace_child(node, self)

    def remove(self):
        return self.detach()

    # Node

    def last_child(self):
        cur = self._first
        if cur:
            while cur._next:
                assert cur._parent is self, f"{cur._parent} {self}"
                cur = cur._next
        return cur

    def first_child(self):
        return self._first

    def prior_child(self, child: "Node"):
        cur = self._first
        while cur:
            next = cur._next
            if next is child:
                return cur
            cur = next

    def append_child(self, child: "Self"):
        child.detach()
        last = self.last_child()
        child._parent = self
        if last:
            last._next = child
        else:
            self._first = child

    def prepend_child(self, child: "Self"):
        child.detach()
        child._next = self._first
        child._parent = self
        self._first = child

    def __iter__(self) -> Generator[Self, Any, None]:
        cur = self._first
        while cur:
            assert cur._parent is not cur
            assert cur._parent is self
            next = cur._next
            yield cur
            cur = next

    def remove_child(self, child: "Node"):
        assert child._parent is self
        child.detach()

    def replace_child(self, new: "Self", old: "Self"):
        new.detach()
        prev = self.prior_child(old)
        next = old.next_sibling()
        old.detach()
        new._parent = self
        new._next = next
        if prev:
            prev._next = new
        else:
            self._first = new

    def remove_children(self):
        while x := self.first_child():
            x.detach()

    def enum_descend(self):
        p = self._parent
        if p:
            yield from p.enum_descend()
        yield self

    def enum_ascend(self):
        top = self
        while top:
            yield top
            top = top._parent

    def enum_depth_first(self):
        for sub in self:
            yield sub
            yield from sub
