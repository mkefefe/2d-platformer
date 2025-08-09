import pygame
import os
import sys

# Initialize Pygame
pygame.init()

# Screen settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Directories for assets
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = BASE_DIR  # assets are stored in the repository root

# Load images
player_idle = pygame.image.load(os.path.join(ASSET_DIR, 'player_idle.png')).convert_alpha()
player_run1 = pygame.image.load(os.path.join(ASSET_DIR, 'player_run1.png')).convert_alpha()
player_run2 = pygame.image.load(os.path.join(ASSET_DIR, 'player_run2.png')).convert_alpha()
platform_img = pygame.image.load(os.path.join(ASSET_DIR, 'platform.png')).convert_alpha()
coin_img = pygame.image.load(os.path.join(ASSET_DIR, 'coin.png')).convert_alpha()

class Player(pygame.sprite.Sprite):
    """Player sprite with simple animation and physics."""
    def __init__(self):
        super().__init__()
        self.images = [player_idle, player_run1, player_run2]
        self.index = 0
        self.image = self.images[self.index]
        self.rect = self.image.get_rect()
        self.rect.topleft = (100, SCREEN_HEIGHT - 150)
        self.vel_y = 0
        self.speed = 5
        self.on_ground = False
        self.frame_timer = 0

    def update(self, platforms):
        """Update player position and animation."""
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

        # Gravity
        self.vel_y += 0.5
        dy += self.vel_y

        # Animation frames: run frames when moving; idle when stationary
        if dx != 0:
            self.frame_timer += 1
            if self.frame_timer >= 10:
                self.frame_timer = 0
                # Cycle through run frames (indices 1 and 2)
                if self.index < 1 or self.index > 2:
                    self.index = 1
                else:
                    self.index = 1 + (self.index - 1 + 1) % 2
        else:
            self.index = 0
            self.frame_timer = 0

        self.image = self.images[self.index]

        # Horizontal collision
        self.rect.x += dx
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if dx > 0:
                    self.rect.right = platform.rect.left
                elif dx < 0:
                    self.rect.left = platform.rect.right

        # Vertical movement and collision
        self.rect.y += dy
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vel_y > 0:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = platform.rect.bottom
                    self.vel_y = 0

        # Reset if player falls below screen
        if self.rect.top > SCREEN_HEIGHT:
            # Reset position and state
            self.rect.topleft = (100, SCREEN_HEIGHT - 150)
            self.vel_y = 0
            self.on_ground = False
            return False
        return True

class Platform(pygame.sprite.Sprite):
    """Static platform using the platform image."""
    def __init__(self, x, y):
        super().__init__()
        self.image = platform_img
        self.rect = self.image.get_rect(topleft=(x, y))

class Coin(pygame.sprite.Sprite):
    """Collectible coin sprite."""
    def __init__(self, x, y):
        super().__init__()
        self.image = coin_img
        self.rect = self.image.get_rect(center=(x, y))


def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("2D Platformer Game")
    clock = pygame.time.Clock()

    # Groups and sprites
    player = Player()
    platforms = pygame.sprite.Group()
    coins = pygame.sprite.Group()

    # Ground platform (full width)
    platforms.add(Platform(0, SCREEN_HEIGHT - platform_img.get_height()))

    # Additional platforms for jumping
    platforms.add(Platform(200, 450))
    platforms.add(Platform(400, 350))
    platforms.add(Platform(600, 250))

    # Add some coins on platforms
    coins.add(Coin(220, 420))
    coins.add(Coin(420, 320))
    coins.add(Coin(620, 220))

    font = pygame.font.SysFont(None, 36)
    score = 0

    running = True
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Update player and check if they fall off screen
        alive = player.update(platforms)

        # Check for coin collisions and update score
        collected = pygame.sprite.spritecollide(player, coins, True)
        score += len(collected)

        # Draw background (light sky blue)
        screen.fill((135, 206, 235))

        # Draw platforms
        for platform in platforms:
            screen.blit(platform.image, platform.rect)

        # Draw coins
        for coin in coins:
            screen.blit(coin.image, coin.rect)

        # Draw player
        screen.blit(player.image, player.rect)

        # Draw score text
        score_text = font.render(f"Score: {score}", True, (0, 0, 0))
        screen.blit(score_text, (10, 10))

        pygame.display.flip()

        # If player fell, reset coins and score
        if not alive:
            # Reset coins
            coins.empty()
            coins.add(Coin(220, 420), Coin(420, 320), Coin(620, 220))
            score = 0

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
