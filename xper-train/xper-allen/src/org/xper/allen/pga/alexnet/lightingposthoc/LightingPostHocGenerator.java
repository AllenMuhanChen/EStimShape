package org.xper.allen.pga.alexnet.lightingposthoc;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.allen.pga.alexnet.AlexNetDrawingManager;
import org.xper.allen.pga.alexnet.FromDbAlexNetGABlockGenerator;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.exception.VariableNotFoundException;

import java.io.FileInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Properties;

public class LightingPostHocGenerator extends FromDbAlexNetGABlockGenerator {


    public static void main(String[] args) throws IOException, ClassNotFoundException {
        Properties props = new Properties();
        try {
            String type = args[0];
            // Load the properties file
            props.load(Files.newInputStream(Paths.get("/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.alexnet." + type)));
        } catch (Exception e) {
            props.load(new FileInputStream("/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.alexnet.lightingposthoc"));
        }

        // Set as system properties
        Properties sysProps = System.getProperties();
        sysProps.putAll(props);
        System.setProperties(sysProps);

        // Get the config class and create context
        Class<?> configClass = Class.forName(props.getProperty("experiment.ga.config_class"));
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(configClass);

        // Get and run generator
        LightingPostHocGenerator generator = context.getBean(LightingPostHocGenerator.class);

        generator.generate();
    }


    @Override
    protected void addTrials() {
        List<StimInstruction> stimInstructions = readStimInstructions();
        for (StimInstruction instruction : stimInstructions) {
            if (!hasStimPathEntry(instruction.getStimId())) {
                // TODO: Handle stim generation based on instruction type
                stims.add(new PostHocStim(this, instruction));
            }
        }
    }
    private List<StimInstruction> readStimInstructions() {
        JdbcTemplate jt = new JdbcTemplate(getDbUtil().getDataSource());
        return jt.query(
                "SELECT * FROM StimInstructions",
                new RowMapper() {
                    @Override
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        StimInstruction instruction = new StimInstruction();
                        instruction.setStimId(rs.getLong("stim_id"));
                        instruction.setParentId(rs.getLong("parent_id"));
                        instruction.setStimType(rs.getString("stim_type"));
                        instruction.setTextureType(rs.getString("texture_type"));
                        instruction.setLightPosX(rs.getFloat("light_pos_x"));
                        instruction.setLightPosY(rs.getFloat("light_pos_y"));
                        instruction.setLightPosZ(rs.getFloat("light_pos_z"));
                        instruction.setLightPosW(rs.getFloat("light_pos_w"));
                        instruction.setContrast(rs.getDouble("contrast"));
                        return instruction;
                    }
                }
        );
    }

    private boolean hasStimPathEntry(long stimId) {
        JdbcTemplate jt = new JdbcTemplate(getDbUtil().getDataSource());
        int count = (int) jt.queryForObject(
                "SELECT COUNT(*) FROM StimPath WHERE stim_id = ?",
                new Object[]{stimId},
                Integer.class
        );
        return count > 0;
    }

    @Override
    protected void writeTrials() {
        for (Stim stim : getStims()) {
            stim.writeStim();
        }
    }

    @Override
    protected void updateReadyGeneration() {

    }

    @Override
    protected void updateGenId() {
    }

    @Override
    protected void init() {
        getDrawingManager().createDrawerWindow();
    }


}

class StimInstruction {
    private long stimId;
    private long parentId;
    private String stimType;
    private String textureType;
    private float lightPosX;
    private float lightPosY;
    private float lightPosZ;
    private float lightPosW;
    private double contrast;

    // Getters and setters
    public long getStimId() { return stimId; }
    public void setStimId(long stimId) { this.stimId = stimId; }

    public long getParentId() { return parentId; }
    public void setParentId(long parentId) { this.parentId = parentId; }

    public String getStimType() { return stimType; }
    public void setStimType(String stimType) { this.stimType = stimType; }

    public String getTextureType() { return textureType; }
    public void setTextureType(String textureType) { this.textureType = textureType; }

    public float getLightPosX() { return lightPosX; }
    public void setLightPosX(float lightPosX) { this.lightPosX = lightPosX; }

    public float getLightPosY() { return lightPosY; }
    public void setLightPosY(float lightPosY) { this.lightPosY = lightPosY; }

    public float getLightPosZ() { return lightPosZ; }
    public void setLightPosZ(float lightPosZ) { this.lightPosZ = lightPosZ; }

    public float getLightPosW() { return lightPosW; }
    public void setLightPosW(float lightPosW) { this.lightPosW = lightPosW; }

    public double getContrast() { return contrast; }
    public void setContrast(double contrast) { this.contrast = contrast; }

    public float[] getLightPosition() {
        return new float[]{lightPosX, lightPosY, lightPosZ, lightPosW};
    }
}