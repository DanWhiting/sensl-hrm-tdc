# sensl-hrm-tdc
Python wrapper and correlation tools for Sensl HRM-TDC modules.

## sensl.py
A wrapper for the C drivers of HRM-TDC modules.
### Installation
Requires standard python 32 bit installation in additon to numpy and 
ctypes packages.
Update SENSL variable to location of user's HRM_TDC drivers.

## correlator.py
A wx GUI for performaing correlation measurements on multi-channel data from HRM-TDC modules.
### Installation
In addition to the requirements for sensl.py, this module requires wx and matplotlib packages.