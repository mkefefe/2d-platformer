"""
game_enhanced.py
-----------------

An expanded 2D platformer built with Pygame. This version uses improved
sprites and backgrounds, adds larger levels and multiple stages, and keeps
track of the player's score. The game loads art assets from the project
directory, draws a scrolling‐style level on a single screen, and cycles
through a list of predefined level layouts once all coins are collected.

Instructions:
  • Install Pygame if you haven't already: ``pip install pygame``.
  • Run this script with ``python game_enhanced.py``.
  • Use the left/right arrow keys to move and spacebar to jump.
  • Collect all the coins to advance to the next level. When all levels
    are finished the game displays a completion message and exits.
"""

import os
import sys
import pygame


def load_image(asset_dir: str, filename: str) -> pygame.Surface:
    """Load an image from disk.

    Args:
        asset_dir: Directory where assets are stored.
        filename: Name of the image file to load.

    Returns:
        A pygame.Surface containing the loaded image.
    """
    path = os.path.join(asset_dir, filename)
    try:
        return pygame.image.load(path)
    except pygame.error as exc:
        raise SystemExit(f"Unable to load image {filename}: {exc}")


class Player(pygame.sprite.Sprite):
    """Player sprite implementing simple physics and animation."""

    def __init__(self, images: list[pygame.Surface], start_pos: tuple[int, int]) -> None:
        super().__init__()
        self.images = images
        self.index = 0
        self.image = self.images[self.index]
        self.rect = self.image.get_rect()
        self.rect.topleft = start_pos
        self.vel_y = 0.0
        self.speed = 5
        self.on_ground = False
        self.frame_timer = 0

    def update(self, platforms: pygame.sprite.Group) -> None:
        """Update the player's position, handle animation and collisions."""
        keys = pygame.key.get_pressed()
        dx = 0
        dy = 0

        # Horizontal movement
        if keys[pygame.K_LEFT]:
            dx = -self.speed
        if keys[pygame.K_RIGHT]:
            dx = self.speed

        # Jumping
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = -15
            self.on_ground = False

        # Apply gravity
        self.vel_y += 0.5
        dy += self.vel_y

        # Collision detection with platforms
        self.on_ground = False
        # horizontal movement
        self.rect.x += dx
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if dx > 0:
                    self.rect.right = platform.rect.left
                elif dx < 0:
                    self.rect.left = platform.rect.right

        # vertical movement
        self.rect.y += dy
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if dy > 0:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif dy < 0:
                    self.rect.top = platform.rect.bottom
                    self.vel_y = 0

        # Animation frames: run frames when moving; idle frame when stationary
        if dx != 0:
            self.frame_timer += 1
            if self.frame_timer >= 10:
                self.frame_timer = 0
                self.index = (self.index - 1) % 2 + 1  # cycle between run frames 1 and 2 (indices 1 and 2)
        else:
            self.index = 0
            self.frame_timer = 0

        self.image = self.images[self.index]


class Platform(pygame.sprite.Sprite):
    """Platform sprite representing a solid surface."""

    def __init__(self, image: pygame.Surface, pos: tuple[int, int]) -> None:
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(topleft=pos)


class Coin(pygame.sprite.Sprite):
    """Coin sprite which can be collected by the player."""

    def __init__(self, image: pygame.Surface, pos: tuple[int, int]) -> None:
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(center=pos)


def load_level(level_index: int,
               levels: list[dict[str, list[tuple[int, int]]]],
               platform_img: pygame.Surface,
               coin_img: pygame.Surface,
               all_sprites: pygame.sprite.Group,
               platforms: pygame.sprite.Group,
               coins: pygame.sprite.Group) -> None:
    """Load a level from the levels data into sprite groups.

    Args:
        level_index: Index of the level to load.
        levels: List of level definitions.
        platform_img: Image for platforms.
        coin_img: Image for coins.
        all_sprites: Group to which all sprites are added.
        platforms: Group to which platforms are added.
        coins: Group to which coins are added.
    """
    # Clear existing platforms and coins
    platforms.empty()
    coins.empty()

    level = levels[level_index]
    # Create platforms
    for pos in level['platforms']:
        plat = Platform(platform_img, pos)
        platforms.add(plat)
        all_sprites.add(plat)
    # Create coins
    for pos in level['coins']:
        coin = Coin(coin_img, pos)
        coins.add(coin)
        all_sprites.add(coin)


def main() -> None:
    """Entry point for the enhanced 2D platformer game."""
    pygame.init()

    # Screen settings (bigger level)
    SCREEN_WIDTH = 1000
    SCREEN_HEIGHT = 600
    FPS = 60

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('2D Platformer Game - Enhanced')
    clock = pygame.time.Clock()

    # Directories for assets
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSET_DIR = BASE_DIR  # assets are stored in the repository root

    # Load images
    background_img = load_image(ASSET_DIR, 'background_v2.png')
    player_idle = load_image(ASSET_DIR, 'player_idle_v2.png')
    player_run1 = load_image(ASSET_DIR, 'player_run1_v2.png')
    player_run2 = load_image(ASSET_DIR, 'player_run2_v2.png')
    platform_img = load_image(ASSET_DIR, 'platform_v2.png')
    coin_img = load_image(ASSET_DIR, 'coin_v2.png')

    # Scale platform and background to appropriate sizes if necessary
    # For this example, platform image is already wide enough; background matches screen size
    background_img = pygame.transform.scale(background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))

    # Player sprites
    player_images = [player_idle, player_run1, player_run2]
    player = Player(player_images, (50, SCREEN_HEIGHT - 150))

    # Sprite groups
    all_sprites = pygame.sprite.Group()
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()

    all_sprites.add(player)

    # Define multiple levels (platform positions are top-left of platform images; coins use center positions)
    levels = [
        {
            'platforms': [
                (0, SCREEN_HEIGHT - 40),
                (150, 500), (350, 450), (550, 400), (750, 350), (950, 300)
            ],
            'coins': [
                (200, 470), (400, 420), (600, 370), (800, 320), (1000, 270)
            ]
        },
        {
            'platforms': [
                (0, SCREEN_HEIGHT - 40),
                (100, 500), (300, 450), (500, 500), (700, 450), (900, 400)
            ],
            'coins': [
                (150, 470), (350, 420), (550, 470), (750, 420), (950, 370)
            ]
        }
    ]

    level_index = 0
    score = 0
    font = pygame.font.SysFont(None, 36)

    # Load the first level
    load_level(level_index, levels, platform_img, coin_img, all_sprites, platforms, coins)

    running = True
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Update player
        player.update(platforms)

        # Check coin collisions
        coin_hits = pygame.sprite.spritecollide(player, coins, dokill=True)
        if coin_hits:
            score += len(coin_hits)

        # If all coins are collected, advance to next level or finish
        if not coins:
            level_index += 1
            if level_index >= len(levels):
                # Game completed
                running = False
            else:
                # Load next level
                load_level(level_index, levels, platform_img, coin_img, all_sprites, platforms, coins)
                # Reset player position
                player.rect.topleft = (50, SCREEN_HEIGHT - 150)
                player.vel_y = 0
                player.on_ground = False

        # Reset if player falls off screen
        if player.rect.top > SCREEN_HEIGHT:
            # Reset level and player
            load_level(level_index, levels, platform_img, coin_img, all_sprites, platforms, coins)
            player.rect.topleft = (50, SCREEN_HEIGHT - 150)
            player.vel_y = 0
            player.on_ground = False
            score = 0

        # Draw everything
        screen.blit(background_img, (0, 0))
        platforms.draw(screen)
        coins.draw(screen)
        screen.blit(player.image, player.rect)

        # Draw score and level text
        score_text = font.render(f"Level {level_index + 1}    Score: {score}", True, (0, 0, 0))
        screen.blit(score_text, (10, 10))

        pygame.display.flip()

    # Display completion message
    screen.fill((0, 0, 0))
    msg = font.render("Congratulations! You've completed all levels.", True, (255, 255, 255))
    msg_rect = msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(msg, msg_rect)
    pygame.display.flip()
    pygame.time.delay(3000)
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()