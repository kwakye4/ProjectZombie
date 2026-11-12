import pygame
import sys
import asyncio
import os
import random
import math

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors (RGB)
BG_COLOR = (20, 24, 33)
PLAYER_COLOR = (50, 205, 50)
ZOMBIE_COLOR = (220, 20, 60)
ZOMBIE_ALERT_COLOR = (255, 140, 0)
BULLET_COLOR = (255, 255, 0)
TEXT_COLOR = (240, 240, 240)
GRID_COLOR = (30, 35, 48)

# Game Configuration Constants
MAX_SPEED = 4.0
ACCEL = 0.5
DRAG = 0.88
BULLET_SPEED = 10.0
ZOMBIE_SPEED = 2.0
DETECTION_RANGE = 250.0
FOV_THRESHOLD = 0.3  # Cosine threshold for field of view (~72 degrees)

def load_sprite(filename, size):
    """Loads an image sprite safely. Returns None if file doesn't exist."""
    if os.path.exists(filename):
        try:
            img = pygame.image.load(filename).convert_alpha()
            return pygame.transform.scale(img, (size * 2, size * 2))
        except pygame.error:
            return None
    return None

class Player:
    def __init__(self, x, y):
        self.position = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.acceleration = pygame.Vector2(0, 0)
        self.angle = 0.0
        self.radius = 18
        self.health = 100
        self.score = 0
        
        # Load player sprite (Look for 'player.png' in your folder)
        self.sprite = load_sprite("player.png", self.radius)

    def update(self):
        self.velocity += self.acceleration
        if self.velocity.length() > MAX_SPEED:
            self.velocity.scale_to_length(MAX_SPEED)
        
        self.position += self.velocity
        self.velocity *= DRAG
        self.acceleration = pygame.Vector2(0, 0)

        # Screen boundaries check
        if self.position.x < self.radius:
            self.position.x = self.radius
            self.velocity.x = 0
        elif self.position.x > SCREEN_WIDTH - self.radius:
            self.position.x = SCREEN_WIDTH - self.radius
            self.velocity.x = 0
        if self.position.y < self.radius:
            self.position.y = self.radius
            self.velocity.y = 0
        elif self.position.y > SCREEN_HEIGHT - self.radius:
            self.position.y = SCREEN_HEIGHT - self.radius
            self.velocity.y = 0

        # Rotate toward mouse position
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        to_mouse = mouse_pos - self.position
        if to_mouse.length() > 0:
            self.angle = math.degrees(math.atan2(-to_mouse.y, to_mouse.x))

    def draw(self, surface):
        if self.sprite:
            # Rotate sprite based on player angle (Pygame angles are counter-clockwise)
            rotated_image = pygame.transform.rotate(self.sprite, self.angle)
            rect = rotated_image.get_rect(center=(int(self.position.x), int(self.position.y)))
            surface.blit(rotated_image, rect.topleft)
        else:
            # Fallback shape if no image is uploaded
            pygame.draw.circle(surface, PLAYER_COLOR, (int(self.position.x), int(self.position.y)), self.radius)
            rad = math.radians(self.angle)
            forward = pygame.Vector2(math.cos(rad), -math.sin(rad))
            barrel_end = self.position + forward * 25
            pygame.draw.line(surface, (255, 255, 255), self.position, barrel_end, 4)

class Bullet:
    def __init__(self, x, y, direction):
        self.position = pygame.Vector2(x, y)
        self.velocity = direction * BULLET_SPEED
        self.radius = 5
        self.active = True

    def update(self):
        self.position += self.velocity
        if not (0 <= self.position.x <= SCREEN_WIDTH and 0 <= self.position.y <= SCREEN_HEIGHT):
            self.active = False

    def draw(self, surface):
        pygame.draw.circle(surface, BULLET_COLOR, (int(self.position.x), int(self.position.y)), self.radius)

class Zombie:
    def __init__(self, x, y):
        self.position = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0.0)
        self.angle = random.uniform(0, 360)
        self.radius = 16
        self.state = "WANDER"
        self.wander_timer = 0
        
        # Load zombie sprite (Look for 'zombie.png' in your folder)
        self.sprite = load_sprite("zombie.png", self.radius)

    def update(self, player):
        distance_to_player = self.position.distance_to(player.position)
        to_player = player.position - self.position
        if to_player.length() > 0:
            dir_to_player = to_player.normalize()
        else:
            dir_to_player = pygame.Vector2(0, 0)

        rad = math.radians(self.angle)
        forward = pygame.Vector2(math.cos(rad), -math.sin(rad))
        dot = forward.dot(dir_to_player)

        # AI Decision Logic
        if distance_to_player < DETECTION_RANGE and dot > FOV_THRESHOLD:
            self.state = "CHASE"
        elif distance_to_player < 100:
            self.state = "CHASE"
        elif distance_to_player > DETECTION_RANGE * 1.5:
            self.state = "WANDER"

        if self.state == "CHASE":
            steering = dir_to_player * ZOMBIE_SPEED
            self.velocity = steering
            self.angle = math.degrees(math.atan2(-dir_to_player.y, dir_to_player.x))
        else:
            self.wander_timer -= 1
            if self.wander_timer <= 0:
                self.angle += random.uniform(-45, 45)
                self.wander_timer = random.randint(60, 120)
            
            rad = math.radians(self.angle)
            forward = pygame.Vector2(math.cos(rad), -math.sin(rad))
            self.velocity = forward * (ZOMBIE_SPEED * 0.5)

        self.position += self.velocity
        self.position.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.position.x))
        self.position.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.position.y))

    def draw(self, surface):
        if self.sprite:
            rotated_image = pygame.transform.rotate(self.sprite, self.angle)
            rect = rotated_image.get_rect(center=(int(self.position.x), int(self.position.y)))
            surface.blit(rotated_image, rect.topleft)
        else:
            color = ZOMBIE_ALERT_COLOR if self.state == "CHASE" else ZOMBIE_COLOR
            pygame.draw.circle(surface, color, (int(self.position.x), int(self.position.y)), self.radius)
            rad = math.radians(self.angle)
            forward = pygame.Vector2(math.cos(rad), -math.sin(rad))
            nose = self.position + forward * 16
            pygame.draw.line(surface, (255, 255, 255), self.position, nose, 2)

def draw_grid(surface):
    for x in range(0, SCREEN_WIDTH, 40):
        pygame.draw.line(surface, GRID_COLOR, (x, 0), (x, SCREEN_HEIGHT))
    for y in range(0, SCREEN_HEIGHT, 40):
        pygame.draw.line(surface, GRID_COLOR, (0, y), (SCREEN_WIDTH, y))

async def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Vector Zombie Survival - Unit 2 Project")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)
    title_font = pygame.font.SysFont("Arial", 36, bold=True)

    player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    bullets = []
    zombies = []

    for _ in range(5):
        zx = random.choice([random.randint(50, 200), random.randint(600, 750)])
        zy = random.choice([random.randint(50, 150), random.randint(450, 550)])
        zombies.append(Zombie(zx, zy))

    spawn_timer = 0
    game_state = "START"

    running = True
    while running:
        screen.fill(BG_COLOR)
        draw_grid(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if game_state == "START":
                    if event.key == pygame.K_RETURN:
                        game_state = "PLAYING"
                elif game_state == "GAMEOVER":
                    if event.key == pygame.K_r:
                        player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                        bullets.clear()
                        zombies.clear()
                        for _ in range(5):
                            zombies.append(Zombie(random.randint(100, 700), random.randint(100, 500)))
                        game_state = "PLAYING"
                elif game_state == "PLAYING":
                    if event.key == pygame.K_SPACE:
                        rad = math.radians(player.angle)
                        forward = pygame.Vector2(math.cos(rad), -math.sin(rad))
                        bullet_spawn = player.position + forward * 25
                        bullets.append(Bullet(bullet_spawn.x, bullet_spawn.y, forward))

        if game_state == "START":
            title_surf = title_font.render("ZOMBIE SURVIVAL: VECTOR ARCADE", True, (50, 205, 50))
            screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 120))

            instructions = [
                "Controls: WASD or Arrow Keys to move.",
                "Aim: Mouse cursor.",
                "Shoot: SPACEBAR.",
                "Objective: Survive the horde! Watch out for zombie AI sightlines.",
                "",
                "Press ENTER to Start"
            ]
            for i, text in enumerate(instructions):
                txt_surf = font.render(text, True, TEXT_COLOR)
                screen.blit(txt_surf, (SCREEN_WIDTH // 2 - txt_surf.get_width() // 2, 220 + i * 30))

        elif game_state == "PLAYING":
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                player.acceleration.y -= ACCEL
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                player.acceleration.y += ACCEL
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                player.acceleration.x -= ACCEL
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                player.acceleration.x += ACCEL

            player.update()
            for bullet in bullets:
                bullet.update()
            bullets = [b for b in bullets if b.active]

            spawn_timer += 1
            if spawn_timer > 90 and len(zombies) < 12:
                spawn_timer = 0
                edge = random.choice(["top", "bottom", "left", "right"])
                if edge == "top":
                    zombies.append(Zombie(random.randint(0, SCREEN_WIDTH), -20))
                elif edge == "bottom":
                    zombies.append(Zombie(random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + 20))
                elif edge == "left":
                    zombies.append(Zombie(-20, random.randint(0, SCREEN_HEIGHT)))
                else:
                    zombies.append(Zombie(SCREEN_WIDTH + 20, random.randint(0, SCREEN_HEIGHT)))

            for zombie in zombies:
                zombie.update(player)
                dist_to_player = player.position.distance_to(zombie.position)
                if dist_to_player < player.radius + zombie.radius:
                    player.health -= 1
                    if player.health <= 0:
                        game_state = "GAMEOVER"

            for bullet in bullets[:]:
                for zombie in zombies[:]:
                    if bullet.position.distance_to(zombie.position) < bullet.radius + zombie.radius:
                        if bullet in bullets:
                            bullets.remove(bullet)
                        if zombie in zombies:
                            zombies.remove(zombie)
                            player.score += 100
                        break

            player.draw(screen)
            for bullet in bullets:
                bullet.draw(screen)
            for zombie in zombies:
                zombie.draw(screen)

            score_surf = font.render(f"Score: {player.score}", True, TEXT_COLOR)
            health_surf = font.render(f"Health: {max(0, player.health)}", True, (220, 20, 60) if player.health < 40 else TEXT_COLOR)
            zombies_surf = font.render(f"Zombies: {len(zombies)}", True, TEXT_COLOR)
            
            screen.blit(score_surf, (20, 20))
            screen.blit(health_surf, (20, 50))
            screen.blit(zombies_surf, (20, 80))

        elif game_state == "GAMEOVER":
            go_surf = title_font.render("GAME OVER", True, (220, 20, 60))
            final_score = font.render(f"Final Score: {player.score}", True, TEXT_COLOR)
            restart_surf = font.render("Press 'R' to Restart", True, TEXT_COLOR)

            screen.blit(go_surf, (SCREEN_WIDTH // 2 - go_surf.get_width() // 2, 200))
            screen.blit(final_score, (SCREEN_WIDTH // 2 - final_score.get_width() // 2, 260))
            s reen.blit(restart_surf, (SCREEN_WIDTH // 2 - restart_surf.get_width() // 2, 320))

        pygame.display.flip()
        clock.tick(FPS)
        
        # Yield control back to the async event loop
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    asyncio.run(main())

 

