# I love lamp.
This is for a personal project in which I did a retrofit on a vintage 1975 Panasonic CCTV WV-341P video camera. The camera was hollowed out and turned into a floor lamp, but it's also still functional as a camera with additional live video feeds streaming from the internet. More info on the project can be found at [this link](https://www.reddit.com/r/RASPBERRY_PI_PROJECTS/comments/v5jah2/converting_a_1975_cctv_panasonic_camera_to/).

Here are the materials used:
* Raspberry Pi Model A+
* Arducam 5MP Camera
* HiLetgo AC-DC 220V to 5V switching power supply for the Pi
* ELECROW 5 Inch Raspberry Pi Screen Touchscreen 800x480 TFT LCD with HDMI
* Photo transistor light sensor from Adafruit (for the Pi to know if the blub is on or off
* Songhe DC relay to control the LCD screen backlight. (I didn't have any transistors at the time)
* ADS1115 analog to digital converter to read the potentiometer values from the back of the camera and the light sensor.

# Setup

NOTE: I used the Debian Buster version of the Raspberry PI minimal OS here, because I was having issues getting the camera working with Bullseye.

First, add the proper LCD settings to the config.txt file:

Add to end of the config.txt file:

```
# --- added by elecrow-pitft-setup  ---
hdmi_force_hotplug=1
max_usb_current=1
hdmi_drive=1
hdmi_group=2
hdmi_mode=1
hdmi_mode=87
hdmi_cvt 800 480 60 6 0 0 0
dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,keep_vref_on=0,swapxy=0,pmax=255,xohms=150,xmin=200,xmax=3900,ymin=200,ymax=3900
display_rotate=0
# --- end elecrow-pitft-setup  ---
```

Install the required software:

```
sudo apt-get install python3-pip git fbi
sudo pip3 install --upgrade setuptools
```

Install CircuitPython:

```
sudo pip3 install --upgrade adafruit-python-shell
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
sudo python3 raspi-blinka.py
sudo pip3 install adafruit-circuitpython-ads1x15
```

Install the ADS libraries from Git:

```
git clone https://github.com/adafruit/Adafruit_Python_ADS1x15
cd Adafruit_Python_ADS1x15
sudo pip3 install --upgrade setuptools
```

Install Livestreamer:

`sudo pip install livestreamer'


