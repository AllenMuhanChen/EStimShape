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
import org.xper.util.FileUtil;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class TwoDVsThreeDTrialGenerator extends AbstractMStickPngTrialGenerator<Stim> {
    private static final int TOP_N_STIMS_PER_LINEAGE = 2; // Number of top stimuli to select per lineage
    // Maximum number of stimuli to select per type

    @Dependency
    DataSource gaDataSource;

    @Dependency
    String gaSpecPath;

    @Dependency
    ReceptiveFieldSource rfSource;

    private ColorPropertyManager colorManager;

    public int numTrialsPerStim = 5;
    public int startRank = 1; // Starting rank for selecting stimuli (1-based)
    public int endRank = 10; // Ending rank for selecting stimuli (inclusive)

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

        TwoDVsThreeDTrialGenerator gen = context.getBean(TwoDVsThreeDTrialGenerator.class, "generator");

        // Set the rank range
        gen.startRank = startRank;
        gen.endRank = endRank;

        // Generate trials
        gen.generate();
    }

    @Override
    protected void addTrials() {
        List<Double> contrastsToTest = Arrays.asList(0.4, 1.0);

        // For 2D, look for "2D", For 3D look for "SHADE" or "SPECULAR"
        List<Long> twoDStimIds = fetchTopNStimIds("2D");
        List<Long> threeDStimIds = fetchTopNStimIds("3D");

        // GENERATE TRIALS
        for (Long stimId : twoDStimIds) {
            double useParentContrast = -1.0;
            TwoDVsThreeDStim stim = new TwoDVsThreeDStim(this, stimId, "SHADE", null, useParentContrast);
            stims.add(stim);

            stim = new TwoDVsThreeDStim(this, stimId, "SPECULAR", null, useParentContrast);
            stims.add(stim);

        }

        for (Long stimId : threeDStimIds) {
            for (Double contrast : contrastsToTest) {
                TwoDVsThreeDStim stim = new TwoDVsThreeDStim(this, stimId, "2D", null, contrast);
                stims.add(stim);
            }
        }
    }

    /**
     * Fetches stimuli ids for a specific texture type within a specified rank range
     * @param textureType The texture type to fetch ("2D" or "3D")
     * @return List of stimuli IDs
     */
    List<Long> fetchTopNStimIds(String textureType) {
        JdbcTemplate jdbcTemplate = new JdbcTemplate(gaDataSource);
        List<Long> resultStimIds = new ArrayList<>();

        // Calculate LIMIT and OFFSET parameters for pagination
        int limit = endRank - startRank + 1;
        int offset = startRank - 1; // MySQL is 0-based for OFFSET

        // If textureType is "3D", we need to look for both "SHADE" and "SPECULAR"
        if ("3D".equals(textureType)) {
            // Query for stimuli with "SHADE" or "SPECULAR" texture types
            resultStimIds = jdbcTemplate.query(
                    "SELECT s.stim_id FROM StimGaInfo s " +
                            "JOIN StimTexture t ON s.stim_id = t.stim_id " +
                            "WHERE t.texture_type IN ('SHADE', 'SPECULAR') " +
                            "ORDER BY s.response DESC " +
                            "LIMIT ? OFFSET ?",
                    new Object[]{limit, offset},
                    new RowMapper() {
                        @Override
                        public Long mapRow(ResultSet rs, int rowNum) throws SQLException {
                            return rs.getLong("stim_id");
                        }
                    }
            );
            System.out.println("3D Stimuli Ids: " + resultStimIds.toString());
        } else {
            // Query for stimuli with the specified texture type
            resultStimIds = jdbcTemplate.query(
                    "SELECT s.stim_id FROM StimGaInfo s " +
                            "JOIN StimTexture t ON s.stim_id = t.stim_id " +
                            "WHERE t.texture_type = ? " +
                            "ORDER BY s.response DESC " +
                            "LIMIT ? OFFSET ?",
                    new Object[]{textureType, limit, offset},
                    new RowMapper() {
                        @Override
                        public Long mapRow(ResultSet rs, int rowNum) throws SQLException {
                            return rs.getLong("stim_id");
                        }
                    }
            );
            System.out.println("2D Stimuli Ids: " + resultStimIds.toString());
        }

        return resultStimIds;
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
                    public Long mapRow(ResultSet rs, int rowNum) throws SQLException {
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

    public int getNumTrialsPerStim() {
        return numTrialsPerStim;
    }

    public void setNumTrialsPerStim(int numTrialsPerStim) {
        this.numTrialsPerStim = numTrialsPerStim;
    }

    public ColorPropertyManager getColorManager() {
        return colorManager;
    }

    public void setColorManager(ColorPropertyManager colorManager) {
        this.colorManager = colorManager;
    }
}