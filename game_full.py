"""
A feature‑rich 2D platformer with scrolling camera, animated coins,
enemies, lives, sound effects and polished visuals.

This game is an evolution of the earlier scrolling platformer. It
introduces animated coins, patrolling enemies, a simple three‑life
system, sound effects and an improved background. The camera follows
the player across long multi‑section levels, and a concise heads‑up
display shows the score, remaining lives and current level.

To run the game ensure you have ``pygame`` installed (``pip install
pygame``) and that the asset files created alongside this script are
present in the same directory. These include:

* ``background_v3.png`` – a wide gradient sky with hills and clouds
* ``platform_v2.png`` – the shaded platform
* ``player_idle_v2.png``, ``player_run1_v2.png``, ``player_run2_v2.png``,
  ``player_run3_v2.png`` – frames for the player character
* ``coin_anim1.png`` .. ``coin_anim4.png`` – frames for the animated coin
* ``enemy_v1.png`` – a simple red enemy sprite
* ``heart.png`` – a heart icon used to display lives
* ``coin.wav``, ``jump.wav``, ``hurt.wav`` – sound effects for coin
  collection, jumping and taking damage

The game will automatically generate 30 levels with increasing
complexity. Each level contains platforms, animated coins and enemies
that patrol along platforms. Collecting all coins advances to the
next level. Colliding with an enemy costs one life and resets the
player to the start of the level. Lose all three lives and the game
ends.
"""

import os
import sys
import pygame


def load_assets(asset_dir: str) -> dict:
    """Load all graphical and audio assets from the given directory.

    This function expects a specific set of files to be present. If
    any file is missing the program exits with an informative
    message.

    Parameters
    ----------
    asset_dir: str
        Directory containing the images and sound files.

    Returns
    -------
    dict
        A dictionary mapping asset names to loaded pygame objects.
    """
    required_images = [
        'background_v3.png', 'platform_v2.png',
        'player_idle_v2.png', 'player_run1_v2.png',
        'player_run2_v2.png', 'player_run3_v2.png',
        'enemy_v1.png', 'heart.png',
        'coin_anim1.png', 'coin_anim2.png',
        'coin_anim3.png', 'coin_anim4.png',
    ]
    required_sounds = ['coin.wav', 'jump.wav', 'hurt.wav']
    assets: dict[str, object] = {}
    # Load images
    for fname in required_images:
        path = os.path.join(asset_dir, fname)
        if not os.path.isfile(path):
            print(f"Required image asset '{fname}' missing from {asset_dir}.")
            sys.exit(1)
        assets[fname] = pygame.image.load(path)
    # Load sounds
    for fname in required_sounds:
        path = os.path.join(asset_dir, fname)
        if not os.path.isfile(path):
            print(f"Required sound asset '{fname}' missing from {asset_dir}.")
            sys.exit(1)
        assets[fname] = pygame.mixer.Sound(path)
    return assets


class Player:
    """Main character controlled by the user."""

    def __init__(self, x: int, y: int, frames: list[pygame.Surface], jump_sound: pygame.mixer.Sound) -> None:
        self.rect = pygame.Rect(x, y, frames[0].get_width(), frames[0].get_height())
        self.frames = frames
        self.frame_index = 0
        self.frame_timer = 0
        self.vel_y = 0.0
        self.on_ground = False
        self.jump_sound = jump_sound

    def handle_input(self) -> float:
        """Process keyboard input and return horizontal movement delta."""
        keys = pygame.key.get_pressed()
        dx = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -5.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = 5.0
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vel_y = -12.0
            self.on_ground = False
            if self.jump_sound:
                self.jump_sound.play()
        return dx

    def update(self, platforms: list[pygame.Rect]) -> None:
        """Update the player's position and animation.

        Gravity and collision detection are handled here. Horizontal
        movement is applied externally via the return value of
        ``handle_input``.
        """
        # Apply gravity
        self.vel_y += 0.5
        if self.vel_y > 10:
            self.vel_y = 10

        # Vertical movement
        self.rect.y += self.vel_y
        # Reset on_ground until collision resolves
        self.on_ground = False
        for plat in platforms:
            if self.rect.colliderect(plat):
                # Falling down onto a platform
                if self.vel_y > 0 and self.rect.bottom - self.vel_y <= plat.top:
                    self.rect.bottom = plat.top
                    self.vel_y = 0
                    self.on_ground = True
                # Jumping and hitting the underside
                elif self.vel_y < 0 and self.rect.top - self.vel_y >= plat.bottom:
                    self.rect.top = plat.bottom
                    self.vel_y = 0

        # Animate sprite (frame 0 is idle, others animate during movement)
        self.frame_timer += 1
        if self.frame_timer >= 8:
            self.frame_timer = 0
            self.frame_index = (self.frame_index + 1) % len(self.frames)

    def draw(self, surface: pygame.Surface, offset_x: float) -> None:
        frame = self.frames[self.frame_index]
        surface.blit(frame, (self.rect.x - offset_x, self.rect.y))

    def reset_position(self, x: int, y: int) -> None:
        """Reset the player's position and vertical velocity."""
        self.rect.x = x
        self.rect.y = y
        self.vel_y = 0.0
        self.on_ground = False


class AnimatedCoin:
    """A coin that cycles through animation frames."""
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
    """An enemy that patrols horizontally along a platform."""
    def __init__(self, x: int, platform_y: int, min_x: int, max_x: int, image: pygame.Surface, hurt_sound: pygame.mixer.Sound):
        # Place enemy so it stands on top of the platform
        self.rect = pygame.Rect(
            x,
            platform_y - image.get_height(),
            image.get_width(),
            image.get_height(),
        )
        self.min_x = min_x
        self.max_x = max_x
        self.speed = 2
        self.image = image
        self.hurt_sound = hurt_sound
    def update(self) -> None:
        self.rect.x += self.speed
        if self.rect.x < self.min_x or self.rect.x > self.max_x:
            self.speed *= -1
            # clamp inside bounds to avoid overshoot
            self.rect.x = max(min(self.rect.x, self.max_x), self.min_x)
    def draw(self, surface: pygame.Surface, offset_x: float) -> None:
        surface.blit(self.image, (self.rect.x - offset_x, self.rect.y))
    def play_sound(self) -> None:
        if self.hurt_sound:
            self.hurt_sound.play()


def generate_levels(num_levels: int, screen_height: int, platform_img: pygame.Surface,
                    coin_frames: list[pygame.Surface], enemy_img: pygame.Surface) -> list[dict[str, object]]:
    """Generate level data including platforms, coins and enemies.

    Each level is progressively longer and contains more platforms,
    coins and occasional enemies. Coins appear on every other
    platform, enemies appear on every third platform.

    Returns a list where each element is a dict with keys
    'platforms', 'coins', 'enemies', and 'length'.
    """
    levels: list[dict[str, object]] = []
    for i in range(num_levels):
        level_length = 1400 + 300 * i
        base_y = screen_height - platform_img.get_height() - 40
        num_platforms = 8 + i // 2
        step_x = max(220, (level_length - 200) // num_platforms)
        platforms: list[tuple[int, int]] = []
        coins: list[tuple[int, int]] = []
        enemies: list[tuple[int, int, int, int]] = []
        # Determine enemy width for boundaries
        enemy_w = enemy_img.get_width()
        plat_w = platform_img.get_width()
        coin_w = coin_frames[0].get_width()
        coin_h = coin_frames[0].get_height()
        for j in range(num_platforms):
            x = 100 + j * step_x
            y_offset = -((j % 5) * 40)
            y = base_y + y_offset
            platforms.append((x, y))
            # coin on every second platform
            if j % 2 == 0:
                coin_x = x + (plat_w - coin_w) // 2
                coin_y = y - coin_h - 10
                coins.append((coin_x, coin_y))
            # enemy on every third platform
            if j % 3 == 1:
                enemy_x = x + (plat_w - enemy_w) // 2
                min_x = x
                max_x = x + plat_w - enemy_w
                enemies.append((enemy_x, y, min_x, max_x))
        levels.append({'platforms': platforms, 'coins': coins, 'enemies': enemies, 'length': level_length})
    return levels


def main() -> None:
    """Entry point of the full feature platformer."""
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption("Professional 2D Platformer")
    screen_width = 1000
    screen_height = 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    clock = pygame.time.Clock()

    # Asset loading
    asset_dir = os.path.dirname(__file__)
    assets = load_assets(asset_dir)
    background = assets['background_v3.png']
    platform_img = assets['platform_v2.png']
    player_frames = [
        assets['player_idle_v2.png'],
        assets['player_run1_v2.png'],
        assets['player_run2_v2.png'],
        assets['player_run3_v2.png'],
    ]
    coin_frames = [
        assets['coin_anim1.png'],
        assets['coin_anim2.png'],
        assets['coin_anim3.png'],
        assets['coin_anim4.png'],
    ]
    enemy_img = assets['enemy_v1.png']
    heart_img = assets['heart.png']
    # Sounds
    coin_sound = assets['coin.wav']
    jump_sound = assets['jump.wav']
    hurt_sound = assets['hurt.wav']

    # Generate levels
    levels = generate_levels(
        num_levels=30,
        screen_height=screen_height,
        platform_img=platform_img,
        coin_frames=coin_frames,
        enemy_img=enemy_img,
    )

    # Font
    font = pygame.font.SysFont(None, 36)

    # Game state
    current_level = 0
    score = 0
    lives = 3
    game_over = False
    game_completed = False

    def load_level(index: int):
        data = levels[index]
        pl_rects = [
            pygame.Rect(x, y, platform_img.get_width(), platform_img.get_height())
            for x, y in data['platforms']
        ]
        coin_objs = [AnimatedCoin(x, y, coin_frames, coin_sound) for x, y in data['coins']]
        enemy_objs = [
            Enemy(x, py, min_x, max_x, enemy_img, hurt_sound)
            for (x, py, min_x, max_x) in data['enemies']
        ]
        return pl_rects, coin_objs, enemy_objs, data['length']

    platforms, coins, enemies, level_length = load_level(current_level)
    player = Player(100, screen_height - 200, player_frames, jump_sound)
    offset_x = 0.0

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

        if not game_over and not game_completed:
            # Input
            dx = player.handle_input()
            # Horizontal movement
            player.rect.x += dx
            # Prevent leaving world boundaries horizontally
            if player.rect.x < 0:
                player.rect.x = 0
            if player.rect.x > level_length - player.rect.width:
                player.rect.x = level_length - player.rect.width
            # Apply gravity and vertical movement/collisions
            player.update(platforms)

            # Update coins and enemies
            for coin in coins:
                coin.update()
            for enemy in enemies:
                enemy.update()

            # Check coin collection
            for coin in coins[:]:
                if player.rect.colliderect(coin.rect):
                    score += 1
                    coin.collect()
                    coins.remove(coin)

            # Check enemy collision
            for enemy in enemies:
                if player.rect.colliderect(enemy.rect):
                    enemy.play_sound()
                    lives -= 1
                    # reset to start of level
                    player.reset_position(100, screen_height - 200)
                    offset_x = 0
                    break
            # Check lives
            if lives <= 0:
                game_over = True

            # Check if all coins collected
            if not coins:
                current_level += 1
                if current_level >= len(levels):
                    game_completed = True
                else:
                    platforms, coins, enemies, level_length = load_level(current_level)
                    player.reset_position(100, screen_height - 200)
                    offset_x = 0

            # Reset if fall
            if player.rect.y > screen_height + 300:
                # lose a life and reset
                lives -= 1
                player.reset_position(100, screen_height - 200)
                offset_x = 0
                if lives <= 0:
                    game_over = True

            # Update camera offset
            offset_x = player.rect.x - screen_width // 2
            if offset_x < 0:
                offset_x = 0
            max_offset = level_length - screen_width
            if offset_x > max_offset:
                offset_x = max_offset

        # Drawing
        # Draw scrolling background with parallax
        bg_width = background.get_width()
        for i in range(int(level_length / bg_width) + 2):
            screen.blit(background, (i * bg_width - offset_x * 0.5, 0))
        # Platforms
        for plat in platforms:
            screen.blit(platform_img, (plat.x - offset_x, plat.y))
        # Coins
        for coin in coins:
            coin.draw(screen, offset_x)
        # Enemies
        for enemy in enemies:
            enemy.draw(screen, offset_x)
        # Player
        player.draw(screen, offset_x)
        # UI: score and level
        score_surf = font.render(f"Score: {score}", True, (0, 0, 0))
        level_surf = font.render(f"Level: {current_level + 1} / {len(levels)}", True, (0, 0, 0))
        screen.blit(score_surf, (15, 15))
        screen.blit(level_surf, (15, 50))
        # Draw lives as hearts
        for i in range(lives):
            x = screen_width - (i + 1) * (heart_img.get_width() + 10) - 15
            y = 15
            screen.blit(heart_img, (x, y))

        # Game over or completion messages
        if game_over:
            msg = font.render("Game Over", True, (200, 0, 0))
            sub = font.render("Press Esc to exit", True, (0, 0, 0))
            screen.blit(msg, ((screen_width - msg.get_width()) // 2, (screen_height - msg.get_height()) // 2))
            screen.blit(sub, ((screen_width - sub.get_width()) // 2, (screen_height - sub.get_height()) // 2 + 40))
        if game_completed:
            msg = font.render("Congratulations! You won!", True, (0, 150, 0))
            sub = font.render("Press Esc to exit", True, (0, 0, 0))
            screen.blit(msg, ((screen_width - msg.get_width()) // 2, (screen_height - msg.get_height()) // 2))
            screen.blit(sub, ((screen_width - sub.get_width()) // 2, (screen_height - sub.get_height()) // 2 + 40))

        pygame.display.flip()
        clock.tick(60)

        # Allow escape key to quit when game is over/completed
        if game_over or game_completed:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]:
                return


if __name__ == "__main__":
    main()