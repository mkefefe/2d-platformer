"""
Enhanced 2D Platformer Game
--------------------------------

This script implements a side‑scrolling platformer with a scrolling camera,
multiple procedurally generated levels, animated sprites, coin collection,
enemy patrol behaviour, attack mechanics and a simple lives system. When the
player loses all lives, a retry screen is shown allowing them to start
again. When all levels are completed, a win screen is displayed.

Assets used in this game are located in the ``detailed_assets`` folder.
They include:

    * player_idle.png – idle frame for the player
    * player_run1.png, player_run2.png, player_run3.png – walking cycle
    * player_jump.png – frame used when jumping
    * player_attack.png – frame used when attacking
    * enemy.png – simple enemy sprite
    * platform.png – tile used for platforms
    * background.png – repeating background for the level
    * coin_1.png .. coin_4.png – animated coin frames
    * heart.png – used to draw life icons at the top of the screen

Gameplay overview:

* The player can move left and right with the arrow keys or A/D. Spacebar
  makes the player jump. Pressing F performs an attack. While attacking the
  player cannot move but will defeat any enemies they touch.
* Collecting all coins on a level moves the player to the next level. There
  are 30 levels generated algorithmically with increasing width and more
  platforms. Completing them all displays a congratulatory message.
* Each level spawns a handful of patrolling enemies. If the player touches an
  enemy without attacking they lose a life. The player begins with three
  hearts; when all hearts are gone a game over screen is shown. Pressing
  R on this screen restarts the game from the first level.
* The camera follows the player horizontally and ensures the action stays
  centred in the viewport. A parallax background scrolls alongside the
  foreground platforms.

This code requires the ``pygame`` library. Install with ``pip install pygame``
before running. Run the script from the repository root:

    python game_final.py

"""

import os
import random
import sys
from typing import List

import pygame


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------
SCREEN_WIDTH, SCREEN_HEIGHT = 1000, 600
FPS = 60
GRAVITY = 0.8
PLAYER_SPEED = 5
PLAYER_JUMP_VELOCITY = -16
ATTACK_DURATION = 15  # frames that attack animation is active
ENEMY_SPEED = 2
LEVEL_COUNT = 30

# Asset directory relative to this script. All art assets (player frames,
# enemy, platform, background, coin frames, heart) are expected to live
# alongside this file in the repository root. Previously the code assumed
# they resided in a subfolder called ``detailed_assets``, but to simplify
# distribution the assets are now read from the same directory as this
# script. If you wish to organise assets into a subfolder, set
# ``ASSET_DIR`` accordingly and move the files.
ASSET_DIR = os.path.dirname(__file__)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
def load_image(name: str) -> pygame.Surface:
    """Load an image from the asset directory and convert for blitting."""
    path = os.path.join(ASSET_DIR, name)
    image = pygame.image.load(path).convert_alpha()
    return image


def flip_images(images: List[pygame.Surface]) -> List[pygame.Surface]:
    """Return a new list of images flipped horizontally."""
    return [pygame.transform.flip(img, True, False) for img in images]


# ---------------------------------------------------------------------------
# Sprite classes
# ---------------------------------------------------------------------------
class Platform(pygame.sprite.Sprite):
    """Simple platform sprite that the player and enemies can stand on."""

    def __init__(self, x: int, y: int, image: pygame.Surface):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))


class Coin(pygame.sprite.Sprite):
    """Animated coin that can be collected by the player."""

    def __init__(self, x: int, y: int, frames: List[pygame.Surface]):
        super().__init__()
        self.frames = frames
        self.frame_index = 0
        self.image = self.frames[self.frame_index]
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.animation_counter = 0

    def update(self, *args):  # noqa: D401
        """Advance the coin animation."""
        self.animation_counter += 1
        if self.animation_counter % 10 == 0:
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.image = self.frames[self.frame_index]


class Enemy(pygame.sprite.Sprite):
    """Enemy that patrols back and forth across platforms."""

    def __init__(self, x: int, y: int, platforms: pygame.sprite.Group,
                 image: pygame.Surface):
        super().__init__()
        self.image_right = image
        self.image_left = pygame.transform.flip(image, True, False)
        self.image = self.image_right
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.direction = random.choice([-1, 1])  # -1 = left, 1 = right
        self.platforms = platforms
        self.speed = ENEMY_SPEED

    def update(self, camera_dx: int):  # noqa: D401
        """Move the enemy and flip direction when reaching platform edges."""
        # apply horizontal movement
        self.rect.x += self.direction * self.speed

        # Determine if the enemy is still on a platform
        # We shift the rect down slightly to check if there is ground beneath
        below = self.rect.copy()
        below.y += 5
        on_platform = False
        for platform in self.platforms:
            if below.colliderect(platform.rect):
                on_platform = True
                break

        # If no platform below or at edge of platform, flip direction
        if not on_platform:
            self.direction *= -1
            self.rect.x += self.direction * self.speed * 2  # step away from edge

        # Choose appropriate sprite orientation
        if self.direction < 0:
            self.image = self.image_left
        else:
            self.image = self.image_right
        
        # Apply camera shift
        self.rect.x -= camera_dx


class Player(pygame.sprite.Sprite):
    """Player character with movement, jump, attack and animation logic."""

    def __init__(self, x: int, y: int, platforms: pygame.sprite.Group,
                 coins: pygame.sprite.Group, enemies: pygame.sprite.Group,
                 images_right: List[pygame.Surface], images_left: List[pygame.Surface]):
        super().__init__()
        # animation frames for different states
        self.images_right = images_right
        self.images_left = images_left
        # indices: 0 = idle, 1-3 = run, 4 = jump, 5 = attack
        self.frame_index = 0
        self.direction = 1  # 1 = right, -1 = left
        self.image = self.images_right[self.frame_index]
        self.rect = self.image.get_rect(midbottom=(x, y))
        
        # movement attributes
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        
        self.platforms = platforms
        self.coins = coins
        self.enemies = enemies

        # combat
        self.attacking = False
        self.attack_timer = 0

        # player state
        self.lives = 3
        self.score = 0

    def handle_input(self, keys):
        """Process keyboard input for movement and attack."""
        if not self.attacking:
            # movement input
            self.vel_x = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.vel_x = -PLAYER_SPEED
                self.direction = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.vel_x = PLAYER_SPEED
                self.direction = 1
            # jump input
            if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
                self.vel_y = PLAYER_JUMP_VELOCITY
                self.on_ground = False
            # attack input
            if keys[pygame.K_f]:
                self.attacking = True
                self.attack_timer = ATTACK_DURATION

    def update(self):  # noqa: D401
        """Update position, handle collisions, animate and resolve interactions."""
        # Apply gravity
        self.vel_y += GRAVITY
        
        # Horizontal movement
        self.rect.x += self.vel_x
        self.handle_horizontal_collisions()
        
        # Vertical movement
        self.rect.y += self.vel_y
        self.handle_vertical_collisions()

        # Collect coins
        coin_hits = pygame.sprite.spritecollide(self, self.coins, True)
        if coin_hits:
            self.score += len(coin_hits)
        
        # Collide with enemies
        enemy_hits = pygame.sprite.spritecollide(self, self.enemies, False)
        for enemy in enemy_hits:
            if self.attacking:
                # remove enemy
                enemy.kill()
            else:
                # hurt player and reset position
                self.lives -= 1
                # small knockback
                self.rect.x -= self.direction * 20
                # reposition player on nearest platform top or spawn position
                self.vel_y = 0
                self.on_ground = False
                break

        # Update attack timer
        if self.attacking:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attacking = False

        # Animation logic
        self.animate()

    def handle_horizontal_collisions(self):
        """Resolve horizontal collisions with platforms."""
        collisions = pygame.sprite.spritecollide(self, self.platforms, False)
        for plat in collisions:
            if self.vel_x > 0:
                self.rect.right = plat.rect.left
            elif self.vel_x < 0:
                self.rect.left = plat.rect.right

    def handle_vertical_collisions(self):
        """Resolve vertical collisions with platforms using a two‑pass approach.

        The first pass snaps the player onto or bumps them off of
        platforms when their rectangle overlaps a platform due to
        vertical motion. If the player is falling and overlaps a
        platform from above, their feet are clamped to the platform
        top and their vertical velocity is reset; if they collide
        while moving upward their head is bumped on the underside
        of the platform. A secondary check handles cases where the
        player is exactly aligned with a platform without an actual
        rectangle overlap (e.g. due to discrete movement steps or
        rounding). In that case we test for horizontal overlap and
        snap the player's feet to the platform if they are within a
        small threshold below it. This prevents the player from
        unexpectedly falling off platforms when their velocity
        reaches zero and improves the reliability of standing on
        platforms.
        """
        # Reset grounded state each frame
        self.on_ground = False
        # First pass: resolve actual overlaps from vertical motion
        collisions = pygame.sprite.spritecollide(self, self.platforms, False)
        for plat in collisions:
            if self.vel_y > 0:
                # Falling down; clamp feet to platform top
                self.rect.bottom = plat.rect.top
                self.vel_y = 0
                self.on_ground = True
            elif self.vel_y < 0:
                # Moving up; bump head on underside
                self.rect.top = plat.rect.bottom
                self.vel_y = 0
        # Second pass: if we didn't land via overlap but our vertical
        # velocity is nearly zero, check if we're almost exactly on a
        # platform. Snap to its top if so to stay grounded.
        if not self.on_ground and abs(self.vel_y) < 1e-3:
            for plat in self.platforms:
                # horizontal overlap check
                if self.rect.right > plat.rect.left and self.rect.left < plat.rect.right:
                    delta = plat.rect.top - self.rect.bottom
                    if 0 <= delta <= 3:
                        self.rect.bottom = plat.rect.top
                        self.on_ground = True
                        break

    def animate(self):
        """Choose the correct frame based on movement and action."""
        # Determine which image set to use based on facing direction
        images = self.images_right if self.direction > 0 else self.images_left
        
        # Attack overrides all other animations
        if self.attacking:
            self.frame_index = 5
        else:
            if not self.on_ground:
                self.frame_index = 4  # jump
            elif self.vel_x != 0:
                # cycling through run frames 1-3
                run_cycle = [1, 2, 3]
                # increment animation timer based on time
                frame = int(pygame.time.get_ticks() / 100) % len(run_cycle)
                self.frame_index = run_cycle[frame]
            else:
                self.frame_index = 0  # idle
        self.image = images[self.frame_index]


# ---------------------------------------------------------------------------
# Game class encapsulating the entire game loop and logic
# ---------------------------------------------------------------------------
class Game:
    """Top‑level game class to encapsulate state and behaviour."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('2D Platformer Game')
        self.clock = pygame.time.Clock()
        self.running = True

        # Load assets
        self.platform_img = load_image('platform.png')
        self.background_img = load_image('background.png')
        # Load and scale to screen height for parallax effect
        self.bg_scaled = pygame.transform.scale(self.background_img, (self.background_img.get_width(), SCREEN_HEIGHT))
        
        # Player images
        right_frames = [
            load_image('player_idle.png'),
            load_image('player_run1.png'),
            load_image('player_run2.png'),
            load_image('player_run3.png'),
            load_image('player_jump.png'),
            load_image('player_attack.png'),
        ]
        left_frames = flip_images(right_frames)
        
        # Coin frames
        self.coin_frames = [load_image(f'coin_{i}.png') for i in range(1, 5)]
        
        # Enemy image
        self.enemy_img = load_image('enemy.png')
        
        # Hearts for lives display
        self.heart_img = load_image('heart.png')
        self.heart_img = pygame.transform.scale(self.heart_img, (24, 24))
        
        # Sprite groups
        self.platforms = pygame.sprite.Group()
        self.coins = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.all_sprites = pygame.sprite.Group()
        
        # Player
        # Placeholder spawn will be updated after loading level
        self.player = Player(100, 100, self.platforms, self.coins, self.enemies,
                             right_frames, left_frames)
        self.all_sprites.add(self.player)
        
        # Level management
        self.level_index = 0
        self.levels = self.generate_levels(LEVEL_COUNT)
        self.load_level(self.level_index)
        
        # Game state flags
        self.game_over = False
        self.game_won = False

    def generate_levels(self, count: int) -> List[List[tuple]]:
        """Generate a list of level data; each level is a list of platform tuples (x, y)."""
        levels = []
        base_width = 2000  # starting width
        for i in range(count):
            width = base_width + i * 400  # gradually increase level length
            level_platforms = []
            # ground platform spanning entire level
            level_platforms.append((0, SCREEN_HEIGHT - 40))
            # randomly place platforms above ground
            random.seed(i)
            platform_count = 8 + i // 2
            for p in range(platform_count):
                x = random.randint(50, width - 200)
                # vary height between 200 and SCREEN_HEIGHT - 150
                y = random.randint(200, SCREEN_HEIGHT - 150)
                level_platforms.append((x, y))
            levels.append(level_platforms)
        return levels

    def load_level(self, index: int):
        """Load level by index, resetting sprite groups and placing objects."""
        self.platforms.empty()
        self.coins.empty()
        self.enemies.empty()
        # Remove all sprites except player from all_sprites
        for sprite in list(self.all_sprites):
            if sprite is not self.player:
                self.all_sprites.remove(sprite)
        
        # Level data
        level_platforms = self.levels[index]
        # Determine world width as farthest platform plus margin
        self.world_width = max([x for x, _ in level_platforms]) + 500
        
        # Resize background to span the entire level width.  This
        # creates a large static backdrop that is revealed as the
        # camera scrolls horizontally.  Without this call the
        # background would only span the screen width and would
        # appear to move relative to the platforms.
        self.bg_scaled = pygame.transform.scale(self.background_img,
                                                (self.world_width, SCREEN_HEIGHT))
        
        # Spawn platforms
        for x, y in level_platforms:
            # If y is bottom (ground), tile the platform across the level
            if y >= SCREEN_HEIGHT - 40:
                # tile across width
                for tx in range(0, self.world_width, self.platform_img.get_width()):
                    plat = Platform(tx, y, self.platform_img)
                    self.platforms.add(plat)
                    self.all_sprites.add(plat)
            else:
                plat = Platform(x, y, self.platform_img)
                self.platforms.add(plat)
                self.all_sprites.add(plat)
        
        # Spawn coins randomly on some platforms (not ground)
        coin_count = 6 + index // 2
        platform_list = [p for p in self.platforms if p.rect.y < SCREEN_HEIGHT - 50]
        random.seed(index + 100)
        for _ in range(min(coin_count, len(platform_list))):
            plat = random.choice(platform_list)
            coin_x = plat.rect.centerx
            coin_y = plat.rect.top
            coin = Coin(coin_x, coin_y, self.coin_frames)
            self.coins.add(coin)
            self.all_sprites.add(coin)
        
        # Spawn enemies on some platforms (not ground)
        enemy_count = 3 + index // 3
        random.seed(index + 200)
        for _ in range(min(enemy_count, len(platform_list))):
            plat = random.choice(platform_list)
            ex = plat.rect.centerx
            ey = plat.rect.top
            enemy = Enemy(ex, ey, self.platforms, self.enemy_img)
            self.enemies.add(enemy)
            self.all_sprites.add(enemy)
        
        # Position player on first platform (not ground) or fallback
        spawn_plats = [p for p in self.platforms if p.rect.y < SCREEN_HEIGHT - 50]
        if spawn_plats:
            spawn_plats.sort(key=lambda p: (p.rect.y, p.rect.x))
            plat = spawn_plats[0]
            self.player.rect.midbottom = (plat.rect.x + 20, plat.rect.top)
            self.player.vel_y = 0
        else:
            # default spawn
            self.player.rect.midbottom = (50, SCREEN_HEIGHT - 50)
        
        # Reset player state
        self.player.score = 0
        self.player.lives = 3
        self.game_over = False
        self.game_won = False

    def handle_game_over(self):
        """Display game over screen and wait for restart key."""
        font = pygame.font.SysFont('Arial', 48)
        small_font = pygame.font.SysFont('Arial', 24)
        game_over_text = font.render('Game Over', True, (255, 255, 255))
        retry_text = small_font.render('Press R to Try Again', True, (200, 200, 200))
        self.screen.blit(game_over_text, ((SCREEN_WIDTH - game_over_text.get_width()) // 2,
                                          SCREEN_HEIGHT // 3))
        self.screen.blit(retry_text, ((SCREEN_WIDTH - retry_text.get_width()) // 2,
                                      SCREEN_HEIGHT // 2))
        pygame.display.flip()
        waiting = True
        while waiting and self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    waiting = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    # restart game
                    self.level_index = 0
                    self.load_level(self.level_index)
                    waiting = False
            self.clock.tick(FPS)

    def handle_win(self):
        """Display win screen and wait for restart key."""
        font = pygame.font.SysFont('Arial', 48)
        small_font = pygame.font.SysFont('Arial', 24)
        win_text = font.render('You Win!', True, (255, 255, 255))
        retry_text = small_font.render('Press R to Play Again', True, (200, 200, 200))
        self.screen.blit(win_text, ((SCREEN_WIDTH - win_text.get_width()) // 2,
                                    SCREEN_HEIGHT // 3))
        self.screen.blit(retry_text, ((SCREEN_WIDTH - retry_text.get_width()) // 2,
                                      SCREEN_HEIGHT // 2))
        pygame.display.flip()
        waiting = True
        while waiting and self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    waiting = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    self.level_index = 0
                    self.load_level(self.level_index)
                    waiting = False
            self.clock.tick(FPS)

    def run(self):
        """Main game loop."""
        while self.running:
            # Event handling
            keys = pygame.key.get_pressed()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            
            # Handle input for player
            if not self.game_over and not self.game_won:
                self.player.handle_input(keys)
            
            # Update entities only if game is active
            if not self.game_over and not self.game_won:
                # Update camera offset based on player position
                camera_x = self.player.rect.centerx - SCREEN_WIDTH // 2
                # Clamp camera
                camera_x = max(0, min(camera_x, self.world_width - SCREEN_WIDTH))
                # Horizontal delta for this frame: how much the world has shifted
                camera_dx = camera_x - getattr(self, 'last_camera_x', 0)
                self.last_camera_x = camera_x
                
                # Update sprites
                self.player.update()
                for enemy in self.enemies:
                    enemy.update(camera_dx)
                self.coins.update()
                
                # Shift all platforms, coins, enemies relative to camera
                for sprite in self.platforms:
                    sprite.rect.x -= camera_dx
                for sprite in self.coins:
                    sprite.rect.x -= camera_dx
                # Player shift done via drawing; we keep player's rect in world space
                
                # Check for level completion
                if len(self.coins) == 0 and not self.game_over:
                    self.level_index += 1
                    if self.level_index >= len(self.levels):
                        self.game_won = True
                    else:
                        self.load_level(self.level_index)
                        continue
                
                # Check for falling off screen
                if self.player.rect.top > SCREEN_HEIGHT:
                    self.player.lives -= 1
                    # respawn on starting platform
                    spawn_plats = [p for p in self.platforms if p.rect.y < SCREEN_HEIGHT - 50]
                    if spawn_plats:
                        plat = spawn_plats[0]
                        self.player.rect.midbottom = (plat.rect.x + 20, plat.rect.top)
                        self.player.vel_y = 0
                        self.player.on_ground = True
                    if self.player.lives <= 0:
                        self.game_over = True
            
            # Draw everything
            # Draw background: a large static backdrop anchored to world
            # position.  We shift it horizontally by the camera offset
            # so that it moves in sync with the level instead of
            # exhibiting a parallax effect.
            cam_x = getattr(self, 'last_camera_x', 0)
            self.screen.blit(self.bg_scaled, (-cam_x, 0))
            
            # Draw sprites relative to camera
            for sprite in self.platforms:
                self.screen.blit(sprite.image, sprite.rect)
            for coin in self.coins:
                self.screen.blit(coin.image, coin.rect)
            for enemy in self.enemies:
                self.screen.blit(enemy.image, enemy.rect)
            # Draw player
            # Player sprite in world space; adjust drawing position by camera_x
            player_draw_x = self.player.rect.x - getattr(self, 'last_camera_x', 0)
            self.screen.blit(self.player.image, (player_draw_x, self.player.rect.y))
            
            # Draw HUD: lives and score
            for i in range(self.player.lives):
                self.screen.blit(self.heart_img, (10 + i * 28, 10))
            # Score text
            score_font = pygame.font.SysFont('Arial', 24)
            score_surf = score_font.render(f'Score: {self.player.score}', True, (255, 255, 255))
            self.screen.blit(score_surf, (10, 40))
            # Level indicator
            level_surf = score_font.render(f'Level: {self.level_index + 1}/{LEVEL_COUNT}', True, (255, 255, 255))
            self.screen.blit(level_surf, (10, 70))
            
            # Flip display
            pygame.display.flip()
            
            # Handle game over and win screens
            if self.game_over:
                self.handle_game_over()
            elif self.game_won:
                self.handle_win()
            
            self.clock.tick(FPS)


if __name__ == '__main__':
    Game().run()