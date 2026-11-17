from .canvas import Canvas
from .track.track import Track


class RootTrack(Track):
    def __init__(self, root: "Root", **kwargs):
        super().__init__(**kwargs)
        self.root = root


class Root:

    def __init__(self):
        self.fps = 24.0
        self.size = (480, 270)
        self.view_box = (-4, 2.25, 4, -2.25)
        self.start = 0.0
        self.track = RootTrack(self)

    def canvas(self, **kwargs):
        self._canvas = c = Canvas(
            fps=self.fps,
            width=self.size[0],
            height=self.size[1],
            view_box=self.view_box,
            **kwargs
        )
        return c

    # track
    def __matmul__(self, offset: float):
        return self.track.sub(offset * 1.0)
