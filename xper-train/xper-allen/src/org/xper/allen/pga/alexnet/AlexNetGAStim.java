package org.xper.allen.pga.alexnet;

import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.LinkedList;
import java.util.List;

public abstract class AlexNetGAStim <T extends AlexNetGAMatchStick, D extends AlexNetGAMStickData> implements Stim {
    protected final FromDbAlexNetGABlockGenerator generator;
    protected final Long parentId;
    protected Long stimId;
    protected String textureType;
    protected RGBColor color;
    protected Coordinates2D location;
    protected float[] light_position;
    protected double sizeDiameter;
    protected double magnitude;
    protected double contrast;

    public AlexNetGAStim(FromDbAlexNetGABlockGenerator generator, Long parentId, Long stimId, String textureType, RGBColor color, Coordinates2D location, float[] light_position, double sizeDiameter, double magnitude, double contrast) {
        this.generator = generator;
        this.parentId = parentId;
        this.stimId = stimId;
        this.textureType = textureType;
        this.color = color;
        this.location = location;
        this.light_position = light_position;
        this.sizeDiameter = sizeDiameter;
        this.magnitude = magnitude;
        this.contrast = contrast;
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        int nTries = 0;
        T mStick = null;
        int maxTries = 100;
        while(nTries < maxTries) {
            nTries++;
            try {
                mStick = createMStick();
                System.out.println("SUCCESSFUL CREATION OF MORPHED MATCHSTICK OF TYPE: " + this.getClass().getSimpleName());
                break;
            } catch (MorphedMatchStick.MorphException me) {
                mStick = null;
                System.out.println("Morphing failed, trying again with new parameters");
            }
        }

        if (nTries == maxTries && mStick == null) {
            System.err.println("CRITICAL ERROR: COULD NOT GENERATE MORPHED MATCHSTICK  OF TYPE" + this.getClass().getSimpleName()+"AFTER 10 TRIES. GENERATING RAND...");
            throw new RuntimeException("CRITICAL ERROR: COULD NOT GENERATE MORPHED MATCHSTICK  OF TYPE" + this.getClass().getSimpleName());
        }


        saveMStickSpec(mStick);
        String pngPath = drawPngs(mStick);
        D mStickData = (D) mStick.getMStickData();
        writeStimSpec(pngPath, mStickData);
    }

    protected void saveMStickSpec(T mStick) {
        AllenMStickSpec mStickSpec = createMStickSpec(mStick);
        mStickSpec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(stimId), true);
    }

    public static <T extends AlexNetGAMatchStick> AllenMStickSpec createMStickSpec(T mStick) {
        AllenMStickSpec mStickSpec = new AllenMStickSpec();
        mStickSpec.setMStickInfo(mStick, true);
        return mStickSpec;
    }

    protected String drawPngs(T mStick) {
        //draw pngs
        List<String> labels = new LinkedList<>();
        labels.add(Long.toString(parentId));
        String pngPath = generator.getDrawingManager().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        return pngPath;
    }

    protected void writeStimSpec(String pngPath, D mStickData) {
        writeStimPath(stimId, pngPath);
        writeStimSpec(stimId, mStickData.toXml());
    }

    protected abstract T createMStick();


    @Override
    public Long getStimId() {
        return stimId;
    }

    public void writeStimPath(Long stimId, String path) {
        String query = "INSERT INTO StimPath (stim_id, path) VALUES (?, ?) " +
                "ON DUPLICATE KEY UPDATE path = ?";

        try (Connection conn = generator.dbUtil.getDataSource().getConnection();
             PreparedStatement stmt = conn.prepareStatement(query)) {

            stmt.setLong(1, stimId);
            stmt.setString(2, path);
            stmt.setString(3, path);

            stmt.executeUpdate();

        } catch (SQLException e) {
            throw new RuntimeException("Error writing to StimPath table", e);
        }
    }

    public void writeStimSpec(Long stimId, String spec) {
        String query = "INSERT INTO StimSpec (id, spec) VALUES (?, ?) " +
                "ON DUPLICATE KEY UPDATE spec = ?";

        try (Connection conn = generator.dbUtil.getDataSource().getConnection();
             PreparedStatement stmt = conn.prepareStatement(query)) {

            stmt.setLong(1, stimId);
            stmt.setString(2, spec);
            stmt.setString(3, spec);

            stmt.executeUpdate();

        } catch (SQLException e) {
            throw new RuntimeException("Error writing to StimSpec table", e);
        }
    }


}