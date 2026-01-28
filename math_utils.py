import pygame
from pygame.math import Vector2

# ===============================
# 2. UTILITY / MATH FUNCTIONS
# ===============================
def orthogonal_path(a: Vector2, b: Vector2, mouse: Vector2 = None) -> list[Vector2]:
    """
    Compute an orthogonal (L-shaped) path from point `a` to point `b`.

    If a and b are aligned horizontally or vertically, the path is just [b].
    Otherwise, choose a corner point to create an L-shaped path.

    If `mouse` is provided, the corner closest to the mouse is chosen.

    Args:
        a (Vector2): Start point
        b (Vector2): End point
        mouse (Vector2, optional): Reference point to choose bend direction

    Returns:
        List[Vector2]: List of points forming the path (bends + end)
    """
    # If a and b are aligned, no bend needed
    if a.x == b.x or a.y == b.y:
        return [b]

    # Possible corner points
    corner_hv = Vector2(b.x, a.y)  # horizontal then vertical
    corner_vh = Vector2(a.x, b.y)  # vertical then horizontal

    # Pick the corner closest to mouse, if given
    if mouse:
        dist_hv = (corner_hv - mouse).length_squared()
        dist_vh = (corner_vh - mouse).length_squared()
        corner = corner_hv if dist_hv < dist_vh else corner_vh
    else:
        corner = corner_hv

    # Return the corner followed by the final point
    return [corner, b]

def rotate_point(point: Vector2, angle_deg: float) -> Vector2:
    """
    Rotate a 2D vector by a given angle in degrees.

    Args:
        point (Vector2): Vector to rotate
        angle_deg (float): Rotation angle in degrees

    Returns:
        Vector2: Rotated vector
    """
    return point.rotate(angle_deg)

def nearest_point_on_segment(a: Vector2, b: Vector2, p: Vector2) -> Vector2:
    """
    Find the closest point on a line segment AB to point P.

    Args:
        a (Vector2): Segment start
        b (Vector2): Segment end
        p (Vector2): Reference point

    Returns:
        Vector2: Closest point on segment AB to P
    """
    ab = b - a
    if ab.length_squared() == 0:
        return a  # segment is a point
    t = max(0, min(1, (p - a).dot(ab) / ab.length_squared()))
    return a + ab * t

def clean_collinear_points(points: list[Vector2]) -> list[Vector2]:
    """
    Remove points in a polyline that are collinear with neighbors (horizontal/vertical).

    Args:
        points (list[Vector2]): Input list of points

    Returns:
        list[Vector2]: Cleaned list of points
    """
    if len(points) < 3:
        return points.copy()

    cleaned = [points[0]]
    for i in range(1, len(points)-1):
        prev = cleaned[-1]
        curr = points[i]
        nxt = points[i+1]
        # Skip if all three points are aligned horizontally or vertically
        if (prev.x == curr.x == nxt.x) or (prev.y == curr.y == nxt.y):
            continue
        cleaned.append(curr)
    cleaned.append(points[-1])
    return cleaned

def make_rect(a: Vector2, b: Vector2) -> pygame.Rect:
    """
    Create a pygame.Rect from two arbitrary points.

    Args:
        a (Vector2): First corner
        b (Vector2): Second corner

    Returns:
        pygame.Rect: Rectangle covering both points
    """
    x = min(a.x, b.x)
    y = min(a.y, b.y)
    w = abs(a.x - b.x)
    h = abs(a.y - b.y)
    return pygame.Rect(x, y, w, h)

