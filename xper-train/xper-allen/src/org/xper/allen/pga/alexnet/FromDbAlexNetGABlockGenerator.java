package org.xper.allen.pga.alexnet;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.pga.alexnet.SeedingStim;
import org.xper.allen.pga.StimGaInfoEntry;

import org.xper.allen.util.MultiGaDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

import java.util.List;

public class FromDbAlexNetGABlockGenerator extends AbstractMStickPngTrialGenerator<Stim> {

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    String gaName;


    @Override
    protected void addTrials() {
        Long experimentId = dbUtil.readCurrentExperimentId(gaName);
        List<Long> lineageIdsInThisExperiment = dbUtil.readLineageIdsForExperiment(experimentId);
        List<Long> stimIdsToGenerate = dbUtil.findStimIdsWithoutStimSpec(lineageIdsInThisExperiment);

        for (Long stimId : stimIdsToGenerate) {
            StimGaInfoEntry stimInfo = dbUtil.readStimGaInfoEntry(stimId);
            double magnitude = stimInfo.getMutationMagnitude();
            Long parentId = stimInfo.getParentId();

            try{
                StimType stimType;
                stimType = StimType.valueOf(stimInfo.getStimType());

                String textureType = "SHADE";
                RGBColor color = new RGBColor(0, 0, 0);
                Coordinates2D location = new Coordinates2D(0, 0);
                float[] lightingDirection = {0, 0, 0};
                double sizeDiameter = 0.0;

                Stim stim;
                switch (stimType) {
                    case SEEDING:
                        stim = new SeedingStim(this, parentId, stimId, textureType, color, location, lightingDirection, sizeDiameter);
                        break;
//                    case RF_LOCATE:
//                        stim = new RFStim(stimId, this, new Coordinates2D(0, 0), "SHADE", new RGBColor(0, 0, 0), RFStrategy.PARTIALLY_INSIDE);
//                        break;
//                    case GROWING:
//                        stim = new GrowingStim(stimId, this, new Coordinates2D(0, 0), "SHADE", new RGBColor(0, 0, 0), RFStrategy.PARTIALLY_INSIDE);
//                        break;
                    default:
                        throw new IllegalArgumentException("No enum constant found for value: " + stimInfo.getStimType());
                }

                stims.add(stim);

            } catch (Exception e) {
                e.printStackTrace();
            }
        }

    }


}