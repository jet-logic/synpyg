from typing import Optional, Union


class Base:
    _next: Union["End", "Node", "Base", None] = None
    _prev: Union["End", "Node", "Base", None] = None
    _parent: Optional["Node"] = None

    def __init__(self):
        self._next = self._prev = self._parent = None

    @property
    def _end(self) -> Union["End", "Node", "Base"]:
        return self

    @property
    def _start(self) -> Union["End", "Node", "Base"]:
        return self

    def next_sibling(self):
        next = self._end._next
        if next:
            if isinstance(next, End):
                assert next._parent is self._parent, f"{next._parent} {self._parent}"
                return None
            return next

    def previous_sibling(self):
        prev = self._prev
        if prev:
            if isinstance(prev, End):
                return prev._start
            elif self._parent is prev:
                return None
            return prev

    def _link_next(self, node: "Base"):
        if node is self:
            raise RuntimeError(f"same node")
        elif node is None:
            self._next = None
        else:
            self._next = node
            node._prev = self
            # assert self._parent is node._parent or node._parent is self , f"{self._parent} {node._parent}"

    def _detach(self):
        end = self._end
        prev = self._prev
        next = end._next
        if prev:
            assert next
            prev._link_next(next)
        self._prev = end._next = self._parent = None
        return self

    def _attach(self, prev: "Base", next: "Base", parent: "Node"):
        start = self._start
        end = self._end
        self._parent = parent
        prev._link_next(start)
        end._link_next(next)

    def ancestors(self):
        top = self._parent
        while top:
            yield top
            top = top._parent

    def root_ancestor(self):
        top = self._parent
        while top:
            cur = top._parent
            if cur:
                top = cur
            else:
                return top

    def root_ancestor_or_self(self):
        top = self
        while top._parent is not None:
            top = top._parent
        return top

    def remove(self):
        return self._detach()


class Node(Base):
    # _tail: "End" = None

    def __init__(self):
        self._tail = self._next = End(self)
        self._prev = self._parent = None

    @property
    def _end(self) -> Union["End", "Node", "Base"]:
        return self._tail

    def __iter__(self):
        cur = self._next
        end = self._tail
        while cur:
            if cur is end:
                break
            assert cur._parent is not cur
            assert cur._parent is self
            next = cur._end._next
            yield cur
            cur = next

    def insert_before(self, which: Base | bool | None, *nodes: Base):
        if which is True:
            child = self.first_child() or self._end
        elif which:
            child = which
        else:
            child = self._end
        if child._parent is not self:
            raise RuntimeError("child not found")

        _nodes = [n for n in nodes if n is not child]
        for n in _nodes:
            if n is self or any(a is n for a in self.ancestors()):
                raise RuntimeError("cannot insert a node into itself or its descendant")
        for n in _nodes:
            n._detach()

        prev = child._prev
        for n in _nodes:
            n._attach(prev, child, self)
            prev = n._end

    def append_child(self, *nodes: Base):
        self.insert_before(self._end, *nodes)

    def first_child(self):
        #  P  c ... ^P
        #  P  C ^C ... ^P
        #  P ^P
        next = self._next
        end = self._end
        if next is end:
            return None
        if next is None:
            raise RuntimeError(f"next expected")  # pragma: no cover
        if next._parent is not self:
            raise RuntimeError(f"unexpected parent")  # pragma: no cover
        assert not isinstance(next, End)
        return next

    def last_child(self):
        #  P  ... c  ^P
        #  P  ... C ^C  ^P
        #  P ^P
        prev = self._end._prev
        if prev is not self:
            assert prev is not None
            return prev._start

    def remove_children(self):
        while x := self.first_child():
            x._detach()

    def children(self):
        cur = self._next
        end = self._tail
        while cur:
            if cur is end:
                break
            assert cur._parent is not cur
            assert cur._parent is self
            next = cur._end._next
            yield cur
            cur = next


class End(Base):
    _next: Union["End", "Node", Base, None]
    _prev: Union["End", "Node", Base, None]  # Should have no None
    _parent: Optional[Node]  # Should have no Optional

    def __init__(self, parent: Node):
        self._parent = parent
        self._prev = parent
        self._next = None

    @property
    def _start(self) -> Union["End", "Node", "Base"]:
        assert self._parent
        return self._parent

    def previous_sibling(self):
        # return self._parent.previous_sibling()
        return self._start.previous_sibling()
