import pygame
import sys

# Initialize Pygame
pygame.init()

# Screen settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)

# Colors
WHITE = (255, 255, 255)
BLUE = (50, 150, 255)
GREEN = (50, 255, 100)

# Set up the display
screen = pygame.display.set_mode(SCREEN_SIZE)
pygame.display.set_caption("2D Platformer Game")
clock = pygame.time.Clock()

# Player class
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # Create simple frames for animation (red and green rectangles)
        self.frames = [self.create_frame(BLUE), self.create_frame(GREEN)]
        self.image = self.frames[0]
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (100, 500)
        self.vx = 0
        self.vy = 0
        self.frame_index = 0
        self.on_ground = False

    def create_frame(self, color):
        surface = pygame.Surface((40, 60))
        surface.fill(color)
        return surface

    def update(self, keys, platforms):
        # Movement input
        self.vx = 0
        if keys[pygame.K_LEFT]:
            self.vx = -5
        if keys[pygame.K_RIGHT]:
            self.vx = 5
        # Jumping
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vy = -12

        # Apply gravity
        self.vy += 0.5
        if self.vy > 10:
            self.vy = 10

        # Horizontal movement and collision
        self.rect.x += self.vx
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vx > 0:
                    self.rect.right = platform.rect.left
                elif self.vx < 0:
                    self.rect.left = platform.rect.right

        # Vertical movement and collision
        self.rect.y += self.vy
        self.on_ground = False
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                if self.vy > 0:
                    self.rect.bottom = platform.rect.top
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = platform.rect.bottom
                    self.vy = 0

        # Animation: switch frames when moving
        if self.vx != 0:
            self.frame_index += 0.1
            if self.frame_index >= len(self.frames):
                self.frame_index = 0
            self.image = self.frames[int(self.frame_index)]
        else:
            # Idle frame
            self.image = self.frames[0]

# Platform class
class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill((139, 69, 19))  # Brown color for platforms
        self.rect = self.image.get_rect(topleft=(x, y))

# Create player and platforms
player = Player()
platforms = pygame.sprite.Group()

# Ground platform
ground = Platform(0, SCREEN_HEIGHT - 40, SCREEN_WIDTH, 40)
platforms.add(ground)

# Additional platforms
platforms.add(Platform(200, 450, 120, 20))
platforms.add(Platform(400, 350, 150, 20))
platforms.add(Platform(650, 250, 100, 20))

all_sprites = pygame.sprite.Group()
all_sprites.add(player)
all_sprites.add(platforms)

# Main game loop
def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()

        # Update player
        player.update(keys, platforms)

        # Draw everything
        screen.fill(WHITE)
        for entity in all_sprites:
            screen.blit(entity.image, entity.rect)

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
