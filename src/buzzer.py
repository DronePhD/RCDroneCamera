from time import sleep

from gpiozero import Buzzer


BUZZER_PIN = 4

def camera_buzz() -> None:
    """
    Start the buzzer when the camera.service starts
    """
    buzzer = Buzzer(BUZZER_PIN, active_high=False)
    for _ in range(3):
        buzzer.on()
        sleep(.2)
        buzzer.off()
        sleep(.2)

def rc_buzz() -> None:
    """
    Start the buzzer when the rc.service starts
    """
    buzzer = Buzzer(BUZZER_PIN, active_high=False)
    for _ in range(5):
        buzzer.on()
        sleep(.05)
        buzzer.off()
        sleep(.05)

    for _ in range(3):
        buzzer.on()
        sleep(.3)
        buzzer.off()
        sleep(.3)