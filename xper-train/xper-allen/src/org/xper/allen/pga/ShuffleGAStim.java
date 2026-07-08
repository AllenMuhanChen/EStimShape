package org.xper.allen.pga;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.contrasts.PythonImageProcessor;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.shuffle.ShuffleStim;
import org.xper.allen.shuffle.ShuffleType;
import org.xper.allen.shuffle.ShuffleTypePropertyManager;

import javax.vecmath.Point3d;
import java.io.IOException;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

/**
 * GA side-test counterpart of {@link ShuffleStim}.
 *
 * Reproduces the parent stimulus faithfully (same shape, texture, color, size, position) and
 * then runs the matching pixel / phase / magnitude shuffle script on the rendered image. This
 * is created by {@link FromDbGABlockGenerator} whenever it encounters a "SHUFFLE_&lt;TYPE&gt;"
 * stim_type written by the Python ShuffleSideTest, replacing the old post-hoc
 * ShuffleTrialGenerator.
 */
public class ShuffleGAStim extends GAStim<GAMatchStick, AllenMStickData> {

    private final ShuffleType shuffleType;
    private final ShuffleTypePropertyManager shuffleTypeManager;

    public ShuffleGAStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, ShuffleType shuffleType) {
        // "PARENT" texture + no average-RGB swap: keep the parent's texture and color as-is.
        super(stimId, generator, parentId, "PARENT", false);
        this.shuffleType = shuffleType;
        this.shuffleTypeManager = new ShuffleTypePropertyManager(
                new JdbcTemplate(generator.getDbUtil().getDataSource()));
    }

    @Override
    protected void chooseRFStrategy() {
        rfStrategy = rfStrategyManager.readProperty(parentId);
    }

    @Override
    protected void chooseSize() {
        sizeDiameterDegrees = sizeManager.readProperty(parentId);
    }

    @Override
    protected void choosePosition() {
        position = positionManager.readProperty(parentId);
    }

    @Override
    protected GAMatchStick createMStick() {
        // Faithfully redraw the parent at its own center of mass (mirrors the post-hoc ShuffleStim).
        Point3d centerOfMass = getTargetsCenterOfMass(parentId);
        GAMatchStick mStick = new GAMatchStick(centerOfMass);
        mStick.setRf(generator.getReceptiveField());
        mStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        mStick.setStimColor(color);
        mStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");
        return mStick;
    }

    /**
     * Overrides {@link GAStim#writeStim()} so that the shuffle script runs on the raw PNG before
     * the path is converted to the experiment machine's view, and so the rendered image (rather
     * than the spec) is what gets shuffled.
     */
    @Override
    public void writeStim() {
        setProperties();
        GAMatchStick mStick = createMStick();

        // GAStim.writeStimProperties() persists averageRGB and NPEs on null, so populate it.
        averageRGB = generator.getPngMaker().getWindow().calculateAverageRGB(mStick);

        saveMStickSpec(mStick);

        // Draw the parent reproduction, shuffle the raw PNG, then convert to the experiment path.
        List<String> labels = new LinkedList<>();
        labels.add("base");
        String rawPngPath = generator.getPngMaker().createAndSavePNG(
                mStick, stimId, labels, generator.getGeneratorPngPath());
        String shuffledRawPath = shufflePng(rawPngPath);
        String experimentPngPath = generator.convertPngPathToExperiment(shuffledRawPath);

        drawThumbnails(mStick);

        AllenMStickData mStickData = (AllenMStickData) mStick.getMStickData();
        writeStimSpec(experimentPngPath, mStickData);

        writeStimProperties();
        shuffleTypeManager.writeProperty(stimId, shuffleType);
    }

    private String shufflePng(String originalPngPath) {
        String scriptPath = ShuffleStim.scriptPathsForShuffleTypes.get(shuffleType);
        if (scriptPath == null) {
            throw new IllegalArgumentException("No script path found for shuffle type: " + shuffleType);
        }
        PythonImageProcessor processor = PythonImageProcessor.withVirtualEnv(
                scriptPath, "/home/connorlab/miniconda3/envs/EStimShapeAnalysis");
        List<String> extraArgs = ShuffleStim.extraScriptArgsForShuffleTypes.getOrDefault(
                shuffleType, Collections.<String>emptyList());
        try {
            return processor.processImage(originalPngPath, shuffleType.toString(), extraArgs).getAbsolutePath();
        } catch (IOException e) {
            throw new RuntimeException(e);
        } catch (InterruptedException e) {
            throw new RuntimeException(e);
        } catch (PythonImageProcessor.ImageProcessingException e) {
            System.out.println("Error processing image with script: " + scriptPath);
            throw new RuntimeException(e);
        }
    }
}
