#!/bin/bash

git pull
git submodule update  --init --recursive

pip3 install --user numpy pyopengl .

cd ext/glumpy
pip3 install --user .

cd ../pyimgui
pip3 install --user .

cd ../../

# TODO build itself eventually
