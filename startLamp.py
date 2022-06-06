import os
import time
import board
import busio
import digitalio
import pwmio
import subprocess
import random
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

SHORT_TRANSITION_IMAGES = ["images/testPattern1.gif","images/testPattern2.gif","images/testPattern3.gif","images/testPattern4.gif"]
VIDEO_STANDBY_IMAGE = "images/testPattern1.gif"

# The list of videos to display when the lamp's input source is not set to "camera" via a physical switch.
# Which video file or internet webcam stream to play is controlled by the lamp's contrast knob.
videoStreamChannels = []
videoStreamChannels.append("livestreamer http://ustream.tv/channel/live-iss-stream mobile_480p --yes-run-as-root --player omxplayer --fifo")
videoStreamChannels.append("livestreamer http://ustream.tv/channel/iss-hdev-payload mobile_360p --yes-run-as-root --player omxplayer --fifo")

# The list of properties/effects to use for the lamp's camera when it is active via the physical switch.
# Which effect to use it controlled by the lamp's contrast knob.
cameraEffects = []
cameraEffects.append("-cfx 128:128") # Normal black & white
cameraEffects.append("-cfx 128:128 -ifx solarise") # Black and white with white blown out
cameraEffects.append("-cfx 128:128 -ifx sketch") # Black and white with sketch effect
cameraEffects.append("-cfx 128:128 -ifx hatch") # Black and white with hatch effect

# Declare GPIO bins and ADC channels to use.
LIGHT_SENSOR_CHANNEL = ADS.P0;
SOURCE_SWITCH_CHANNEL = ADS.P1;
BRIGHTNESS_POT_CHANNEL = ADS.P2;
CONTRAST_POT_CHANNEL = ADS.P3;
LED_PIN = board.D18;
SCREEN_ENABLE_PIN_OUTPUT = board.D4;
SCREEN_ENABLE_PIN_INPUT = board.D17;

# Other constants.
MAX_POTENTIOMETER_VOLTAGE = 3.286
LIGHT_SENSOR_THRESHOLD = 10000 # If the light photo sensor falls below this amount, it indicates the AC lightbulb is off.
MAX_PWM_VALUE = 65535

class Lamp():

    def __init__(self):

        self.bLampIsOn = False;
        self.bCameraActive = False;
        self.bVideoFeedActive = False;
        self.bScreenIsOn = False;
        self.videoStream = None
        self.cameraProcess = None
        self.contrastValue = 0;
        self.brightnessValue = 0;

        # Kill any previous processes that may have still been running to clear the screen.
        self.showImage(None);
        self.killCamera();
        self.killVideoStream();

        # Create the I2C bus
        i2c = busio.I2C(board.SCL, board.SDA)

        # Setup ADC sensors
        ads = ADS.ADS1015(i2c)
        self.lightSensor = AnalogIn(ads, LIGHT_SENSOR_CHANNEL)
        self.sourceSwitch = AnalogIn(ads, SOURCE_SWITCH_CHANNEL)
        self.brightnessKnob = AnalogIn(ads, BRIGHTNESS_POT_CHANNEL)
        self.contrastKnob = AnalogIn(ads, CONTRAST_POT_CHANNEL)

        # Setup Pi's GPIO
        self.redLED = pwmio.PWMOut(LED_PIN)
        self.screenEnableOutput = digitalio.DigitalInOut(SCREEN_ENABLE_PIN_OUTPUT)
        self.screenEnableOutput.direction = digitalio.Direction.OUTPUT
        self.screenEnableInput = digitalio.DigitalInOut(SCREEN_ENABLE_PIN_INPUT)
        self.screenEnableInput.direction = digitalio.Direction.INPUT
        self.screenEnableInput.pull = digitalio.Pull.DOWN


        while True:
            time.sleep(0.05)
            
            self.evalLampState();
            self.evalBrightnessControl();
            self.evalContrastControl(False);
            self.evalScreenControl();
            self.evalCamera();
            self.evalVideoFeed();

    def clamp(self, num, min_value, max_value):
        return max(min(num, max_value), min_value)

    def showImage(self, filename):
        if( filename == None):
            subprocess.Popen('sudo pkill -9 fbi', shell=True)
        else:
            filename = os.path.dirname(os.path.realpath(__file__)) + "/" + filename
            print(filename)
            subprocess.Popen('sudo pkill -9 fbi ; fbi --noverbose -T 2 ' + filename, shell=True)

    def evalScreenControl(self):
        if( self.bLampIsOn and self.screenEnableInput.value ):
            self.bScreenIsOn = True
        else:
            self.bScreenIsOn = False

        self.screenEnableOutput.value = self.bLampIsOn # Set GPIO value to turn on or off the screen backlight.

    # Evaluate if the lamp bulp with the AC power source is on or off using a photo transistor.
    def evalLampState(self):
        if( self.lightSensor.value < LIGHT_SENSOR_THRESHOLD ):
            self.bLampIsOn = False;
        else:
            self.bLampIsOn = True;

    def killCamera(self):
        self.cameraProcess = None
        killProcess = subprocess.Popen('sudo pkill -9 raspivid', shell=True)
        killProcess.wait()
        self.bCameraActive = False

    # Determine if we should be using the camera to display instead of a video file. And if so, start it if needed.
    def evalCamera(self):
        if( self.bCameraActive and (self.sourceSwitch.voltage < 3 or not self.bScreenIsOn) ):
            self.killCamera()

        elif( not self.bCameraActive and self.sourceSwitch.voltage >= 3 and self.bScreenIsOn):
            self.showImage(random.choice(SHORT_TRANSITION_IMAGES))
            self.bCameraActive = True;
            self.evalContrastControl(True);
            self.cameraProcess = subprocess.Popen('raspivid ' + cameraEffects[self.contrastValue] + ' -awb auto -t 0 -vf -hf -w 800 -h 480 -fps 30', shell=True,stdin=subprocess.PIPE)
           
    # Kill any video file or live webcam stream from the internet.
    def killVideoStream(self):
        if( self.videoStream):
            self.videoStream.kill();

            subprocess.Popen('sudo pkill -9 livestreamer', shell=True)
            subprocess.Popen('sudo pkill -9 omxplayer', shell=True)
            self.bVideoFeedActive = False;

    # Start playing a video instead of using the camera. Video source may be a live internet webcam or a local file.
    def startVideoStream(self, channel):
        self.showImage(VIDEO_STANDBY_IMAGE)
        self.videoStream = subprocess.Popen(videoStreamChannels[channel], shell=True,stdin=subprocess.PIPE)

    # Determine if we should be playing a video feed (instead of using the camera) and manage the stream.
    def evalVideoFeed(self):
        if( self.bVideoFeedActive and (self.sourceSwitch.voltage >= 3 or not self.bScreenIsOn) ):
            self.killVideoStream();
        elif( not self.bVideoFeedActive and self.sourceSwitch.voltage < 3 and self.bScreenIsOn ):
            self.bVideoFeedActive = True;
            self.evalContrastControl(True);
            self.startVideoStream(self.contrastValue)

        # Check if video stream process should be running but isn't anymore.
        if( self.bVideoFeedActive and self.videoStream):
            poll = self.videoStream.poll()
            if poll is not None:
                print("Video process isn't running! Restart!")
                # Flag system that video process needs to be restarted.
                self.bVideoFeedActive = False;

    def evalBrightnessControl(self):
        if( self.bScreenIsOn ):
            try:
                self.brightnessValue = self.clamp(MAX_PWM_VALUE - int((self.brightnessKnob.voltage*MAX_PWM_VALUE)/MAX_POTENTIOMETER_VOLTAGE), 0, MAX_PWM_VALUE);
            except:
                self.brightnessValue = 0
        else:
            self.brightnessValue = 0

        self.redLED.duty_cycle = self.brightnessValue

    # The contrast knob on the camera switches between different video streams or different camera effects.
    def evalContrastControl(self, bDisableRestart):
        if( not self.bVideoFeedActive and not self.bCameraActive ):
            return

        if( self.bVideoFeedActive ):
            maxRange = len(videoStreamChannels)-1
        else:
            maxRange = len(cameraEffects)-1

        if( self.bLampIsOn ):
            newContrastValue = self.clamp(maxRange - int((self.contrastKnob.voltage*maxRange)/MAX_POTENTIOMETER_VOLTAGE), 0, maxRange);
        else:
            newContrastValue = 0;

        if( newContrastValue != self.contrastValue):
            if( self.bVideoFeedActive and not bDisableRestart ):
                # Flag video stream to die so it can restart the stream with the new feed.
                # New feed is determined by the contrast value.
                self.killVideoStream()
            elif( self.bCameraActive and not bDisableRestart ):
                # Flag camera stream to die so it can restart with the new effect.
                # New effect is determined by contrast value.
                self.killCamera()

            self.contrastValue = newContrastValue

# I love lamp.
lamp = Lamp()
quit()

