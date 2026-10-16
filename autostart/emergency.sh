#!/bin/sh
# Boot hook consumed by /etc/upstart/kmc.conf (SpiderCat, framework_ready),
# and registered in appreg.db as org.kindlemodding.emergency_launcher.
# Upstream: KindleModding/jb.sh src/kmc/system_patches/kmc.conf
#           KindleModding/jb.sh src/kmc/sql/appreg_register_emergency.sql
#
# Keep this tiny and non-blocking: pre-start blocks the upstart job until we
# exit. All logic lives in /mnt/us/qoder/autostart/autostart.sh.
sh /mnt/us/qoder/autostart/autostart.sh
