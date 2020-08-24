#!/bin/bash
cp /Users/allenchen/Documents/GitHub/V1Microstim/shellScripts/xper.properties.allen.properties /Users/allenchen/Documents/GitHub/V1Microstim/xper-train/dist/xper.properties
#cp xper.properties.allen /Users/allenchen/Documents/GitHub/V1Microstim/xper-train/dist/allen/xper.properties
cd /Users/allenchen/Documents/GitHub/V1Microstim/xper-train/dist
java -jar time_server.jar
