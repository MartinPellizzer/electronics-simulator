# TODO: ai refactoring done, now move on to manual refactoring
# new component types? ✅
# net highlighting? ✅
# selection modes? ✅
# copy/paste? ✅

import pygame
from pygame.math import Vector2
import copy

# ===============================
# 1. CONSTANTS & CONFIGURATION
# ===============================
GRID_SIZE = 40
ROTATION_STEP = 90
SNAP_RADIUS = 8

COMPONENT_PINS = {
    'resistor': [
        Vector2(-20, 0),
        Vector2(20, 0)
    ]
}

# ===============================
# UNDO/REDO
# ===============================
def take_snapshot(components, wires):
    """
    Return a deep copy of the world state for undo/redo.
    """
    return {
        'components': copy.deepcopy(components),
        'wires': copy.deepcopy(wires),
    }

def undo(undo_stack, redo_stack, components, wires):
    """
    Undo the last action.

    Returns:
        (components, wires)
    """
    if not undo_stack:
        return components, wires

    # Save current state to redo
    redo_stack.append(take_snapshot(components, wires))

    # Restore previous state
    state = undo_stack.pop()
    return copy.deepcopy(state['components']), copy.deepcopy(state['wires'])

def redo(undo_stack, redo_stack, components, wires):
    """
    Redo the last undone action.

    Returns:
        (components, wires)
    """
    if not redo_stack:
        return components, wires

    # Save current state to undo
    undo_stack.append(take_snapshot(components, wires))

    # Restore next state
    state = redo_stack.pop()
    return copy.deepcopy(state['components']), copy.deepcopy(state['wires'])

def record_undo(components, wires, undo_stack, redo_stack):
    undo_stack.append(take_snapshot(components, wires))
    redo_stack.clear()

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

# ===============================
# 3. COMPONENT HELPERS
# ===============================
def get_component_pins(comp: dict) -> list[Vector2]:
    """
    Return the world positions of all pins of a component.

    The component is defined by:
      - 'type': string, e.g., 'resistor'
      - 'pos': Vector2, world position of component center
      - 'rotation': float, rotation in degrees

    Steps:
      1. Get local pin positions from COMPONENT_PINS
      2. Rotate each pin by the component's rotation
      3. Offset each pin by the component's world position
      4. Return the list of world pin positions

    Args:
        comp (dict): Component dictionary

    Returns:
        List[Vector2]: World positions of component pins
    """
    pins_world = []
    local_pins = COMPONENT_PINS.get(comp['type'], [])

    for local_pin in local_pins:
        # Rotate pin relative to component center
        rotated_pin = rotate_point(local_pin, comp['rotation'])
        # Convert to world coordinates
        world_pin = comp['pos'] + rotated_pin
        pins_world.append(world_pin)

    return pins_world

# ===============================
# 4. SNAPPING FUNCTIONS
# ===============================
def snap_to_grid(pos: Vector2) -> Vector2:
    """
    Snap a position to the nearest grid point.

    Args:
        pos (Vector2): Original world position

    Returns:
        Vector2: Position snapped to nearest grid intersection
    """
    return Vector2(
        round(pos.x / GRID_SIZE) * GRID_SIZE,
        round(pos.y / GRID_SIZE) * GRID_SIZE
    )

def snap_to_pins(mouse_world: Vector2, components: list[dict], radius: float = SNAP_RADIUS) -> Vector2 | None:
    """
    Snap the mouse to the nearest component pin within a given radius.

    Args:
        mouse_world (Vector2): Mouse position in world coordinates
        components (list[dict]): List of components
        radius (float, optional): Maximum snapping distance (default SNAP_RADIUS)

    Returns:
        Vector2 | None: Closest pin world position, or None if no pin is nearby
    """
    closest = None
    min_dist2 = radius * radius  # use squared distance for efficiency

    for comp in components:
        for pin in get_component_pins(comp):
            d2 = (pin - mouse_world).length_squared()
            if d2 <= min_dist2:
                min_dist2 = d2
                closest = pin

    return closest

def snap_to_wire_points(mouse_world: Vector2, wires: list[dict], radius: float = SNAP_RADIUS) -> Vector2 | None:
    """
    Snap the mouse to the nearest existing wire point within a given radius.

    Args:
        mouse_world (Vector2): Mouse position in world coordinates
        wires (list[dict]): List of wires, each with 'points': list[Vector2]
        radius (float, optional): Maximum snapping distance (default SNAP_RADIUS)

    Returns:
        Vector2 | None: Nearest wire point, or None if none are nearby
    """
    closest = None
    min_dist2 = radius * radius

    for wire in wires:
        for pt in wire['points']:
            d2 = (pt - mouse_world).length_squared()
            if d2 <= min_dist2:
                min_dist2 = d2
                closest = pt

    return closest

# ===============================
# 5. WIRE HELPERS
# ===============================
def find_wire_segment_at_mouse(wires: list[dict], mouse_world: Vector2, radius: float = SNAP_RADIUS) -> tuple[dict, int, Vector2] | tuple[None, None, None]:
    """
    Find a wire segment under the mouse within a given radius.

    Args:
        wires (list[dict]): List of wires, each with 'points': list[Vector2]
        mouse_world (Vector2): Mouse position in world coordinates
        radius (float, optional): Maximum distance to detect segment (default SNAP_RADIUS)

    Returns:
        Tuple[dict, int, Vector2] | Tuple[None, None, None]:
            - wire dict
            - index of segment start point
            - closest point on segment
            Returns (None, None, None) if no segment is near the mouse
    """
    for wire in wires:
        points = wire['points']
        for i in range(len(points) - 1):
            a, b = points[i], points[i + 1]
            closest = nearest_point_on_segment(a, b, mouse_world)
            if (closest - mouse_world).length_squared() <= radius * radius:
                return wire, i, closest
    return None, None, None

def update_wire_attachments(wires):
    """
    Update wire points that are attached to components.

    Args:
        wires: list of wire dicts with 'points' and 'attachments'
    """
    for wire in wires:
        attachments = wire.get('attachments', [])
        for i, attach in enumerate(attachments):
            if attach:
                comp, pin_idx = attach
                pin_pos = get_component_pins(comp)[pin_idx]
                wire['points'][i] = pin_pos

def delete_wire_under_mouse(wires, mouse_world, radius=SNAP_RADIUS):
    """
    Delete a wire if the mouse is near any of its segments.

    Args:
        wires (list[dict]): List of wires
        mouse_world (Vector2): Mouse position in world coordinates
        radius (float, optional): Max distance to consider wire "hit"

    Returns:
        bool: True if a wire was deleted, False otherwise
    """
    wire, _, _ = find_wire_segment_at_mouse(wires, mouse_world, radius)
    if wire:
        wires.remove(wire)
        return True
    return False

# ===============================
# 6. SELECTION & DRAGGING
# ===============================
def drag_components(selected_components: list[dict], drag_offsets: list[Vector2], mouse_world: Vector2) -> list[Vector2]:
    """
    Compute new positions for selected components while dragging.

    Args:
        selected_components (list[dict]): Components being dragged
        drag_offsets (list[Vector2]): Original offsets between mouse and component positions
        mouse_world (Vector2): Current mouse position in world coordinates

    Returns:
        list[Vector2]: New snapped positions for each selected component
    """
    new_positions = []
    for comp, offset in zip(selected_components, drag_offsets):
        new_pos = snap_to_grid(mouse_world + offset)
        new_positions.append(new_pos)
    return new_positions

def box_select_components(components: list[dict], rect: pygame.Rect, camera_offset: Vector2) -> list[dict]:
    """
    Return components whose screen positions are inside the selection rectangle.

    Args:
        components (list[dict]): List of all components
        rect (pygame.Rect): Selection rectangle in screen coordinates
        camera_offset (Vector2): Camera offset for converting world -> screen

    Returns:
        list[dict]: Components inside the selection rectangle
    """
    selected = []
    for comp in components:
        screen_pos = world_to_screen(comp['pos'], camera_offset)
        if rect.collidepoint(screen_pos):
            selected.append(comp)
    return selected


def find_pin_at_mouse(components, mouse_world, radius=6):
    for comp in components:
        for pin in get_component_pins(comp):
            if (pin - mouse_world).length() <= radius:
                return pin
    return None

def find_component_and_pin_under_mouse(mouse_world, components):
    for comp in components:  # components must be global or pass as argument
        pins = get_component_pins(comp)
        for idx, pin in enumerate(pins):
            if (pin - mouse_world).length() <= SNAP_RADIUS:
                return comp, idx
    return None, None

# ===============================
# 7. CAMERA HELPERS
# ===============================
def world_to_screen(pos: Vector2, camera_offset: Vector2) -> Vector2:
    """
    Convert a world position to screen coordinates considering camera offset.

    Args:
        pos (Vector2): Position in world coordinates
        camera_offset (Vector2): Current camera offset

    Returns:
        Vector2: Position in screen coordinates for drawing
    """
    return pos - camera_offset

def screen_to_world(pos: Vector2, camera_offset: Vector2) -> Vector2:
    """
    Convert a screen position (mouse, selection rectangle) to world coordinates.

    Args:
        pos (Vector2): Position in screen coordinates
        camera_offset (Vector2): Current camera offset

    Returns:
        Vector2: Corresponding position in world coordinates
    """
    return pos + camera_offset

# ===============================
# 9. INPUTS
# ===============================
def handle_keyboard_event(event, components, selected_components, wires, mouse_world, undo_stack, redo_stack):
    """
    Handle keyboard events.

    Args:
        event: pygame.KEYDOWN event
        selected_components: list of selected components

    Returns:
        dict: Actions to take (e.g., {'cancel_wire': True})
    """
    actions = {}

    mods = pygame.key.get_mods()
    ctrl_pressed = mods & pygame.KMOD_CTRL

    if event.key == pygame.K_ESCAPE:
        actions['cancel_wire'] = True

    if event.key == pygame.K_r:
        record_undo(components, wires, undo_stack, redo_stack)  # snapshot BEFORE rotation
        for comp in selected_components:
            comp['rotation'] = (comp['rotation'] + ROTATION_STEP) % 360

    if event.key == pygame.K_x:
        # Delete wire under mouse
        record_undo(components, wires, undo_stack, redo_stack)
        deleted = delete_wire_under_mouse(wires, mouse_world)
        actions['wire_deleted'] = deleted

    if ctrl_pressed and event.key == pygame.K_z:
        actions['undo'] = True
    if ctrl_pressed and event.key == pygame.K_y:
        actions['redo'] = True

    return actions

def handle_mouse_button_down(event, mouse_world, mouse_screen, components, wires, active_wire, selected_components, drag_offsets, selection_start, undo_stack, redo_stack):
    """
    Handle mouse button down events.

    Args:
        event: pygame.MOUSEBUTTONDOWN event
        mouse_world: Vector2 mouse position in world coordinates
        mouse_screen: Vector2 mouse position in screen coordinates
        components: list of components
        wires: list of wires
        active_wire: currently active wire or None
        selected_components: list of currently selected components
        drag_offsets: list of Vector2 offsets for dragging
        selection_start: Vector2 or None

    Returns:
        dict: Updated state including active_wire, selected_components, drag_offsets, selection_start
    """
    state_update = {
        'active_wire': active_wire,
        'selected_components': selected_components,
        'drag_offsets': drag_offsets,
        'selection_start': selection_start,
    }

    if event.button == 1:  # left click
        clicked_pin = snap_to_pins(mouse_world, components)
        comp, pin_idx = find_component_and_pin_under_mouse(mouse_world, components) if clicked_pin else (None, None)

        if not clicked_pin:
            wire, idx, closest = find_wire_segment_at_mouse(wires, mouse_world)
            if wire:
                clicked_pin = snap_to_grid(closest)
                comp, pin_idx = None, None

                # Insert bends along orthogonal path
                prev = wire['points'][idx]
                for p in orthogonal_path(prev, clicked_pin, mouse=mouse_world):
                    if p != prev:
                        wire['points'].insert(idx + 1, p)
                        wire.setdefault('attachments', []).insert(idx + 1, None)
                        idx += 1
                wire['points'] = clean_collinear_points(wire['points'])

        # Start or continue wire
        if clicked_pin or wire:
            new_point = clicked_pin if clicked_pin else snap_to_grid(mouse_world)
            if active_wire is None:
                state_update['active_wire'] = {
                    'points': [new_point],
                    'attachments': [(comp, pin_idx) if clicked_pin else None]
                }
            else:
                last = active_wire['points'][-1]
                for p in orthogonal_path(last, new_point, mouse=mouse_world):
                    if p != last:
                        active_wire['points'].append(p)
                        active_wire['attachments'].append(None)
                if clicked_pin:
                    active_wire['attachments'][-1] = (comp, pin_idx)
                    record_undo(components, wires, undo_stack, redo_stack)  # snapshot BEFORE wire added
                    wires.append(active_wire)
                    state_update['active_wire'] = None

        # Skip selection logic if wire click occurred
        if clicked_pin or wire:
            return state_update

        # Component body click
        clicked_component = None
        for comp in components:
            if (comp['pos'] - snap_to_grid(mouse_world)).length() < GRID_SIZE / 2:
                clicked_component = comp
                break

        keys = pygame.key.get_pressed()
        if clicked_component:
            record_undo(components, wires, undo_stack, redo_stack)  # snapshot BEFORE drag starts
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                if clicked_component not in selected_components:
                    selected_components.append(clicked_component)
            else:
                selected_components = [clicked_component]

            drag_offsets = [comp['pos'] - mouse_world for comp in selected_components]

            state_update['selected_components'] = selected_components
            state_update['drag_offsets'] = drag_offsets
            state_update['selection_start'] = None
            return state_update

        # Empty space → start box selection
        state_update['selected_components'] = []
        state_update['selection_start'] = mouse_screen
        return state_update

    elif event.button == 3:  # right click → place new component
        record_undo(components, wires, undo_stack, redo_stack)  # snapshot BEFORE change
        snapped_pos = snap_to_grid(mouse_world)
        components.append({
            'type': 'resistor',
            'pos': snapped_pos,
            'rotation': 0,
        })
        return state_update

    return state_update

def handle_mouse_motion(mouse_screen, selection_start):
    """
    Handle mouse motion events for box selection.

    Args:
        mouse_screen: Vector2 current mouse screen position
        selection_start: Vector2 starting point of box selection

    Returns:
        pygame.Rect | None: Updated selection rectangle
    """
    if selection_start:
        return make_rect(selection_start, mouse_screen)
    return None

def handle_mouse_button_up(event, selection_rect, components, selected_components, camera_offset):
    """
    Handle mouse button up events for selection.

    Args:
        event: pygame.MOUSEBUTTONUP
        selection_rect: pygame.Rect current selection rectangle
        components: list of components
        selected_components: list of currently selected components
        camera_offset: Vector2 camera offset

    Returns:
        list[dict]: Updated selected components
    """
    if event.button == 1 and selection_rect:
        keys = pygame.key.get_pressed()
        box_selected = box_select_components(components, selection_rect, camera_offset)

        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            for comp in box_selected:
                if comp not in selected_components:
                    selected_components.append(comp)
        else:
            selected_components = box_selected
    return selected_components

# ===============================
# 10. DRAW
# ===============================
def draw_grid(screen, camera_offset, grid_size):
    """
    Draws a scrolling grid background.

    Args:
        screen: pygame display surface
        camera_offset (Vector2): current camera offset
        grid_size (int): grid spacing in pixels
    """
    width, height = screen.get_size()

    start_x = -camera_offset.x % grid_size
    start_y = -camera_offset.y % grid_size

    for x in range(int(start_x), width, grid_size):
        pygame.draw.line(screen, (51, 51, 51), (x, 0), (x, height))

    for y in range(int(start_y), height, grid_size):
        pygame.draw.line(screen, (51, 51, 51), (0, y), (width, y))

def draw_components(screen, components, selected_components, camera_offset):
    """
    Draws all components and their orientation indicators.

    Args:
        screen: pygame display surface
        components (list[dict]): all components
        selected_components (list[dict]): selected components
        camera_offset (Vector2): camera offset
    """
    for comp in components:
        screen_pos = world_to_screen(comp['pos'], camera_offset)

        color = (255, 200, 0) if comp in selected_components else (0, 200, 0)
        rect = pygame.Rect(screen_pos.x - 10, screen_pos.y - 10, 20, 20)
        pygame.draw.rect(screen, color, rect)

        angle = comp['rotation']
        if angle % 180 == 0:
            pygame.draw.line(
                screen, (0, 0, 0),
                (rect.centerx - 5, rect.centery),
                (rect.centerx + 5, rect.centery),
                2
            )
        else:
            pygame.draw.line(
                screen, (0, 0, 0),
                (rect.centerx, rect.centery - 5),
                (rect.centerx, rect.centery + 5),
                2
            )

def draw_pins(screen, components, camera_offset):
    """
    Draws all component pins.

    Args:
        screen: pygame display surface
        components (list[dict]): all components
        camera_offset (Vector2): camera offset
    """
    for comp in components:
        for pin_pos in get_component_pins(comp):
            pin_screen = world_to_screen(pin_pos, camera_offset)
            pygame.draw.circle(screen, (200, 50, 50), pin_screen, 4)

def draw_wires(screen, wires, camera_offset):
    """
    Draws all completed wires.

    Args:
        screen: pygame display surface
        wires (list[dict]): list of wires
        camera_offset (Vector2): camera offset
    """
    for wire in wires:
        points = [world_to_screen(p, camera_offset) for p in wire['points']]
        pygame.draw.lines(screen, (100, 200, 255), False, points, 3)

        for p in points:
            pygame.draw.circle(screen, (255, 100, 50), p, 3)

def draw_active_wire(screen, active_wire, preview_point, mouse_world, camera_offset, components, wires):
    """
    Draws the preview of the currently active wire.
    """
    if not active_wire or preview_point is None:
        return

    last = active_wire['points'][-1]
    preview_points = orthogonal_path(last, preview_point, mouse=mouse_world)
    points = active_wire['points'] + preview_points
    points = [world_to_screen(p, camera_offset) for p in points]

    # ===============================
    # Highlight preview color based on snapping
    # ===============================
    preview_color = (200, 200, 200) if (snap_to_pins(mouse_world, components) or snap_to_wire_points(mouse_world, wires)) else (150, 150, 150)

    pygame.draw.lines(screen, preview_color, False, points, 2)

    for p in points:
        pygame.draw.circle(screen, (255, 100, 50), p, 3)

def draw_selection_rect(screen, selection_rect):
    """
    Draws the box selection rectangle.

    Args:
        screen: pygame display surface
        selection_rect (pygame.Rect | None): selection rectangle
    """
    if selection_rect:
        pygame.draw.rect(screen, (100, 150, 255), selection_rect, 1)

def draw_debug_info(screen, font, mouse_screen, mouse_world, fps):
    """
    Draws debug text on screen.

    Args:
        screen: pygame display surface
        font: pygame font
        mouse_screen (Vector2): mouse position on screen
        mouse_world (Vector2): mouse position in world
        fps (float): frames per second
    """
    screen.blit(font.render(f"FPS: {fps:.1f}", True, (255, 255, 255)), (10, 10))
    screen.blit(font.render(
        f"Screen: {int(mouse_screen.x)}, {int(mouse_screen.y)}",
        True, (255, 255, 255)), (10, 30))
    screen.blit(font.render(
        f"World: {int(mouse_world.x)}, {int(mouse_world.y)}",
        True, (200, 200, 200)), (10, 50))

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Electronics Simulator")

    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    # ===============================
    # WORLD STATE
    # ===============================
    components = []
    wires = []
    active_wire = None

    selected_components = []
    drag_offsets = []

    selection_start = None
    selection_rect = None

    camera_offset = Vector2(0, 0)
    preview_point = None

    running = True

    # Initialize stacks
    undo_stack = []
    redo_stack = []

    # Before any change, optionally push initial state
    undo_stack.append(take_snapshot(components, wires))

    # ===============================
    # MAIN LOOP
    # ===============================
    while running:
        dt = clock.tick(60) / 1000.0
        fps = clock.get_fps()

        mouse_screen = Vector2(pygame.mouse.get_pos())
        mouse_world = screen_to_world(mouse_screen, camera_offset)

        mouse_pressed = pygame.mouse.get_pressed()
        keys = pygame.key.get_pressed()

        # ===============================
        # PREVIEW POINT UPDATE (WIRE)
        # ===============================
        if active_wire:
            preview_point = (
                snap_to_pins(mouse_world, components)
                or snap_to_wire_points(mouse_world, wires)
                or snap_to_grid(mouse_world)
            )
        else:
            preview_point = None

        # ===============================
        # INPUT EVENTS
        # ===============================
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                actions = handle_keyboard_event(
                    event, components, selected_components, wires, mouse_world, undo_stack, redo_stack
                )
                if actions.get("cancel_wire"):
                    active_wire = None
                if actions.get("undo"):
                    components, wires = undo(undo_stack, redo_stack, components, wires)
                if actions.get("redo"):
                    components, wires = redo(undo_stack, redo_stack, components, wires)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                state = handle_mouse_button_down(
                    event,
                    mouse_world,
                    mouse_screen,
                    components,
                    wires,
                    active_wire,
                    selected_components,
                    drag_offsets,
                    selection_start,
                    undo_stack,
                    redo_stack
                )
                active_wire = state["active_wire"]
                selected_components = state["selected_components"]
                drag_offsets = state["drag_offsets"]
                selection_start = state["selection_start"]

            elif event.type == pygame.MOUSEMOTION:
                selection_rect = handle_mouse_motion(mouse_screen, selection_start)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    selected_components = handle_mouse_button_up(
                        event,
                        selection_rect,
                        components,
                        selected_components,
                        camera_offset,
                    )
                    selection_start = None
                    selection_rect = None
                    drag_offsets = []

        # ===============================
        # CAMERA PAN (MIDDLE MOUSE)
        # ===============================
        if mouse_pressed[1]:
            camera_offset -= Vector2(pygame.mouse.get_rel())
        else:
            pygame.mouse.get_rel()

        # ===============================
        # DRAGGING SELECTED COMPONENTS
        # ===============================
        if selected_components and drag_offsets and mouse_pressed[0]:
            new_positions = drag_components(
                selected_components,
                drag_offsets,
                mouse_world,
            )
            for comp, pos in zip(selected_components, new_positions):
                comp["pos"] = pos

            update_wire_attachments(wires)

        # ===============================
        # RENDERING
        # ===============================
        screen.fill((17, 17, 17))

        draw_grid(screen, camera_offset, GRID_SIZE)
        draw_components(screen, components, selected_components, camera_offset)
        draw_pins(screen, components, camera_offset)
        draw_wires(screen, wires, camera_offset)
        draw_active_wire(
            screen,
            active_wire,
            preview_point,
            mouse_world,
            camera_offset,
            components,
            wires,
        )
        draw_selection_rect(screen, selection_rect)
        draw_debug_info(screen, font, mouse_screen, mouse_world, fps)

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()
