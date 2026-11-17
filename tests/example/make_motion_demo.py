from synpyg.canvas import Canvas
from synpyg.layer import CircleLayer
from synpyg.track.track import Track
from synpyg.track.action import Add, Par, ParE, Seq, To

canvas = Canvas(
    version="1.2",
    width=960,
    height=540,
    fps=24,
    begin_time="0s",
    end_time="6.5s",
    view_box=(-8.0, 4.5, 8.0, -4.5),
)

# Background is a real SolidColorLayer from the project's Layer API.
background = canvas.add_solid_color_layer("Midnight blue background")
background.color = (0.035, 0.055, 0.10, 1.0)

# Three circles make the path and moving subject easy to read.
left_marker = canvas.add_circle_layer("Start marker")
left_marker.color = (0.20, 0.35, 0.52, 1.0)
left_marker.radius = 0.16
left_marker.feather = 0.0
left_marker.origin = (-2.4, 0.0)

right_marker = canvas.add_circle_layer("End marker")
right_marker.color = (0.20, 0.35, 0.52, 1.0)
right_marker.radius = 0.16
right_marker.feather = 0.0
right_marker.origin = (2.4, 0.0)

ball = canvas.add_circle_layer("Animated cyan ball")
ball.color = (0.10, 0.82, 0.88, 1.0)
ball.radius = 0.55
ball.feather = 0.0
ball.origin = (-2.4, 0.0)

# Convert the two parameters to Animated values, preserving their initial
# values at t=0 as the first waypoints.
position = ball.origin.as_animated()
radius = ball.radius.as_animated()

track = Track(hint_dur=1.0)
track << Seq(
    # 0.0s–1.5s: travel from the start marker toward the center.
    To(position, (-0.8, 0.0), dur=1.5),
    # 1.5s–3.5s: Par runs both child actions from the same start time.
    Par(
        To(position, (0.8, 0.0), dur=1.5),
        To(radius, 0.90, dur=2.0),
    ),
    # 3.5s–5.5s: ParE aligns both child actions at their end time.
    # The position move starts later (4.5s); the radius change starts at 3.5s.
    ParE(
        To(position, (2.4, 0.0), dur=1.0),
        To(radius, 0.55, dur=2.0),
    ),
    # 5.5s–6.5s: Add applies a delta to the current position (2.4 -> 1.2).
    Add(position, (-1.2, 0.0), dur=1.0),
)

canvas.save_xml("/tmp/motion_choreography.sif")
print(f"Wrote motion_choreography.sif; track ends at {track.current_time:g}s")
