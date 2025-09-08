package org.xper.allen.shuffle;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.contrasts.PythonImageProcessor;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.twodvsthreed.TwoDVsThreeDStim;
import org.xper.allen.twodvsthreed.TwoDVsThreeDTrialGenerator;
import org.xper.drawing.RGBColor;
import org.xper.util.ThreadUtil;

import javax.vecmath.Point3d;
import java.io.IOException;
import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class ShuffleStim extends TwoDVsThreeDStim {
    protected ShuffleType shuffleType;
    public static Map<ShuffleType, String> scriptPathsForShuffleTypes = new HashMap<ShuffleType, String>(){
        {
            put(ShuffleType.PIXEL, "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/imageshuffle/pixel_shuffle.py");
            put(ShuffleType.PHASE, "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/imageshuffle/phase_shuffle.py");
            put(ShuffleType.MAGNITUDE, "/home/connorlab/git/EStimShape/EStimShapeAnalysis/src/imageshuffle/magnitude_shuffle.py");
        }
    };
    ShuffleTypePropertyManager shuffleTypeManager;
    /**
     * @param generator
     * @param gaStimId    : the stimulus id from the GA experiment we are changing the shading / color / contrast of for testing
     * @param textureType : "2D", "SHADE", "SPECULAR" or "USE_PARENT"
     */
    public ShuffleStim(TwoDVsThreeDTrialGenerator generator, long gaStimId, String textureType, ShuffleType shuffleType) {
        super(generator, gaStimId, textureType, null, -1.0);
        this.shuffleType = shuffleType;

        this.shuffleTypeManager = new ShuffleTypePropertyManager(new JdbcTemplate(generator.getDbUtil().getDataSource()));

    }

    @Override
    public void writeStim() {
        //TODO: check if we've already drawn this stim once?
        stimId = generator.getGlobalTimeUtil().currentTimeMicros();
        Point3d centerOfMass = getTargetsCenterOfMass();
        GAMatchStick mStick = new GAMatchStick(centerOfMass); //this constructor ignores RF for purposes of drawing
        mStick.setRf(receptiveField); //we need reference to this to calculate position for thumbnail
        mStick.setProperties(sizeDiameterDegrees, textureType, contrast);
        mStick.setStimColor(color);
        mStick.genMatchStickFromFile(targetSpecPath, new double[]{0,0,0});

        String originalPngPath = drawPng(mStick);
        ThreadUtil.sleep(100);

        // using python image process
        String shuffledPngPath;
        if (shuffleType.equals(ShuffleType.NONE)) {
            shuffledPngPath = originalPngPath; // no shuffling, use original PNG
        } else {
            String scriptPath = scriptPathsForShuffleTypes.get(shuffleType);
            if (scriptPath == null) {
                throw new IllegalArgumentException("No script path found for shuffle type: " + shuffleType);
            }
            PythonImageProcessor processor = PythonImageProcessor.withVirtualEnv(scriptPath, "/home/connorlab/miniconda3/envs/EStimShapeAnalysis");
            try {
                shuffledPngPath = processor.processImage(originalPngPath, shuffleType.toString()).getAbsolutePath();
            } catch (IOException e) {
                throw new RuntimeException(e);
            } catch (InterruptedException e) {
                throw new RuntimeException(e);
            } catch (PythonImageProcessor.ImageProcessingException e) {
                System.out.println("Error processing image with script: " + scriptPath);

                throw new RuntimeException(e);
            }
        }
        shuffledPngPath = generator.convertPngPathToExperiment(shuffledPngPath);
        AllenMStickData mStickData = (AllenMStickData) mStick.getMStickData();
        writeStimSpec(shuffledPngPath, mStickData);

        writeStimProperties();
    }

    protected String drawPng(AllenMatchStick mStick) {
        //draw pngs
        String pngPath;
        List<String> labels = new LinkedList<>();
        if (shuffleType.equals(ShuffleType.NONE)) {
            pngPath = generator.getPngMaker().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        } else {
            labels.add("base");
            pngPath = generator.getPngMaker().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        }
        return pngPath;
    }

    protected void writeStimProperties() {
        super.writeStimProperties();
        shuffleTypeManager.writeProperty(stimId, shuffleType);
    }


}