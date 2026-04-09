import math
import random
import sys

import pygame
import pymunk

pygame.init()
pygame.key.set_repeat(180, 45)

CELL_SIZE = 30
COLS = 10
ROWS = 20

PLAY_WIDTH = CELL_SIZE * COLS
PLAY_HEIGHT = CELL_SIZE * ROWS
SIDE_WIDTH = 260
SCREEN_WIDTH = PLAY_WIDTH + SIDE_WIDTH
SCREEN_HEIGHT = PLAY_HEIGHT

FPS = 60

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("俄罗斯方块：数学+物理增强版")
clock = pygame.time.Clock()

try:
    font = pygame.font.SysFont(["simhei", "microsoftyahei", "arial"], 24)
    small_font = pygame.font.SysFont(["simhei", "microsoftyahei", "arial"], 18)
    big_font = pygame.font.SysFont(["simhei", "microsoftyahei", "arial"], 34)
except Exception:
    font = pygame.font.Font(None, 30)
    small_font = pygame.font.Font(None, 24)
    big_font = pygame.font.Font(None, 42)

BG_COLOR = (16, 18, 28)
GRID_COLOR = (48, 52, 72)
BORDER_COLOR = (210, 215, 230)
TEXT_COLOR = (242, 244, 248)
FLASH_COLOR = (255, 255, 255)
LEVEL_UP_COLOR = (255, 230, 120)

COLORS = {
    "I": (80, 220, 255),
    "O": (255, 220, 90),
    "T": (180, 100, 255),
    "S": (100, 220, 120),
    "Z": (255, 100, 120),
    "J": (100, 140, 255),
    "L": (255, 170, 90),
}

SHAPES = {
    "I": [
        ["....", "####", "....", "...."],
        ["..#.", "..#.", "..#.", "..#."],
        ["....", "....", "####", "...."],
        [".#..", ".#..", ".#..", ".#.."],
    ],
    "O": [[".##.", ".##.", "....", "...."]] * 4,
    "T": [
        [".#..", "###.", "....", "...."],
        [".#..", ".##.", ".#..", "...."],
        ["....", "###.", ".#..", "...."],
        [".#..", "##..", ".#..", "...."],
    ],
    "S": [
        [".##.", "##..", "....", "...."],
        ["#...", "##..", ".#..", "...."],
        [".##.", "##..", "....", "...."],
        ["#...", "##..", ".#..", "...."],
    ],
    "Z": [
        ["##..", ".##.", "....", "...."],
        [".#..", "##..", "#...", "...."],
        ["##..", ".##.", "....", "...."],
        [".#..", "##..", "#...", "...."],
    ],
    "J": [
        ["#...", "###.", "....", "...."],
        [".##.", ".#..", ".#..", "...."],
        ["....", "###.", "..#.", "...."],
        [".#..", ".#..", "##..", "...."],
    ],
    "L": [
        ["..#.", "###.", "....", "...."],
        [".#..", ".#..", ".##.", "...."],
        ["....", "###.", "#...", "...."],
        ["##..", ".#..", ".#..", "...."],
    ],
}

SHAPE_COORDS = {
    name: [[(j, i) for i, line in enumerate(rotation) for j, ch in enumerate(line) if ch == "#"] for rotation in rotations]
    for name, rotations in SHAPES.items()
}


class Piece:
    def __init__(self, shape_name: str):
        self.shape_name = shape_name
        self.rotations = SHAPES[shape_name]
        self.rotation = 0
        self.shape = self.rotations[self.rotation]
        self.coords = SHAPE_COORDS[shape_name][self.rotation]
        self.x = COLS // 2 - 2
        self.y = 0
        self.color = COLORS[shape_name]

    def rotate(self):
        self.rotation = (self.rotation + 1) % 4
        self.shape = self.rotations[self.rotation]
        self.coords = SHAPE_COORDS[self.shape_name][self.rotation]

    def undo_rotate(self):
        self.rotation = (self.rotation - 1) % 4
        self.shape = self.rotations[self.rotation]
        self.coords = SHAPE_COORDS[self.shape_name][self.rotation]


class PieceGenerator:
    def __init__(self):
        self.bag = []

    def get_piece(self):
        if not self.bag:
            self.bag = list(SHAPES.keys())
            random.shuffle(self.bag)
        return Piece(self.bag.pop())


class Spring1D:
    def __init__(self, value=0.0, stiffness=38.0, damping=11.0):
        self.x = value
        self.v = 0.0
        self.k = stiffness
        self.c = damping

    def snap(self, value):
        self.x = value
        self.v = 0.0

    def update(self, target, dt):
        a = self.k * (target - self.x) - self.c * self.v
        self.v += a * dt
        self.x += self.v * dt
        return self.x


class ActivePieceRenderer:
    def __init__(self):
        self.x_spring = Spring1D(0.0, stiffness=44.0, damping=12.5)
        self.y_spring = Spring1D(0.0, stiffness=34.0, damping=10.0)
        self.squash_spring = Spring1D(0.0, stiffness=28.0, damping=8.0)
        self.tilt_spring = Spring1D(0.0, stiffness=26.0, damping=8.5)
        self.initialized = False
        self.fall_speed_hint = 0.0

    def snap_to_piece(self, piece):
        tx = piece.x * CELL_SIZE
        ty = piece.y * CELL_SIZE
        self.x_spring.snap(tx)
        self.y_spring.snap(ty)
        self.squash_spring.snap(0.0)
        self.tilt_spring.snap(0.0)
        self.initialized = True

    def update(self, piece, dt):
        tx = piece.x * CELL_SIZE
        ty = piece.y * CELL_SIZE
        if not self.initialized:
            self.snap_to_piece(piece)

        prev_y = self.y_spring.x
        self.x_spring.update(tx, dt)
        self.y_spring.update(ty, dt)
        self.squash_spring.update(0.0, dt)
        self.tilt_spring.update(0.0, dt)
        self.fall_speed_hint = (self.y_spring.x - prev_y) / (dt * 60) if dt > 0 else 0

    def nudge_move(self, dx):
        self.tilt_spring.v += dx * 42.0

    def nudge_rotate(self):
        self.squash_spring.v += 9.0

    def nudge_hard_drop(self, impact):
        self.squash_spring.v += 12.0 + impact * 4.5

    def get_offset(self, piece):
        tx = piece.x * CELL_SIZE
        ty = piece.y * CELL_SIZE
        return self.x_spring.x - tx, self.y_spring.x - ty

    def get_visual_squash(self):
        return max(0.0, min(1.6, self.squash_spring.x * 0.08 + max(0.0, self.fall_speed_hint) * 0.04))

    def get_visual_tilt(self):
        return max(-1.2, min(1.2, self.tilt_spring.x * 0.025))


class LandedJelly:
    def __init__(self, cells, impact=1.0):
        self.cells = set(cells)
        self.spring = Spring1D(impact, stiffness=24.0, damping=7.8)

    def update(self, dt):
        self.spring.update(0.0, dt)

    @property
    def impact(self):
        return max(0.0, self.spring.x)

    def alive(self):
        return self.impact > 0.02


class FloatingText:
    def __init__(self, text, color, x, y, life=50):
        self.text = text
        self.color = color
        self.x = x
        self.y = y
        self.life = life
        self.max_life = life

    def update(self):
        self.y -= 0.6
        self.life -= 1

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / self.max_life))
        label = big_font.render(self.text, True, self.color)
        temp = pygame.Surface(label.get_size(), pygame.SRCALPHA)
        temp.blit(label, (0, 0))
        temp.set_alpha(alpha)
        surface.blit(temp, (self.x - label.get_width() // 2, int(self.y)))


class PhysicsChunk:
    def __init__(self, body, shape, color, size, life=90):
        self.body = body
        self.shape = shape
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life

    def update(self):
        self.life -= 1

    def alive(self):
        return self.life > 0


def create_physics_space():
    space = pymunk.Space()
    space.gravity = (0, 900)
    floor = pymunk.Segment(space.static_body, (-20, PLAY_HEIGHT + 5), (PLAY_WIDTH + 20, PLAY_HEIGHT + 5), 3)
    left_wall = pymunk.Segment(space.static_body, (-10, 0), (-10, PLAY_HEIGHT + 5), 3)
    right_wall = pymunk.Segment(space.static_body, (PLAY_WIDTH + 10, 0), (PLAY_WIDTH + 10, PLAY_HEIGHT + 5), 3)
    for wall in [floor, left_wall, right_wall]:
        wall.friction = 0.9
        wall.elasticity = 0.12
        space.add(wall)
    return space


def convert_shape_to_positions(piece):
    return [(piece.x + j, piece.y + i) for j, i in piece.coords]


def spawn_clear_chunks(space, rows_to_clear, locked_snapshot, chunks, phase_strength=1.0):
    center = (COLS - 1) / 2
    for y in rows_to_clear:
        for x in range(COLS):
            color = locked_snapshot.get((x, y), FLASH_COLOR)
            cell_px = x * CELL_SIZE
            cell_py = y * CELL_SIZE
            lateral_bias = (x - center) * 18.0 * phase_strength
            for _ in range(4):
                size = random.randint(6, 10)
                mass = 0.4
                moment = pymunk.moment_for_box(mass, (size, size))
                body = pymunk.Body(mass, moment)
                body.position = (cell_px + random.randint(6, CELL_SIZE - 6), cell_py + random.randint(6, CELL_SIZE - 6))
                body.velocity = (random.uniform(-70, 70) + lateral_bias, random.uniform(-150, -35) * phase_strength)
                body.angular_velocity = random.uniform(-7, 7)
                shape = pymunk.Poly.create_box(body, (size, size), radius=1)
                shape.friction = 0.75
                shape.elasticity = 0.12
                space.add(body, shape)
                chunks.append(PhysicsChunk(body, shape, color, size, life=random.randint(50, 85)))


def spawn_dust_chunks(space, piece, chunks, impact=1.0):
    for x, y in convert_shape_to_positions(piece):
        for _ in range(2):
            size = random.randint(4, 7)
            mass = 0.25
            moment = pymunk.moment_for_box(mass, (size, size))
            body = pymunk.Body(mass, moment)
            body.position = (x * CELL_SIZE + random.randint(6, CELL_SIZE - 6), (y + 1) * CELL_SIZE)
            body.velocity = (
                random.uniform(-55, 55) * (0.7 + impact * 0.5),
                random.uniform(-170, -70) * (0.7 + impact * 0.6),
            )
            body.angular_velocity = random.uniform(-10, 10)
            shape = pymunk.Poly.create_box(body, (size, size), radius=1)
            shape.friction = 0.5
            shape.elasticity = 0.08
            space.add(body, shape)
            chunks.append(PhysicsChunk(body, shape, (220, 220, 220), size, life=random.randint(20, 34)))


def cleanup_physics_chunks(space, chunks):
    for chunk in chunks[:]:
        chunk.update()
        if not chunk.alive():
            if chunk.body in space.bodies:
                space.remove(chunk.body, chunk.shape)
            chunks.remove(chunk)


def create_grid(locked):
    grid = [[BG_COLOR for _ in range(COLS)] for _ in range(ROWS)]
    for (x, y), color in locked.items():
        if 0 <= x < COLS and 0 <= y < ROWS:
            grid[y][x] = color
    return grid


def valid_space(piece, locked):
    for x, y in convert_shape_to_positions(piece):
        if x < 0 or x >= COLS or y >= ROWS:
            return False
        if y >= 0 and (x, y) in locked:
            return False
    return True


def touching_ground(piece, locked):
    piece.y += 1
    ok = valid_space(piece, locked)
    piece.y -= 1
    return not ok


def get_full_rows(locked, candidate_rows=None):
    rows = candidate_rows if candidate_rows is not None else range(ROWS)
    return [y for y in sorted(set(rows)) if all((x, y) in locked for x in range(COLS))]


def remove_rows_and_shift(locked, rows_to_clear):
    if not rows_to_clear:
        return 0
    rows_to_clear = sorted(rows_to_clear)
    for y in rows_to_clear:
        for x in range(COLS):
            locked.pop((x, y), None)
    shift = 0
    for y in range(ROWS - 1, -1, -1):
        if y in rows_to_clear:
            shift += 1
        elif shift > 0:
            for x in range(COLS):
                if (x, y) in locked:
                    locked[(x, y + shift)] = locked[(x, y)]
                    del locked[(x, y)]
    return len(rows_to_clear)


def get_ghost_y(piece, locked):
    temp_y = piece.y
    while valid_space(piece, locked):
        piece.y += 1
    ghost_y = piece.y - 1
    piece.y = temp_y
    return ghost_y


def draw_jelly_block(surface, color, x, y, squash=0.0, stretch_x=0.0, offset_px=(0, 0), is_ghost=False, brightness=1.0, jitter=(0, 0), scale=1.0):
    ox, oy = offset_px
    jx, jy = jitter
    base_rect = pygame.Rect(int(x * CELL_SIZE + ox + jx), int(y * CELL_SIZE + oy + jy), CELL_SIZE, CELL_SIZE)
    if is_ghost:
        ghost_color = (int(color[0] * 0.4), int(color[1] * 0.4), int(color[2] * 0.4))
        pygame.draw.rect(surface, ghost_color, base_rect, 2, border_radius=4)
        return

    c = (min(255, int(color[0] * brightness)), min(255, int(color[1] * brightness)), min(255, int(color[2] * brightness)))
    inner = base_rect.inflate(-4, -4)
    sw = int(squash * 6 + abs(stretch_x) * 2.0)
    sh = int(squash * 5)
    w = max(8, int((inner.width + sw) * scale))
    h = max(8, int((max(8, inner.height - sh)) * scale))
    jelly_rect = pygame.Rect(0, 0, w, h)
    jelly_rect.center = (inner.centerx, inner.centery + sh // 2)
    pygame.draw.rect(surface, c, jelly_rect, border_radius=10)
    highlight = (min(255, int(c[0] + 42)), min(255, int(c[1] + 42)), min(255, int(c[2] + 42)))
    top_rect = pygame.Rect(jelly_rect.x + 2, jelly_rect.y + 2, max(4, jelly_rect.width - 4), max(5, jelly_rect.height // 4))
    pygame.draw.rect(surface, highlight, top_rect, border_radius=8)


def draw_ghost(surface, piece, ghost_y):
    if ghost_y == piece.y:
        return
    temp_y = piece.y
    piece.y = ghost_y
    for x, y in convert_shape_to_positions(piece):
        if y >= 0:
            draw_jelly_block(surface, piece.color, x, y, is_ghost=True)
    piece.y = temp_y


def draw_locked_grid(surface, grid, clear_anim=None, landed_jelly=None):
    landed_cells = landed_jelly.cells if landed_jelly else set()
    landed_impact = landed_jelly.impact if landed_jelly else 0.0
    rows_to_clear = clear_anim["rows"] if clear_anim else []
    phase = clear_anim["phase"] if clear_anim else 0
    t = clear_anim["t"] if clear_anim else 0.0

    for y in range(ROWS):
        for x in range(COLS):
            rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(surface, GRID_COLOR, rect, 1)
            color = grid[y][x]
            if color == BG_COLOR:
                continue
            if y in rows_to_clear:
                if phase == 1:
                    draw_jelly_block(surface, color, x, y, brightness=1.05, scale=1.0 - 0.18 * t)
                elif phase == 2:
                    draw_jelly_block(surface, color, x, y, brightness=1.05 + 0.30 * t, jitter=(random.uniform(-1.2, 1.2) * t * 2.0, random.uniform(-0.8, 0.8) * t * 1.5), scale=0.82 + 0.05 * math.sin(t * math.pi * 8))
                continue
            squash = landed_impact if (x, y) in landed_cells else 0.0
            draw_jelly_block(surface, color, x, y, squash=squash)


def draw_active_piece(surface, piece, renderer):
    offset_px = renderer.get_offset(piece)
    stretch = renderer.get_visual_tilt()
    squash = renderer.get_visual_squash()
    for x, y in convert_shape_to_positions(piece):
        if 0 <= x < COLS and 0 <= y < ROWS:
            draw_jelly_block(surface, piece.color, x, y, squash=squash, stretch_x=stretch, offset_px=offset_px)


def draw_piece_preview(surface, piece, start_x, start_y):
    label = small_font.render("下一个", True, TEXT_COLOR)
    surface.blit(label, (start_x, start_y))
    for i, line in enumerate(piece.shape):
        for j, ch in enumerate(line):
            if ch == "#":
                rect = pygame.Rect(start_x + j * 20, start_y + 40 + i * 20, 20, 20)
                pygame.draw.rect(surface, piece.color, rect, border_radius=5)
                pygame.draw.rect(surface, GRID_COLOR, rect, 1, border_radius=5)


def draw_physics_chunks(surface, chunks):
    for chunk in chunks:
        x, y = chunk.body.position
        angle = chunk.body.angle
        size = chunk.size
        alpha = max(25, int(255 * (chunk.life / chunk.max_life)))
        temp = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.rect(temp, (*chunk.color, alpha), (size // 2, size // 2, size, size), border_radius=2)
        rotated = pygame.transform.rotate(temp, -math.degrees(angle))
        surface.blit(rotated, rotated.get_rect(center=(int(x), int(y))).topleft)


def draw_window(surface, grid, score, current_piece, ghost_y, next_piece, paused, level, speed_ms, chunks, active_renderer, lines_cleared, floating_texts, clear_anim=None, landed_jelly=None):
    surface.fill(BG_COLOR)
    pygame.draw.rect(surface, BORDER_COLOR, (0, 0, PLAY_WIDTH, PLAY_HEIGHT), 3)
    if not paused and current_piece and ghost_y is not None:
        draw_ghost(surface, current_piece, ghost_y)
    draw_locked_grid(surface, grid, clear_anim=clear_anim, landed_jelly=landed_jelly)
    if not paused and current_piece and not clear_anim:
        draw_active_piece(surface, current_piece, active_renderer)
    draw_physics_chunks(surface, chunks)
    for f in floating_texts:
        f.draw(surface)

    title = font.render("俄罗斯方块", True, TEXT_COLOR)
    surface.blit(title, (PLAY_WIDTH + 20, 20))
    info = [f"分数: {score}", f"当前等级: Lv.{level}", f"总消行数: {lines_cleared}", f"下落间隔: {speed_ms} ms", "", "← → 移动 (长按)", "↑ 旋转", "↓ 软降", "空格 硬降", "ESC 暂停/继续", "F1 重新开始"]
    for i, txt in enumerate(info):
        surface.blit(small_font.render(txt, True, TEXT_COLOR), (PLAY_WIDTH + 20, 80 + i * 25))
    draw_piece_preview(surface, next_piece, PLAY_WIDTH + 20, 380)

    if paused:
        overlay = pygame.Surface((PLAY_WIDTH, PLAY_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        surface.blit(overlay, (0, 0))
        pause_label = font.render("已暂停", True, TEXT_COLOR)
        tip_label = small_font.render("按 ESC 继续", True, TEXT_COLOR)
        surface.blit(pause_label, (PLAY_WIDTH // 2 - pause_label.get_width() // 2, PLAY_HEIGHT // 2 - 25))
        surface.blit(tip_label, (PLAY_WIDTH // 2 - tip_label.get_width() // 2, PLAY_HEIGHT // 2 + 15))


def draw_game_over(surface, score):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    surface.blit(overlay, (0, 0))
    text1 = font.render("游戏结束", True, (255, 80, 80))
    text2 = small_font.render(f"最终分数: {score}", True, TEXT_COLOR)
    text3 = small_font.render("按 F1 重新开始 / 窗口关闭退出", True, TEXT_COLOR)
    surface.blit(text1, (PLAY_WIDTH // 2 - text1.get_width() // 2, PLAY_HEIGHT // 2 - 50))
    surface.blit(text2, (PLAY_WIDTH // 2 - text2.get_width() // 2, PLAY_HEIGHT // 2))
    surface.blit(text3, (PLAY_WIDTH // 2 - text3.get_width() // 2, PLAY_HEIGHT // 2 + 40))


def try_rotate_with_kick(piece, locked):
    piece.rotate()
    if valid_space(piece, locked):
        return True
    kicks = [(-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1), (1, -1), (-1, -1)]
    for dx, dy in kicks:
        piece.x += dx
        piece.y += dy
        if valid_space(piece, locked):
            return True
        piece.x -= dx
        piece.y -= dy
    piece.undo_rotate()
    return False


def compute_impact_from_drop(drop_distance):
    return min(2.2, 0.45 + 0.22 * math.sqrt(max(0, drop_distance)))


def get_clear_anim_state(now, start_time):
    elapsed = now - start_time
    if elapsed < 90:
        return {"phase": 1, "t": elapsed / 90.0}
    if elapsed < 180:
        return {"phase": 2, "t": (elapsed - 90) / 90.0}
    return {"phase": 3, "t": min(1.0, (elapsed - 180) / 80.0)}


def lock_current_piece(current_piece, locked):
    placed_positions = []
    touched_rows = set()
    for x, y in convert_shape_to_positions(current_piece):
        if y >= 0:
            locked[(x, y)] = current_piece.color
            placed_positions.append((x, y))
            touched_rows.add(y)
    return placed_positions, touched_rows


def run_game():
    space = create_physics_space()
    physics_chunks = []
    locked = {}
    generator = PieceGenerator()
    current_piece = generator.get_piece()
    next_piece = generator.get_piece()

    score = 0
    total_lines = 0
    paused = False
    game_over = False
    speed_levels = [800, 650, 500, 400, 300, 220, 150, 100, 70, 45]
    level = 1
    fall_speed = speed_levels[0]

    last_fall = pygame.time.get_ticks()
    lock_delay = 500
    touching_since = None
    lock_resets = 0
    max_lock_resets = 15

    clearing = False
    rows_to_clear = None
    clear_start_time = 0
    clear_duration = 260
    clear_chunks_spawned = False

    floating_texts = []
    landed_jelly = None
    active_renderer = ActivePieceRenderer()
    active_renderer.snap_to_piece(current_piece)
    ghost_y = get_ghost_y(current_piece, locked)
    physics_accumulator = 0.0
    physics_step = 1.0 / 120.0

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1:
                    return "restart"
                if event.key == pygame.K_ESCAPE:
                    if not game_over:
                        paused = not paused
                        if not paused:
                            last_fall = pygame.time.get_ticks()
                    continue
                if paused or clearing or game_over:
                    continue

                moved = False
                if event.key == pygame.K_LEFT:
                    current_piece.x -= 1
                    if not valid_space(current_piece, locked):
                        current_piece.x += 1
                    else:
                        active_renderer.nudge_move(-1)
                        moved = True
                elif event.key == pygame.K_RIGHT:
                    current_piece.x += 1
                    if not valid_space(current_piece, locked):
                        current_piece.x -= 1
                    else:
                        active_renderer.nudge_move(1)
                        moved = True
                elif event.key == pygame.K_DOWN:
                    current_piece.y += 1
                    if not valid_space(current_piece, locked):
                        current_piece.y -= 1
                    else:
                        score += 1
                        moved = True
                elif event.key == pygame.K_UP:
                    if try_rotate_with_kick(current_piece, locked):
                        active_renderer.nudge_rotate()
                        moved = True
                elif event.key == pygame.K_SPACE:
                    dropped_piece = current_piece
                    drop_distance = ghost_y - current_piece.y
                    current_piece.y = ghost_y
                    impact = compute_impact_from_drop(drop_distance)
                    score += max(0, drop_distance) * 2
                    active_renderer.nudge_hard_drop(impact)
                    placed_positions, touched_rows = lock_current_piece(current_piece, locked)
                    landed_jelly = LandedJelly(placed_positions, impact=impact)
                    check_rows = get_full_rows(locked, touched_rows)
                    if check_rows:
                        clearing = True
                        rows_to_clear = check_rows
                        clear_start_time = now
                        clear_chunks_spawned = False
                    else:
                        current_piece = next_piece
                        next_piece = generator.get_piece()
                        active_renderer = ActivePieceRenderer()
                        active_renderer.snap_to_piece(current_piece)
                        if not valid_space(current_piece, locked):
                            game_over = True
                    ghost_y = get_ghost_y(current_piece, locked) if not game_over else None
                    last_fall = now
                    touching_since = None
                    lock_resets = 0
                    if drop_distance > 1:
                        spawn_dust_chunks(space, dropped_piece, physics_chunks, impact=impact)

                if moved and not clearing and not game_over:
                    ghost_y = get_ghost_y(current_piece, locked)
                    if touching_ground(current_piece, locked):
                        if lock_resets < max_lock_resets:
                            touching_since = now
                            lock_resets += 1
                    else:
                        touching_since = None

        if not paused:
            physics_accumulator = min(physics_accumulator + dt, 0.25)
            while physics_accumulator >= physics_step:
                space.step(physics_step)
                physics_accumulator -= physics_step
            cleanup_physics_chunks(space, physics_chunks)

        for f in floating_texts[:]:
            f.update()
            if f.life <= 0:
                floating_texts.remove(f)

        if landed_jelly:
            landed_jelly.update(dt)
            if not landed_jelly.alive():
                landed_jelly = None

        if not paused and not clearing and not game_over:
            active_renderer.update(current_piece, dt)
            if now - last_fall >= fall_speed:
                current_piece.y += 1
                if not valid_space(current_piece, locked):
                    current_piece.y -= 1
                    if touching_since is None:
                        touching_since = now
                else:
                    touching_since = None
                    lock_resets = 0
                last_fall = now

            if touching_ground(current_piece, locked):
                if touching_since is None:
                    touching_since = now
                if now - touching_since >= lock_delay:
                    placed_positions, touched_rows = lock_current_piece(current_piece, locked)
                    landed_jelly = LandedJelly(placed_positions, impact=1.0)
                    check_rows = get_full_rows(locked, touched_rows)
                    if check_rows:
                        clearing = True
                        rows_to_clear = check_rows
                        clear_start_time = now
                        clear_chunks_spawned = False
                    else:
                        current_piece = next_piece
                        next_piece = generator.get_piece()
                        active_renderer = ActivePieceRenderer()
                        active_renderer.snap_to_piece(current_piece)
                        ghost_y = get_ghost_y(current_piece, locked)
                        lock_resets = 0
                        if not valid_space(current_piece, locked):
                            game_over = True
                    touching_since = None
            else:
                touching_since = None

        clear_anim = None
        if clearing:
            state = get_clear_anim_state(now, clear_start_time)
            clear_anim = {"rows": rows_to_clear, "phase": state["phase"], "t": state["t"]}
            if state["phase"] == 3 and not clear_chunks_spawned:
                spawn_clear_chunks(space, rows_to_clear, locked.copy(), physics_chunks, phase_strength=1.0 + 0.3 * state["t"])
                clear_chunks_spawned = True

            if now - clear_start_time >= clear_duration:
                cleared_count = remove_rows_and_shift(locked, rows_to_clear)
                total_lines += cleared_count
                old_level = level
                level = min((total_lines // 10) + 1, len(speed_levels))
                fall_speed = speed_levels[level - 1]
                gain = [0, 100, 300, 500, 800][cleared_count] * level
                score += gain
                if cleared_count > 0:
                    floating_texts.append(FloatingText(f"+{gain}", TEXT_COLOR, PLAY_WIDTH // 2, PLAY_HEIGHT // 3, 40))
                if level > old_level:
                    floating_texts.append(FloatingText(f"LEVEL {level}", LEVEL_UP_COLOR, PLAY_WIDTH // 2, PLAY_HEIGHT // 2, 55))
                clearing = False
                rows_to_clear = None
                clear_chunks_spawned = False
                landed_jelly = None
                current_piece = next_piece
                next_piece = generator.get_piece()
                active_renderer = ActivePieceRenderer()
                active_renderer.snap_to_piece(current_piece)
                ghost_y = get_ghost_y(current_piece, locked)
                lock_resets = 0
                if not valid_space(current_piece, locked):
                    game_over = True
                last_fall = pygame.time.get_ticks()

        grid = create_grid(locked)
        draw_window(screen, grid, score, current_piece if not clearing else None, ghost_y, next_piece, paused, level, fall_speed, physics_chunks, active_renderer, total_lines, floating_texts, clear_anim=clear_anim, landed_jelly=landed_jelly)
        if game_over:
            draw_game_over(screen, score)
        pygame.display.flip()


def main():
    while True:
        result = run_game()
        if result != "restart":
            break
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
