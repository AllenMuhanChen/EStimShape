package org.xper.allen.fixation.blockgen;

import org.xper.allen.nafc.blockgen.Trial;
import org.xper.drawing.Coordinates2D;

public class NoisyPngFixationTrial implements Trial {

    Coordinates2D coords;
    String pngPath;
    String noiseMapPath;

    @Override
    public void preWrite() {

    }

    @Override
    public void write() {
        //generate rand png
        //generate noise map
        //write stimObjId
        //write stimSpec
    }

    private void generateStim(){

    }

    @Override
    public Long getTaskId() {
        return null;
    }
}
