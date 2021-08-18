# AESify
Encrypt and protect PDF files - A GUI for pikepdf -> qpdf

## Features
* Encrypt PDF files with Advanced Encryption Standard (AES) encyption 
  * AES-128 bits
  * AES-256 bits
* Support to set "Document open" and "Permissions" (Owner) passwords  
* Set document restrictions 
    * Print resolution
    * Document assembly
    * Content copying
    * Commenting
    * Filling in form fields
* Define a page range if you just want to export a part of your PDF
* Create strong passwords
* Ready for localization (EN, DE and RU already included)
* Supported OS: Windows 10 and Linux (e.g. Ubuntu 20.04) 

## Installation
In order to use the copy/paste features on linux computers you need to install 'xclip', 'xsel' or 'wl-clipboard' with apt.

If your **Linux** Distro comes with <code>snap</code> (e. g. Ubuntu) you can:

[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/aesify)

or you can type

<code>sudo snap install aesify</code> 

in your terminal.

If your Linux Distro does not have <code>snap</code> pre-installed you can find instructions for installing <code>snap</code> [here.](https://snapcraft.io/docs/installing-snapd)

The easiest way to "install" AESify on **Windows** is to download the [release package](https://github.com/digidigital/AESify/releases/tag/v1.5.1), unzip and simply run the binary.

Alternatively you can download the code folder and run the AESify.py script. In this case you have to install the packages PySimpleGUI, pyperclip and pikepdf using pip3.     

