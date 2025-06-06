package org.xper.allen.twodvsthreed;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.Stim;
import org.xper.allen.app.twodvsthreed.TwoDVsThreeDConfig;
import org.xper.allen.stimproperty.ColorPropertyManager;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.HSVUtils;
import org.xper.util.FileUtil;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class TwoDThreeDLightnessTrialGenerator extends TwoDVsThreeDTrialGenerator {
    public static final List<Double> VALUES_TO_TEST = Arrays.asList(0.1, 0.2, 0.4, 0.6, 0.8, 1.0); //Value in HSV

    public int numTrialsPerStim = 5;
    private ColorPropertyManager colorManager;

    public static void main(String[] args) {
        // Set default values
        int startRank = 1;
        int endRank = 2;

        // Parse command line arguments if providedght
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

        TwoDThreeDLightnessTrialGenerator gen = context.getBean(TwoDThreeDLightnessTrialGenerator.class, "generator2");

        // Set the rank range
        gen.startRank = startRank;
        gen.endRank = endRank;

        // Generate trials
        gen.generate();
    }

    @Override
    protected void addTrials() {
        colorManager = new ColorPropertyManager(new JdbcTemplate(gaDataSource));

        // Use the fetchTopNStimIds method from parent class to get stimuli within the specified rank range
        List<Long> twoDStimIds = fetchTopNStimIds("2D");
        List<Long> threeDStimIds = fetchTopNStimIds("3D");

        // Combine the lists
        List<Long> stimIdsToTest = new ArrayList<>();
        stimIdsToTest.addAll(twoDStimIds);
        stimIdsToTest.addAll(threeDStimIds);

        System.out.println("Using stimuli IDs: " + stimIdsToTest.toString());

        List<String> textureTypesToTest = Arrays.asList("SHADE", "SPECULAR", "2D");

        // GENERATE TRIALS
        for (Long gaStimId : stimIdsToTest) {
            for (RGBColor color : calculateColorsToTest(gaStimId)) {
                for (String textureType : textureTypesToTest) {
                    // We use contrast 1.0 even for 2D stimuli because we used the lightness to calculate
                    // an RGB value in fetchColorsToTest(). We did this because contrast doesn't change drawing of
                    // 3D stimuli, only 2D stimuli. So here we modulate the brightness on both 3D and 2D
                    // stimuli with rgb color only, not contrast.
                    TwoDVsThreeDStim stim = new TwoDVsThreeDStim(this, gaStimId, textureType, color, 1.0);
                    stims.add(stim);
                }
            }
        }
    }

    @Override
    protected void writeTrials() {
        List<Long> allStimIds = new ArrayList<>();

        for (Stim stim : getStims()) {
            stim.writeStim();
            Long stimId = stim.getStimId();
            for (int i = 0; i < numTrialsPerStim; i++) {
                allStimIds.add(stimId);
            }
        }

        Collections.shuffle(allStimIds);

        long lastTaskId = -1L;
        for (Long stimId : allStimIds) {
            long taskId = getGlobalTimeUtil().currentTimeMicros();
            while (taskId == lastTaskId) {
                taskId = getGlobalTimeUtil().currentTimeMicros();
            }
            lastTaskId = taskId;

            getDbUtil().writeTaskToDo(taskId, stimId, -1, genId);
        }
    }

    /**
     * Calculate the colors to test for a given stimulus ID.
     * We get the original color of the stimulus and then calculate
     * the new colors by changing the value (as in HSV, rather than lightness in HSL).

     * @param gaStimId
     * @return
     */
    private List<RGBColor> calculateColorsToTest(Long gaStimId) {
        List<RGBColor> colorsToTest = new ArrayList<>();

        RGBColor originalStimColor = fetchColorForStimId(gaStimId);
        if (originalStimColor != null) {
            float[] hsv = HSVUtils.rgbToHSV(originalStimColor);
            for (Double value : VALUES_TO_TEST) {
                hsv[2] = value.floatValue();
                RGBColor newColor = HSVUtils.hsvToRGB(hsv);
                colorsToTest.add(newColor);
            }
        } else {
            throw new RuntimeException("No color found for stimulus with gaStimId: " + gaStimId);
        }
        return colorsToTest;
    }

    private RGBColor fetchColorForStimId(Long stimId) {
        return colorManager.readProperty(stimId);
    }

    @Override
    public ColorPropertyManager getColorManager() {
        return colorManager;
    }

    @Override
    public void setColorManager(ColorPropertyManager colorManager) {
        this.colorManager = colorManager;
    }
}