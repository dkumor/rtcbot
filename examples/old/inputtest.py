from inputs import devices

print(devices.gamepads)
gp = devices.gamepads[0]

while True:
    evt = gp.read()
    for event in evt:
        print(event.ev_type, event.code, event.state)
