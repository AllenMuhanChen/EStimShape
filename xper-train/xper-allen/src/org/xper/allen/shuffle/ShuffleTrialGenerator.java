package org.xper.allen.shuffle;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.allen.twodvsthreed.TwoDVsThreeDTrialGenerator;

import javax.sql.DataSource;
import java.util.Arrays;
import java.util.List;

public class ShuffleTrialGenerator extends TwoDVsThreeDTrialGenerator {

    private List<ShuffleType> shuffleTypes = Arrays.asList(
            ShuffleType.PIXEL,
            ShuffleType.PHASE,
            ShuffleType.MAGNITUDE
    );

    @Override
    protected void addTrials() {
        //Read top N 3D stimuli from the ga database
        List<Long> threeDStimIds = fetchTopNStimIds("3D");

        ShuffleStim stim;
        for (Long gaStimId : threeDStimIds) {
            for (ShuffleType shuffleType : shuffleTypes) {
                stim = new ShuffleStim(this, gaStimId, "SHADE", shuffleType);
                stims.add(stim);

                stim = new ShuffleStim(this, gaStimId, "SPECULAR", shuffleType);
                stims.add(stim);
            }

        }
    }
}