package org.xper.allen.shuffle;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.app.shuffle.ShuffleConfig;
import org.xper.allen.app.twodvsthreed.TwoDVsThreeDConfig;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.allen.twodvsthreed.TwoDVsThreeDTrialGenerator;
import org.xper.util.FileUtil;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class ShuffleTrialGenerator extends TwoDVsThreeDTrialGenerator {

    private static final int NUM_BINS = 5;
    private static final int STIMS_PER_BIN = 2;

    private List<ShuffleType> shuffleTypes = Arrays.asList(
            ShuffleType.NONE,
            ShuffleType.PIXEL,
            ShuffleType.PHASE,
            ShuffleType.MAGNITUDE
    );

    public static void main(String[] args) {
        // Create and configure the generator
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"),
                ShuffleConfig.class
        );

        ShuffleTrialGenerator gen = context.getBean(ShuffleTrialGenerator.class, "generator");

        // Generate trials
        gen.generate();
    }

    @Override
    protected void addTrials() {
        // Read 3D stimuli uniformly sampled across the response distribution
        List<Long> threeDStimIds = fetchBinnedStimIds("3D");

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

    /**
     * Fetches stimuli ids for a specific texture type, uniformly sampled across
     * the response distribution. Divides the sorted-by-response stimuli into
     * NUM_BINS equally-sized bins and pulls the top STIMS_PER_BIN from each bin.
     */
    protected List<Long> fetchBinnedStimIds(String type) {
        JdbcTemplate jdbcTemplate = new JdbcTemplate(getGaDataSource());
        List<Long> resultStimIds = new ArrayList<>();

        int totalCount;
        if ("3D".equals(type)) {
            totalCount = (Integer) jdbcTemplate.queryForObject(
                    "SELECT COUNT(*) FROM StimGaInfo s " +
                            "JOIN StimTexture t ON s.stim_id = t.stim_id " +
                            "WHERE t.texture_type IN ('SHADE', 'SPECULAR')",
                    Integer.class
            );
        } else {
            totalCount = (Integer) jdbcTemplate.queryForObject(
                    "SELECT COUNT(*) FROM StimGaInfo s " +
                            "JOIN StimTexture t ON s.stim_id = t.stim_id " +
                            "WHERE t.texture_type = ?",
                    new Object[]{type},
                    Integer.class
            );
        }

        int binSize = totalCount / NUM_BINS;
        System.out.println("Total " + type + " stimuli: " + totalCount + ", bin size: " + binSize);

        for (int bin = 0; bin < NUM_BINS; bin++) {
            int offset = bin * binSize;
            List<Long> binStimIds;
            if ("3D".equals(type)) {
                binStimIds = jdbcTemplate.query(
                        "SELECT s.stim_id FROM StimGaInfo s " +
                                "JOIN StimTexture t ON s.stim_id = t.stim_id " +
                                "WHERE t.texture_type IN ('SHADE', 'SPECULAR') " +
                                "ORDER BY s.response DESC " +
                                "LIMIT ? OFFSET ?",
                        new Object[]{STIMS_PER_BIN, offset},
                        new RowMapper() {
                            @Override
                            public Long mapRow(ResultSet rs, int rowNum) throws SQLException {
                                return rs.getLong("stim_id");
                            }
                        }
                );
            } else {
                binStimIds = jdbcTemplate.query(
                        "SELECT s.stim_id FROM StimGaInfo s " +
                                "JOIN StimTexture t ON s.stim_id = t.stim_id " +
                                "WHERE t.texture_type = ? " +
                                "ORDER BY s.response DESC " +
                                "LIMIT ? OFFSET ?",
                        new Object[]{type, STIMS_PER_BIN, offset},
                        new RowMapper() {
                            @Override
                            public Long mapRow(ResultSet rs, int rowNum) throws SQLException {
                                return rs.getLong("stim_id");
                            }
                        }
                );
            }
            System.out.println("Bin " + bin + " (offset " + offset + ") stim IDs: " + binStimIds);
            resultStimIds.addAll(binStimIds);
        }

        return resultStimIds;
    }
}
