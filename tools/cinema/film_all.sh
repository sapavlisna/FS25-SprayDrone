#!/bin/bash
# Natočí zbývající takes (s01 t1 už je): bash tools/cinema/film_all.sh ; log do tmp/trailer/film_all.log
cd /e/ClaudeProjects/FS25-SprayDrone
run() { echo "=== $1 take $2 $(date +%T)"; python tools/cinema/run_scene.py "$1" --record --take "$2" 2>&1 | grep -v "^20" | grep "camPath\|camFollow\|ERR\|přerušena\|waitDrone"; }
run s01_aerial 2
run s02_road 1
run s02_road 2
run s03_track 1
run s03_track 2
run s04_unfold 1
run s04_unfold 2
run s05_takeoff 1
sleep 40
run s05_takeoff 2
sleep 40
run s06_spray 1
sleep 40
run s06_spray 2
echo "=== hotovo $(date +%T)"
