#!/bin/bash
source /opt/ros/jazzy/setup.bash
source /home/oguz/multi_ahe/install/setup.bash
env -u GTK_PATH -u GTK_EXE_PREFIX -u GTK_MODULES -u GTK_IM_MODULE_FILE \
    DISPLAY=:1 \
    rviz2 -d /home/oguz/multi_ahe/src/m_ahe_mrta_bringup/config/phase9_demo.rviz "$@"
