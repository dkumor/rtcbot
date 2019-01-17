import pygame

pygame.joystick.init()

js = pygame.joystick.Joystick(0)

js.init()
print(js.get_name())
