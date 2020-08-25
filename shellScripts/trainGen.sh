#!/bin/bash
cp /Users/allenchen/Documents/GitHub/V1Microstim/shellScripts/xper.properties.allen.properties /Users/allenchen/Documents/GitHub/V1Microstim/xper-train/dist/allen/xper.properties
cd /Users/allenchen/Documents/GitHub/V1Microstim/xper-train/dist/allen
java -jar trainingGeneration.jar '/Users/allenchen/Documents/GitHub/V1Microstim/xper-train/xper-allen/doc/Test.xml'