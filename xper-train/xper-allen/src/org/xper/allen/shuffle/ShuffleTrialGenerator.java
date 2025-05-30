package org.xper.allen.shuffle;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.pga.ReceptiveFieldSource;

import javax.sql.DataSource;

public class ShuffleTrialGenerator extends AbstractMStickPngTrialGenerator<Stim> {

    @Dependency
    DataSource gaDataSource;

    @Dependency
    String gaSpecPath;

    @Dependency
    ReceptiveFieldSource rfSource;

    @Override
    protected void addTrials() {
        //Read top N 3D stimuli from the ga database

        //Make Stims for them (child of TwoDVsThreeDStim)
            // Original
            // Pixel Shuffle
            // Phase Shuffle
            // Magnitude Shuffle


    }
}