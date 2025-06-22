# Interactive Learning Device using Raspberry Pi 5

## Getting started:

- [Introduction](#introduction)
- [Setup & Installation](#setup--installation)
- [User Guide](#user-guide)
## Introduction

## Setup & Installation:
### 1. Preparing the hardware:
- **Hardware requirements**
  
  Before using the provided software in this repository, you should own the following:

  - a __Raspberry Pi 5 8GB RAM__ or greater model
  - the official __Raspberry Pi AI HAT__ (provided in the __Raspberry Pi AI Kit__)
  - one of the official __Raspberry Pi Cameras__ (this product was built using the __Raspberry Pi Camera 3__)
  - a __microSD card__ (64GB or greater)
  - a __power supply option__ for the Raspberry Pi
  - the official __Raspberry Pi Active Cooler__ (or any other active cooler designed for HAT support)
  - any Linux-supported __USB Speaker__
  - _(optional, but recommended)_ a __camera support__ for the Pi Camera
  - _(optional, but recommended)_ a ___HAT-compatible_ Raspberry Pi 5 case__
    
- **Installing components:**
  
  This section is dedicated to explaining and offering guides to installing every hardware component on the Raspberry Pi 5 needed in order to ensure proper support for running the software presented in this repository.
> [!NOTE]
> This guide does **not** include instructions for installing any case or camera stand/support for the Raspberry Pi.\

> [!IMPORTANT]
> Please ensure that your Raspberry Pi 5 is turned off and disconnected from any power source.\
> Be mindful of static electricity and/or dust in your environment.

  - Step 1: _Install the Active Cooler._
    
    If you own the official Raspberry Pi Active Cooler, you can follow [the official guide](https://datasheets.raspberrypi.com/cooling/raspberry-pi-active-cooler-product-brief.pdf)(see page 4), or [this YouTube video](https://youtu.be/uRvfN6HL6Tw?si=RQmCNywDAsRoRi4T&t=108).\
    For other active coolers supported by the Raspberry Pi 5, check with the manufacturer of your product for an installation guide.
  
  - Step 2: _Install the PiCamera and the GPIO header extension provided in the AI Kit._
    
    __For the camera:__ Unlatch the tab of one of the CAMERA connctors of your board (next to the Ethernet and USB Hub) and gently insert one end of the ribbon cable. Push the tab back into place and ensure the ribbon cable is connected securely. Repeat the process with the other end of the ribbon cable and the PiCamera module. Alternatively, follow [the official guide](https://www.raspberrypi.com/documentation/accessories/camera.html#install-a-raspberry-pi-camera).
    
    __For the GPIO header extension:__ Slot the GPIO header extension on top of the GPIO header and gently push it down until seated properly.\
> [!NOTE]
> The GPIO header extension is not long enough to expose the pins after the AI HAT is installed. If you need access to the GPIO pins, a longer GPIO header extension can be purchased and installed.
    
  - Step 3: _Install the AI HAT:_

    For this installation, it is recommended to follow [the official guide](https://www.raspberrypi.com/documentation/accessories/ai-kit.html#ai-kit-installation) provided by Raspberry Pi.

  - Step 4: _Connecting the speaker:_

    Most USB speakers are plug-and-play, which means connecting them to one of the USB ports on your Raspberry Pi will be enough.
    
### 2. Installing operating system:
TO BE DONE.
### 3. Cloning the repository:
TO BE DONE
### 4. Installing software:
- **Install Hailo SDK:**
  
  Install the required SDK in order to ensure the functionality of the AI HAT:
  ```
  sudo apt install hailo-all
  ```
  A reboot of the Pi is neccessary after this step. Reboot by running the following command in a terminal:
  ```
  reboot
  ```

- **Install project dependencies:**
  
  Open a terminal and run the _install.sh_ shell script by doing the following:
  ```
  ./install.sh
  ```
> [!IMPORTANT]
> Provided script will install Ollama along with other Python packages required for this project. Check _"requirements.txt"_ for a list of packages that are about to be installed.\
> A network connection is required for the initial setup of the device. Please ensure you're providing an Internet connection either by using an Ethernet cable or by Wi-Fi (see [Installing operating system](#2-installing-operating-system) for setting up Wi-FI on your Raspberry Pi 5)
## User Guide:
TO BE DONE
## 
