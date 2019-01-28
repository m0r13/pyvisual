#!/bin/bash

# packages: python3.7 python3.7-dev g++ libglfw3 libasound2-dev
# TODO pip
# --> check if there is pip3.7
# if not: try python3.7 -m pip

git submodule update  --init --recursive

pip3 install --user -r requirements.txt

#pip3 install --user numpy scipy pyopengl .

#cd ext/glumpy
#pip3 install --user .

#cd ../pyimgui
#pip3 install --user .

#cd ../../
