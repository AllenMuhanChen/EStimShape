package org.xper.allen.twodvsthreed;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.app.twodvsthreed.TwoDVsThreeDConfig;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.allen.stimproperty.ColorPropertyManager;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.HSLUtils;
import org.xper.util.FileUtil;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class TwoDThreeDLightnessTrialGenerator extends TwoDVsThreeDTrialGenerator {
    public static final List<Double> LIGHTNESSES_TO_TEST= Arrays.asList(0.2, 0.4, 0.6, 0.8, 1.0);
    private static final int TOP_N_STIMS_PER_LINEAGE = 2; // Number of top stimuli to select per lineage
//    public static final List<Double> LIGHTNESSES_TO_TEST = Arrays.asList(0.2);




    public int numTrialsPerStim = 5;
    private ColorPropertyManager colorManager;


    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"),
                TwoDVsThreeDConfig.class
        );
        TwoDThreeDLightnessTrialGenerator gen = context.getBean(TwoDThreeDLightnessTrialGenerator.class, "generator2");
        gen.generate();
    }

    @Override
    protected void addTrials() {
        colorManager = new ColorPropertyManager(new JdbcTemplate(gaDataSource));

        List<Long> stimIdsToTest = fetchStimIdsToTest();
        List<String> textureTypesToTest = Arrays.asList("SHADE", "SPECULAR", "2D");

        // GENERATE TRIALS
        for (Long stimId : stimIdsToTest) {
            List<RGBColor> colorsToTest = fetchColorsToTest(stimId);
            for (RGBColor color : colorsToTest) {
                for (String textureType : textureTypesToTest) {
                    TwoDVsThreeDStim stim = new TwoDVsThreeDStim(this, stimId, textureType, color);
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

    protected void shuffleTrials() {
        Collections.shuffle(getStims());
    }

    private List<Long> getCompleteLineages() {
        JdbcTemplate jdbcTemplate = new JdbcTemplate(gaDataSource);

        // First, find the highest regime number
        Integer maxRegime = (Integer) jdbcTemplate.queryForObject(
                "SELECT MAX(CAST(regime AS SIGNED)) FROM LineageGaInfo",
                Integer.class
        );

        if (maxRegime == null) {
            return new ArrayList<>();
        }

        // Then find all lineages that reached this regime
        return jdbcTemplate.query(
                "SELECT DISTINCT lineage_id FROM LineageGaInfo WHERE regime = ?",
                new Object[]{String.valueOf(maxRegime)},
                new RowMapper() {
                    @Override
                    public Long mapRow(ResultSet rs, int rowNum) throws SQLException, SQLException {
                        return rs.getLong("lineage_id");
                    }
                }
        );
    }

    private List<Long> getTopStimsForLineage(Long lineageId) {
        JdbcTemplate jdbcTemplate = new JdbcTemplate(gaDataSource);

        return jdbcTemplate.query(
                "SELECT stim_id FROM StimGaInfo " +
                        "WHERE lineage_id = ? " +
                        "ORDER BY response DESC " +
                        "LIMIT ?",
                new Object[]{lineageId, TOP_N_STIMS_PER_LINEAGE},
                new RowMapper() {
                    @Override
                    public Long mapRow(ResultSet rs, int rowNum) throws SQLException {
                        return rs.getLong("stim_id");
                    }
                }
        );
    }

    private List<Long> fetchStimIdsToTest() {
        // Get all complete lineages
        List<Long> completeLineages = getCompleteLineages();

        // For each lineage, get top performing stimuli
        List<Long> allTopStims = new ArrayList<>();
        for (Long lineageId : completeLineages) {
            List<Long> lineageTopStims = getTopStimsForLineage(lineageId);
            allTopStims.addAll(lineageTopStims);
        }

        // Remove any duplicates and return
        return allTopStims;
    }


    private List<RGBColor> fetchColorsToTest(Long stimId) {
        List<RGBColor> colorsToTest = new ArrayList<>();

        RGBColor originalStimColor  = fetchColorForStimId(stimId);
        float[] hsv = HSLUtils.rgbToHSV(originalStimColor);
        for (Double lightness : LIGHTNESSES_TO_TEST) {
            hsv[2] = lightness.floatValue();
            RGBColor newColor = HSLUtils.hsvToRGB(hsv);

            colorsToTest.add(newColor);
        }
        return colorsToTest;

    }

    private RGBColor fetchColorForStimId(Long stimId) {
        return colorManager.readProperty(stimId);
    }

    public DataSource getGaDataSource() {
        return gaDataSource;
    }

    public void setGaDataSource(DataSource gaDataSource) {
        this.gaDataSource = gaDataSource;
    }

    public String getGaSpecPath() {
        return gaSpecPath;
    }

    public void setGaSpecPath(String gaSpecPath) {
        this.gaSpecPath = gaSpecPath;
    }

    public ReceptiveFieldSource getRfSource() {
        return rfSource;
    }

    public void setRfSource(ReceptiveFieldSource rfSource) {
        this.rfSource = rfSource;
    }
}