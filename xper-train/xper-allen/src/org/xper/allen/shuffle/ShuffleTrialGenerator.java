package org.xper.allen.shuffle;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.app.twodvsthreed.TwoDVsThreeDConfig;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.allen.twodvsthreed.TwoDVsThreeDTrialGenerator;
import org.xper.util.FileUtil;

import javax.sql.DataSource;
import java.util.Arrays;
import java.util.List;

public class ShuffleTrialGenerator extends TwoDVsThreeDTrialGenerator {

    private List<ShuffleType> shuffleTypes = Arrays.asList(
            ShuffleType.PIXEL,
            ShuffleType.PHASE,
            ShuffleType.MAGNITUDE
    );

    public static void main(String[] args) {
        // Set default values
        int startRank = 1;
        int endRank = 10;

        // Parse command line arguments if provided
        if (args.length >= 1) {
            try {
                startRank = Integer.parseInt(args[0]);
            } catch (NumberFormatException e) {
                System.err.println("Error parsing startRank argument. Using default value: " + startRank);
            }
        }

        if (args.length >= 2) {
            try {
                endRank = Integer.parseInt(args[1]);
            } catch (NumberFormatException e) {
                System.err.println("Error parsing endRank argument. Using default value: " + endRank);
            }
        }

        // Validate the input
        if (startRank < 1) {
            System.err.println("startRank must be at least 1. Using default value: 1");
            startRank = 1;
        }

        if (endRank < startRank) {
            System.err.println("endRank must be greater than or equal to startRank. Using value: " + startRank);
            endRank = startRank;
        }

        System.out.println("Using rank range: " + startRank + " to " + endRank);

        // Create and configure the generator
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"),
                TwoDVsThreeDConfig.class
        );

        ShuffleTrialGenerator gen = context.getBean(ShuffleTrialGenerator.class, "generator");

        // Set the rank range
        gen.startRank = startRank;
        gen.endRank = endRank;

        // Generate trials
        gen.generate();
    }

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