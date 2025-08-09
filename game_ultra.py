"""
An enhanced professional 2D platformer with refined artwork and improved level design.

This version builds upon the feature‑rich platformer by introducing
polished pixel art sprites for the player and enemies, smoother
platforms, and more forgiving level layouts. The camera still
scrolls to follow the player across long stages, coins animate and
enemies patrol, and the player has three lives. Sound effects
accompany jumps, coin pickups and damage.

To run the game install ``pygame`` and ensure the following assets
exist in the same directory as this script:

* ``background_v3.png`` – gradient sky with hills
* ``platform_v3.png`` – wide gradient platform
* ``player_idle_v3.png``, ``player_run1_v3.png``,
  ``player_run2_v3.png``, ``player_run3_v3.png`` – improved player frames
* ``enemy_v2.png`` – a green slime enemy
* ``coin_anim1.png`` .. ``coin_anim4.png`` – animated coin frames
* ``heart.png`` – icon for lives
* ``coin.wav``, ``jump.wav``, ``hurt.wav`` – sound effects

The game generates 30 increasingly long levels. Each level includes
platforms of comfortable spacing, animated coins and occasional
enemies. The player's starting position aligns with the first
platform. Collect all coins to advance; avoid enemies or lose a
life. When all lives are spent the game ends.
"""

import os
import sys
import pygame


def load_assets(asset_dir: str) -> dict:
    required_images = [
        'background_v3.png', 'platform_v3.png',
        'player_idle_v3.png', 'player_run1_v3.png',
        'player_run2_v3.png', 'player_run3_v3.png',
        'enemy_v2.png', 'heart.png',
        'coin_anim1.png', 'coin_anim2.png',
        'coin_anim3.png', 'coin_anim4.png',
    ]
    required_sounds = ['coin.wav', 'jump.wav', 'hurt.wav']
    assets: dict[str, object] = {}
    for fname in required_images:
        path = os.path.join(asset_dir, fname)
        if not os.path.isfile(path):
            print(f"Missing image asset: {fname}")
            sys.exit(1)
        assets[fname] = pygame.image.load(path)
    for fname in required_sounds:
        path = os.path.join(asset_dir, fname)
        if not os.path.isfile(path):
            print(f"Missing sound asset: {fname}")
            sys.exit(1)
        assets[fname] = pygame.mixer.Sound(path)
    return assets


class Player:
    def __init__(self, x: int, y: int, frames: list[pygame.Surface], jump_sound: pygame.mixer.Sound) -> None:
        self.rect = pygame.Rect(x, y, frames[0].get_width(), frames[0].get_height())
        self.frames = frames
        self.frame_index = 0
        self.frame_timer = 0
        self.vel_y = 0.0
        self.on_ground = False
        self.jump_sound = jump_sound
    def handle_input(self) -> float:
        keys = pygame.key.get_pressed()
        dx = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -5.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = 5.0
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = -12.0
            self.on_ground = False
            if self.jump_sound:
                self.jump_sound.play()
        return dx
    def apply_gravity(self) -> None:
        self.vel_y += 0.5
        if self.vel_y > 10:
            self.vel_y = 10
    def update(self, platforms: list[pygame.Rect], dx: float) -> None:
        """
        Update the player's position, apply physics and resolve
        collisions.  Horizontal motion is handled first followed by
        gravity and vertical motion.  Collisions on the vertical axis
        are resolved using a two‑step approach: direct collision
        detection to snap onto or bump off of platforms when moving
        vertically, followed by a secondary contact check that keeps
        the player attached to a platform when they are already
        standing on it but minor rounding errors or zero velocity
        prevent an actual rectangle overlap.  This improves the
        reliability of standing on platforms and prevents the player
        from unexpectedly falling through due to small integration
        steps or frame timing.
        """
        # Move horizontally and resolve collisions
        self.rect.x += dx
        for plat in platforms:
            if self.rect.colliderect(plat):
                if dx > 0:
                    # Moving right; clamp to left side of platform
                    self.rect.right = plat.left
                elif dx < 0:
                    # Moving left; clamp to right side of platform
                    self.rect.left = plat.right

        # Apply gravity and update vertical velocity.  Cap downward speed.
        self.apply_gravity()

        # Perform vertical movement
        self.rect.y += self.vel_y

        # Reset grounded state each frame; will be set to True when on a platform.
        self.on_ground = False
        landed = False
        # First pass: resolve any actual rectangle overlaps caused by the vertical move.
        for plat in platforms:
            if self.rect.colliderect(plat):
                if self.vel_y > 0:
                    # Falling down: snap player's feet to platform top
                    self.rect.bottom = plat.top
                    self.vel_y = 0
                    self.on_ground = True
                    landed = True
                elif self.vel_y < 0:
                    # Moving up: bump head on underside of platform
                    self.rect.top = plat.bottom
                    self.vel_y = 0
                # We break here intentionally only for the falling case;
                # but continue checking other overlaps when moving up.
        # Second pass: if we did not land via overlap but vertical
        # velocity has come to rest (i.e. 0), check if the player's
        # feet are aligned with a platform within a small epsilon.  If
        # so, snap to the platform and treat as grounded.  This covers
        # the case where the player's bottom sits exactly at the
        # platform top without overlapping due to discrete movement.
        if not self.on_ground and abs(self.vel_y) < 1e-3:
            for plat in platforms:
                # Check horizontal overlap
                if self.rect.right > plat.left and self.rect.left < plat.right:
                    # Check if we are almost exactly on top of this platform
                    delta = plat.top - self.rect.bottom
                    if 0 <= delta <= 3:
                        self.rect.bottom = plat.top
                        self.on_ground = True
                        break

        # Animate frames: use idle frame when not moving horizontally.  Skip
        # the idle frame when running.
        if dx != 0:
            self.frame_timer += 1
            if self.frame_timer >= 8:
                self.frame_timer = 0
                # Skip frame 0 (idle) when running.  Frames list is
                # [idle, run1, run2, run3]; cycling through run1..run3.
                self.frame_index = (self.frame_index + 1) % (len(self.frames) - 1) + 1
        else:
            self.frame_index = 0
    def draw(self, surface: pygame.Surface, offset_x: float) -> None:
        frame = self.frames[self.frame_index]
        surface.blit(frame, (self.rect.x - offset_x, self.rect.y))
    def reset_position(self, x: int, y: int) -> None:
        """
        Reset the player's position to a given x, y coordinate and
        initialise physics so they start standing on a platform.

        Without explicitly setting the ``on_ground`` flag to ``True``
        after repositioning the character, the first update tick will
        apply gravity and cause the player to drift off the platform
        before collision detection resolves the landing. By marking
        the player as grounded and zeroing the vertical velocity here
        we ensure they stay planted on the platform at the start of
        each level and after respawns.
        """
        self.rect.x = x
        self.rect.y = y
        # Reset vertical velocity so the player isn't moving when spawned
        self.vel_y = 0.0
        # Treat the player as standing on solid ground so gravity won't
        # immediately pull them off the platform on the next frame.
        self.on_ground = True


class AnimatedCoin:
    def __init__(self, x: int, y: int, frames: list[pygame.Surface], sound: pygame.mixer.Sound):
        self.frames = frames
        self.rect = pygame.Rect(x, y, frames[0].get_width(), frames[0].get_height())
        self.frame_index = 0
        self.timer = 0
        self.sound = sound
    def update(self) -> None:
        self.timer += 1
        if self.timer >= 10:
            self.timer = 0
            self.frame_index = (self.frame_index + 1) % len(self.frames)
    def draw(self, surface: pygame.Surface, offset_x: float) -> None:
        surface.blit(self.frames[self.frame_index], (self.rect.x - offset_x, self.rect.y))
    def collect(self) -> None:
        if self.sound:
            self.sound.play()


class Enemy:
    def __init__(self, x: int, platform_y: int, min_x: int, max_x: int, image: pygame.Surface, sound: pygame.mixer.Sound):
        self.rect = pygame.Rect(x, platform_y - image.get_height(), image.get_width(), image.get_height())
        self.min_x = min_x
        self.max_x = max_x
        self.speed = 1.5
        self.image = image
        self.sound = sound
    def update(self) -> None:
        self.rect.x += self.speed
        if self.rect.x < self.min_x or self.rect.x > self.max_x:
            self.speed *= -1
            self.rect.x = max(min(self.rect.x, self.max_x), self.min_x)
    def draw(self, surface: pygame.Surface, offset_x: float) -> None:
        surface.blit(self.image, (self.rect.x - offset_x, self.rect.y))
    def play_sound(self) -> None:
        if self.sound:
            self.sound.play()


def generate_levels(num_levels: int, screen_height: int, platform_img: pygame.Surface,
                    coin_frames: list[pygame.Surface], enemy_img: pygame.Surface) -> list[dict]:
    levels = []
    plat_w = platform_img.get_width()
    enemy_w = enemy_img.get_width()
    coin_w = coin_frames[0].get_width()
    coin_h = coin_frames[0].get_height()
    for i in range(num_levels):
        length = 1600 + 250 * i  # steadily increase length
        base_y = screen_height - platform_img.get_height() - 80
        num_platforms = 10 + i // 3
        step = max(180, (length - 200) // num_platforms)
        platforms = []
        coins = []
        enemies = []
        for j in range(num_platforms):
            x = 100 + j * step
            # smaller vertical variation for easier jumps
            y_offset = -((j % 4) * 30)
            y = base_y + y_offset
            platforms.append((x, y))
            # place coin above every 2nd platform
            if j % 2 == 0:
                coins.append((x + (plat_w - coin_w)//2, y - coin_h - 10))
            # place enemy on every 4th platform
            if j % 4 == 1:
                min_x = x
                max_x = x + plat_w - enemy_w
                enemy_x = x + (plat_w - enemy_w)//2
                enemies.append((enemy_x, y, min_x, max_x))
        levels.append({'platforms': platforms, 'coins': coins, 'enemies': enemies, 'length': length})
    return levels


def main() -> None:
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption("Ultra Platformer")
    screen_width, screen_height = 1000, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    clock = pygame.time.Clock()
    asset_dir = os.path.dirname(__file__)
    assets = load_assets(asset_dir)
    background = assets['background_v3.png']
    platform_img = assets['platform_v3.png']
    player_frames = [
        assets['player_idle_v3.png'],
        assets['player_run1_v3.png'],
        assets['player_run2_v3.png'],
        assets['player_run3_v3.png'],
    ]
    coin_frames = [
        assets['coin_anim1.png'],
        assets['coin_anim2.png'],
        assets['coin_anim3.png'],
        assets['coin_anim4.png'],
    ]
    enemy_img = assets['enemy_v2.png']
    heart_img = assets['heart.png']
    coin_sound = assets['coin.wav']
    jump_sound = assets['jump.wav']
    hurt_sound = assets['hurt.wav']
    # Generate levels
    levels = generate_levels(30, screen_height, platform_img, coin_frames, enemy_img)
    font = pygame.font.SysFont(None, 32)
    current_level = 0
    score = 0
    lives = 3
    game_over = False
    game_completed = False
    def load_level(idx: int):
        data = levels[idx]
        pl_rects = [pygame.Rect(x,y,platform_img.get_width(),platform_img.get_height()) for x,y in data['platforms']]
        coin_objs = [AnimatedCoin(x,y,coin_frames, coin_sound) for x,y in data['coins']]
        enemy_objs = [Enemy(x,py,min_x,max_x, enemy_img, hurt_sound) for (x,py,min_x,max_x) in data['enemies']]
        return pl_rects, coin_objs, enemy_objs, data['length']
    platforms, coins, enemies, level_length = load_level(current_level)
    # align player on first platform
    spawn_x = platforms[0].x + 10
    spawn_y = platforms[0].y - player_frames[0].get_height()
    player = Player(spawn_x, spawn_y, player_frames, jump_sound)
    offset_x = 0.0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
        # handle escape to quit
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE] and (game_over or game_completed):
            return
        if not game_over and not game_completed:
            # movement
            dx = player.handle_input()
            player.update(platforms, dx)
            # coin and enemy updates
            for coin in coins:
                coin.update()
            for enemy in enemies:
                enemy.update()
            # coin collection
            for coin in coins[:]:
                if player.rect.colliderect(coin.rect):
                    score += 1
                    coin.collect()
                    coins.remove(coin)
            # enemy collision
            for enemy in enemies:
                if player.rect.colliderect(enemy.rect):
                    enemy.play_sound()
                    lives -= 1
                    # reset player
                    player.reset_position(spawn_x, spawn_y)
                    offset_x = 0
                    break
            if lives <= 0:
                game_over = True
            # advance level if coins done
            if not coins:
                current_level += 1
                if current_level >= len(levels):
                    game_completed = True
                else:
                    platforms, coins, enemies, level_length = load_level(current_level)
                    spawn_x = platforms[0].x + 10
                    spawn_y = platforms[0].y - player_frames[0].get_height()
                    player.reset_position(spawn_x, spawn_y)
                    offset_x = 0
            # reset if fall
            if player.rect.y > screen_height + 300:
                lives -= 1
                player.reset_position(spawn_x, spawn_y)
                offset_x = 0
                if lives <= 0:
                    game_over = True
            # update camera
            offset_x = player.rect.x - screen_width // 2
            if offset_x < 0:
                offset_x = 0
            max_offset = level_length - screen_width
            if offset_x > max_offset:
                offset_x = max_offset
        # draw background
        bg_w = background.get_width()
        for i in range(int(level_length / bg_w) + 2):
            screen.blit(background, (i * bg_w - offset_x * 0.5, 0))
        # draw platforms
        for plat in platforms:
            screen.blit(platform_img, (plat.x - offset_x, plat.y))
        # draw coins
        for coin in coins:
            coin.draw(screen, offset_x)
        # draw enemies
        for enemy in enemies:
            enemy.draw(screen, offset_x)
        # draw player
        player.draw(screen, offset_x)
        # UI
        score_surf = font.render(f"Score: {score}", True, (0,0,0))
        level_surf = font.render(f"Level: {current_level+1}/{len(levels)}", True, (0,0,0))
        screen.blit(score_surf, (15,15))
        screen.blit(level_surf, (15,45))
        # draw hearts
        for i in range(lives):
            x = screen_width - (i+1)*(heart_img.get_width()+10) - 15
            screen.blit(heart_img, (x, 15))
        if game_over:
            over = font.render("Game Over", True, (200,0,0))
            sub = font.render("Press Esc to exit", True, (0,0,0))
            screen.blit(over, ((screen_width - over.get_width())//2, (screen_height - over.get_height())//2))
            screen.blit(sub, ((screen_width - sub.get_width())//2, (screen_height - sub.get_height())//2 + 40))
        if game_completed:
            win = font.render("You Win!", True, (0,150,0))
            sub = font.render("Press Esc to exit", True, (0,0,0))
            screen.blit(win, ((screen_width - win.get_width())//2, (screen_height - win.get_height())//2))
            screen.blit(sub, ((screen_width - sub.get_width())//2, (screen_height - sub.get_height())//2 + 40))
        pygame.display.flip()
        clock.tick(60)


if __name__ == '__main__':
    main()