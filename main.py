import pygame
from pygame.math import Vector2

GRID_SIZE = 40

def snap_to_grid(pos):
    return Vector2(
        round(pos.x / GRID_SIZE) * GRID_SIZE,
        round(pos.y / GRID_SIZE) * GRID_SIZE
    )

def world_to_screen(pos, camera_offset):
    return pos - camera_offset

def screen_to_world(pos, camera_offset):
    return pos + camera_offset

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

    while running:
        dt = clock.tick(60) / 1000.0
        fps = clock.get_fps()

        # --- EVENTS ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_world = screen_to_world(Vector2(pygame.mouse.get_pos()), camera_offset)
                snapped_pos = snap_to_grid(mouse_world)

                if event.button == 1: # left click
                    components.append({'type': 'resistor', 'pos': snapped_pos})

                elif event.button == 3: # right click
                    for comp in components:
                        if (comp['pos'] - snapped_pos).length() < GRID_SIZE / 2:
                            components.remove(comp)

        # --- CAMERA PAN ---
        if pygame.mouse.get_pressed()[1]:
            movement = Vector2(pygame.mouse.get_rel())
            camera_offset -= movement
        else:
            pygame.mouse.get_rel()

        # --- MOUSE ---
        mouse_screen = Vector2(pygame.mouse.get_pos())
        mouse_world = screen_to_world(mouse_screen, camera_offset)

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
            pygame.draw.rect(screen, (0, 200, 0), (screen_pos.x - 10, screen_pos.y - 10, 20, 20))

        # --- MOUSE CROSS ---
        pygame.draw.circle(screen, (255, 0, 0), mouse_screen, 5)

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
