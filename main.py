import pygame
from pygame.math import Vector2

GRID_SIZE = 40
ROTATION_STEP = 90

COMPONENT_PINS = {
    'resistor': [
        Vector2(-20, 0),
        Vector2(20, 0)
    ]
}

def orthogonal_path(a, b, mouse=None):
    """
    Returns a list of points forming an orthogonal path from a to b.
    """
    if a.x == b.x or a.y == b.y:
        return [b]

    corner_hv = Vector2(b.x, a.y)
    corner_vh = Vector2(a.x, b.y)
    
    if mouse:
        d_hv = (corner_hv - mouse).length_squared()
        d_vh = (corner_vh - mouse).length_squared()
        corner = corner_hv if d_hv < d_vh else corner_vh
    else:
        corner = corner_hv

    return [corner, b]

def rotate_point(point, angle_deg):
    return point.rotate(angle_deg)

def get_component_pins(comp):
    pins = []
    for local_pin in COMPONENT_PINS.get(comp['type'], []):
        rotated = rotate_point(local_pin, comp['rotation'])
        world_pos = comp['pos'] + rotated
        pins.append(world_pos)
    return pins

def snap_to_grid(pos):
    return Vector2(
        round(pos.x / GRID_SIZE) * GRID_SIZE,
        round(pos.y / GRID_SIZE) * GRID_SIZE
    )

SNAP_RADIUS = 8

def snap_to_pins(mouse_world, components, radius=SNAP_RADIUS):
    """
    Return nearest pin within radius or None
    """
    closest = None
    min_dist2 = radius * radius
    for comp in components:
        for pin in get_component_pins(comp):
            d2 = (pin - mouse_world).length_squared()
            if d2 <= min_dist2:
                min_dist2 = d2
                closest = pin
    return closest

def snap_to_wire_points(mouse_world, wires, radius=SNAP_RADIUS):
    """
    Return nearest wire point within radius or None
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

def nearest_point_on_segment(a, b, p):
    """
    Return the closest point on segment a-b to point p
    """
    ap = p - a
    ab = b - a
    t = max(0, min(1, ap.dot(ab) / ab.length_squared()))
    return a + ab * t

def find_wire_segment_at_mouse(wires, mouse_world, radius=SNAP_RADIUS):
    for wire in wires:
        for i in range(len(wire['points']) - 1):
            a, b = wire['points'][i], wire['points'][i +1]
            closest = nearest_point_on_segment(a, b, mouse_world)
            if (closest - mouse_world).length_squared() <= radius * radius:
                return wire, i, closest
    return None, None, None

def world_to_screen(pos, camera_offset):
    return pos - camera_offset

def screen_to_world(pos, camera_offset):
    return pos + camera_offset

def drag_components(selected_components, drag_offsets, mouse_world):
    """
    Returns a list of updated positions for selected components while dragging.
    """
    new_positions = []
    for i, comp in enumerate(selected_components):
        new_pos = snap_to_grid(mouse_world + drag_offsets[i])
        new_positions.append(new_pos)
    return new_positions

def make_rect(a, b):
    """
    Create a pygame.Rect from two points (any order).
    """
    x = min(a.x, b.x)
    y = min(a.y, b.y)
    w = abs(a.x - b.x)
    h = abs(a.y - b.y)
    return pygame.Rect(x, y, w, h)

def box_select_components(components, rect, camera_offset):
    """
    Returns a list of components whose screen positions
    are inside the selection rectangle.
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

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption('Electronics Simulator')
    
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    running = True
    camera_offset = Vector2(0, 0)

    # --- World State ---
    components = [] # list of {'type': str, 'pos': Vector2}
    selected_components = []
    drag_offsets = []
    selection_start = None
    selection_rect = None
    wires = []
    active_wire = None
    preview_point = None

    while running:
        dt = clock.tick(60) / 1000.0
        fps = clock.get_fps()

        mouse_screen = Vector2(pygame.mouse.get_pos())
        mouse_world = screen_to_world(mouse_screen, camera_offset)
        mouse_pressed = pygame.mouse.get_pressed()
        keys = pygame.key.get_pressed()

        if active_wire:
            preview_point = snap_to_pins(mouse_world, components)
            if not preview_point:
                preview_point = snap_to_wire_points(mouse_world, wires)
            if not preview_point:
                preview_point = snap_to_grid(mouse_world)

        # --- EVENTS ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    active_wire = None
                if event.key == pygame.K_r:
                    for comp in selected_components:
                        comp['rotation'] = (comp['rotation'] + ROTATION_STEP) % 360

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # left click
                    # wire splitting
                    wire, idx, closest = find_wire_segment_at_mouse(wires, mouse_world)
                    if wire:
                        split_point = snap_to_grid(closest)
            
                        prev = wire['points'][idx]
                        for p in orthogonal_path(prev, split_point, mouse=mouse_world):
                            wire['points'].insert(idx + 1, p)
                            idx += 1

                        # start a new wire
                        active_wire = {'points': [split_point]}

                        selected_components = []
                        drag_offsets = []
                        continue

                    # find snap target
                    snap_target = snap_to_pins(mouse_world, components)
                    if not snap_target:
                        snap_target = snap_to_wire_points(mouse_world, wires)
                    if not snap_target:
                        snap_target = snap_to_grid(mouse_world)  # fallback to grid

                    # wire handling
                    if active_wire is None:
                        # start wire
                        active_wire = {'points': [snap_target]}
                    else:
                        # add a new bend / end point
                        last = active_wire['points'][-1]
                        for p in orthogonal_path(last, snap_target, mouse=mouse_world):
                            if p != last:
                                active_wire['points'].append(p)
                                last = p
            
                        if find_pin_at_mouse(components, snap_target):
                            # try snapping to pin first
                            wires.append(active_wire)
                            active_wire = None

                    # check if clicking on a component
                    clicked_component = None
                    for comp in components:
                        if (comp['pos'] - snap_to_grid(mouse_world)).length() < GRID_SIZE / 2:
                            clicked_component = comp
                            break

                    if clicked_component:
                        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                            # multi-select
                            if clicked_component not in selected_components:
                                selected_components.append(clicked_component)
                        else:
                            # single select
                            selected_components = [clicked_component]
                        drag_offsets = [comp['pos'] - mouse_world for comp in selected_components]
                    else:
                        # start box selection
                        selected_components = []
                        selection_start = mouse_screen
                        selection_rect = None
                elif event.button == 3: # right click
                    # delete function
                    '''
                    for comp in components:
                        if (comp['pos'] - snap_to_grid(mouse_world)).length() < GRID_SIZE / 2:
                            if comp in selected_components:
                                selected_components.remove(comp)
                            components.remove(comp)
                            break
                    '''
                    snapped_pos = snap_to_grid(mouse_world)
                    components.append({
                        'type': 'resistor',
                        'pos': snapped_pos,
                        'rotation': 0,
                    })

            elif event.type == pygame.MOUSEMOTION:
                if selection_start:
                    selection_rect = make_rect(selection_start, mouse_screen)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if selection_rect:
                        box_selected = box_select_components(
                            components, 
                            selection_rect, 
                            camera_offset
                        )

                        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                            for comp in box_selected: 
                                if comp not in selected_components:
                                    selected_components.append(comp)
                        else:
                            selected_components = box_selected

                    selection_start = None
                    selection_rect = None
                    drag_offsets = []

        # --- CAMERA PAN ---
        if pygame.mouse.get_pressed()[1]:
            movement = Vector2(pygame.mouse.get_rel())
            camera_offset -= movement
        else:
            pygame.mouse.get_rel()

        # --- DRAGGING SELECTED COMPONENT ---
        if selected_components and drag_offsets and mouse_pressed[0]:
            new_positions = drag_components(selected_components, drag_offsets, mouse_world)
            for comp, pos in zip(selected_components, new_positions):
                comp['pos'] = pos

        # --- DRAW ---
        screen.fill((17, 17, 17))

        # --- GRID ---
        width, height = screen.get_size()
        start_x = -camera_offset.x % GRID_SIZE
        start_y = -camera_offset.y % GRID_SIZE
        for x in range(int(start_x), width, GRID_SIZE):
            pygame.draw.line(screen, (51, 51, 51), (x, 0), (x, height))
        for y in range(int(start_y), height, GRID_SIZE):
            pygame.draw.line(screen, (51, 51, 51), (0, y), (width, y))
        
        # --- COMPONENTS ---
        for comp in components:
            screen_pos = world_to_screen(comp['pos'], camera_offset)
            color = (255, 200, 0) if comp in selected_components else (0, 200, 0)
            rect = pygame.Rect(screen_pos.x - 10, screen_pos.y - 10, 20, 20)
            pygame.draw.rect(screen, color, rect)
            angle = comp['rotation']
            if angle % 180 == 0:
                pygame.draw.line(screen, (0, 0, 0), (rect.centerx-5, rect.centery), (rect.centerx+5, rect.centery), 2)
            else:
                pygame.draw.line(screen, (0, 0, 0), (rect.centerx, rect.centery-5), (rect.centerx, rect.centery+5), 2)

            # --- PINS ---
            for pin_pos in get_component_pins(comp):
                pin_screen = world_to_screen(pin_pos, camera_offset)
                pygame.draw.circle(screen, (200, 50, 50), pin_screen, 4)

        # --- MOUSE CROSS ---
        pygame.draw.circle(screen, (255, 0, 0), mouse_screen, 5)
    
        # --- WIRE ---
        for wire in wires:
            points = [world_to_screen(p, camera_offset) for p in wire['points']]
            pygame.draw.lines(screen, (100, 200, 255), False, points, 3)

            for p in points:
                pygame.draw.circle(screen, (255, 100, 50), p, 3)

        if active_wire and preview_point:
            last = active_wire['points'][-1]
            preview_points = orthogonal_path(last, preview_point, mouse=mouse_world)
            points = active_wire['points'] + preview_points
            points = [world_to_screen(p, camera_offset) for p in points]
            pygame.draw.lines(screen, (200, 200, 200), False, points, 2)

            for p in points:
                pygame.draw.circle(screen, (255, 100, 50), p, 3)

        # --- SELECTION RECT ---
        if selection_rect:
            pygame.draw.rect(screen, (100, 150, 255), selection_rect, 1)

        # --- DEBUG ---
        screen_text = font.render(f'Screen: {int(mouse_screen.x)}, {int(mouse_screen.y)}', True, (255, 255, 255))
        world_text = font.render(f'World: {int(mouse_world.x)}, {int(mouse_world.y)}', True, (200, 200, 200))
        fps_text = font.render(f'FPS: {fps:.1f}', True, (255, 255, 255))

        screen.blit(screen_text, (10, 30))
        screen.blit(world_text, (10, 50))
        screen.blit(fps_text, (10, 10))

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()
