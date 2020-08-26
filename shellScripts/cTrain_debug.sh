#!/bin/bash
cp /Users/allenchen/Documents/GitHub/V1Microstim/shellScripts/xper.properties.allen.properties /Users/allenchen/Documents/GitHub/V1Microstim/xper-train/dist/allen/xper.properties
cd /Users/allenchen/Documents/GitHub/V1Microstim/xper-train/dist/allen
java -Xdebug -Xrunjdwp:transport=dt_socket,server=y,suspend=y,address=localhost:5005 -jar console.jar