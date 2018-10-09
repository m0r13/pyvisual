#!/bin/bash

git pull
git submodule init
git submodule update

cd ext/vispy
pip3 install --user .

cd ../pyimgui
pip3 install --user .

cd ../../

# TODO build itself eventually
