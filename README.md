# Interactive Learning Device using Raspberry Pi 5

## Getting started:

- [Introduction](#introduction)
- [Setup & Installation](#setup--installation)
- [User Guide](#user-guide)
## Introduction

## Setup & Installation:
### 1. Preparing the hardware:
- **Hardware requirements**\
Before using the provided software in this repository, one should own the following:
  - a Raspberry Pi 5 8GB RAM or greater model
  - the official Raspberry Pi AI HAT (provided in the Raspberry Pi AI Kit)
  - one of the official Raspberry Pi Cameras (this product was built using the Raspberry Pi Camera 3)
  - a microSD card (64GB or greater)
  - a power supply option for the Raspberry Pi
  - the official Raspberry Pi Active Cooler (or any other active cooler designed for HAT support)
  - any Linux-supported USB Speaker
  - _(optional, but recommended)_ a camera support for the Pi Camera
  - _(optional, but recommended)_ a HAT-compatible Raspberry Pi 5 case
### 2. Installing operating system:
blablabla
### 3. Cloning the repository:
### 4. Installing software:
- **Install Hailo SDK:**\
  Install the required SDK in order to ensure the functionality of the AI HAT:
  ```
  sudo apt install hailo-all
  ```
  A reboot of the Pi is neccessary after this step. Reboot by running the following command in a terminal:
  ```
  reboot
  ```

- **Install project dependencies:**\
  Open a terminal and run the _install.sh_ bash script by doing the following:
  ```
  ./install.sh
  ```
> [!IMPORTANT]
> Provided script will install Ollama along with other Python packages required for this project. Check _"requirements.txt"_ for a list of packages that are about to be installed.\
> A network connection is required for the initial setup of the device. Please ensure you're providing an Internet connection either by using an Ethernet cable or by Wi-Fi (see [Installing operating system](#2-installing-operating-system) for setting up Wi-FI)
## User Guide:

## 
