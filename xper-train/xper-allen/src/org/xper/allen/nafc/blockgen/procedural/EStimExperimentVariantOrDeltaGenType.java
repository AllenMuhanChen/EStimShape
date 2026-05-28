package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.nafc.NAFCStim;

import javax.sql.DataSource;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

public class EStimExperimentVariantOrDeltaGenType extends EStimExperimentVariantsDeltaGenType {

    private boolean isDelta;

    public void setDelta(boolean isDelta) {
        this.isDelta = isDelta;
    }

    public boolean isDelta() {
        return isDelta;
    }

    @Override
    public String getLabel() {
        return isDelta ? "EStimExperimentDeltasOnly" : "EStimExperimentVariantsOnly";
    }

    @Override
    protected List<NAFCStim> genTrials(EStimExperimentGenType.EStimExperimentGenParameters parameters) {
        if (isDelta) {
            return genDeltaOnlyTrials(parameters);
        }
        return genVariantOnlyTrials(parameters);
    }

    private List<NAFCStim> genVariantOnlyTrials(EStimExperimentGenType.EStimExperimentGenParameters parameters) {
        List<NAFCStim> newBlock = new LinkedList<>();

        List<Long> assignedVariantIds = new LinkedList<>();
        int numTrials;
        if (parameters.getNumTrials() <= 0) {
            int numSets = parameters.getNumTrials() * -1;

            DataSource gaDataSource = ((EStimShapeExperimentTrialGenerator) generator).getGaDataSource();
            JdbcTemplate gaJDBCTemplate = new JdbcTemplate(gaDataSource);

            List<Long> allVariantIds = gaJDBCTemplate.queryForList(
                    "SELECT DISTINCT variant_id FROM IncludedDeltas WHERE included = TRUE",
                    Long.class
            );

            if (allVariantIds.isEmpty()) {
                throw new RuntimeException("No variants with included deltas found in IncludedDeltas table. " +
                        "Run the PlotVariantDeltas analysis pipeline first to populate this table.");
            }

            numTrials = allVariantIds.size() * numSets;
            for (int i = 0; i < numSets; i++) {
                assignedVariantIds.addAll(allVariantIds);
            }
        } else {
            numTrials = parameters.getNumTrials();
            assignedVariantIds = distributeVariantIds(parameters.getNumTrials());
        }

        for (int i = 0; i < numTrials; i++) {
            long variantId = parameters.stimId == 0 ? assignedVariantIds.get(i) : parameters.stimId;

            EStimShapeVariantsNAFCStim stim = new EStimShapeVariantsDeltaNAFCStim(
                    (EStimShapeExperimentTrialGenerator) generator,
                    parameters.getProceduralStimParameters(),
                    variantId,
                    false,
                    parameters.isEStimEnabled,
                    parameters.eStimSpecId);
            stim.setIncludeRemovedChoice(parameters.includeRemovedChoice);
            newBlock.add(stim);
        }
        return newBlock;
    }

    /**
     * Iterate over (variant_id, delta_id) pairs so each included delta becomes its own sample
     * trial. With N deltas across the included variants and numSets sets, this yields N * numSets
     * trials — vs. the variant-only path which yields numVariants * numSets.
     */
    private List<NAFCStim> genDeltaOnlyTrials(EStimExperimentGenType.EStimExperimentGenParameters parameters) {
        List<NAFCStim> newBlock = new LinkedList<NAFCStim>();

        DataSource gaDataSource = ((EStimShapeExperimentTrialGenerator) generator).getGaDataSource();
        JdbcTemplate gaJDBCTemplate = new JdbcTemplate(gaDataSource);

        RowMapper pairMapper = new RowMapper() {
            public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                return new long[]{rs.getLong("variant_id"), rs.getLong("delta_id")};
            }
        };

        List allPairs;
        if (parameters.stimId == 0) {
            allPairs = gaJDBCTemplate.query(
                    "SELECT variant_id, delta_id FROM IncludedDeltas WHERE included = TRUE",
                    pairMapper
            );
        } else {
            allPairs = gaJDBCTemplate.query(
                    "SELECT variant_id, delta_id FROM IncludedDeltas WHERE included = TRUE AND variant_id = ?",
                    new Object[]{parameters.stimId},
                    pairMapper
            );
        }
        if (allPairs.isEmpty()) {
            throw new RuntimeException("No included delta pairs found in IncludedDeltas table" +
                    (parameters.stimId == 0 ? "." : " for variant_id " + parameters.stimId + ".") +
                    " Run the PlotVariantDeltas analysis pipeline first to populate this table.");
        }

        List assignedPairs = new LinkedList();
        if (parameters.getNumTrials() <= 0) {
            int numSets = parameters.getNumTrials() * -1;
            for (int i = 0; i < numSets; i++) {
                assignedPairs.addAll(allPairs);
            }
        } else {
            int numTrials = parameters.getNumTrials();
            Collections.shuffle(allPairs);
            for (int i = 0; i < numTrials; i++) {
                assignedPairs.add(allPairs.get(i % allPairs.size()));
            }
        }

        for (int i = 0; i < assignedPairs.size(); i++) {
            long[] pair = (long[]) assignedPairs.get(i);
            long variantId = pair[0];
            long sampleDeltaId = pair[1];

            EStimShapeVariantsNAFCStim stim = new EStimShapeVariantsDeltaNAFCStim(
                    (EStimShapeExperimentTrialGenerator) generator,
                    parameters.getProceduralStimParameters(),
                    variantId,
                    Long.valueOf(sampleDeltaId),
                    parameters.isEStimEnabled,
                    parameters.eStimSpecId);
            stim.setIncludeRemovedChoice(parameters.includeRemovedChoice);
            newBlock.add(stim);
        }
        return newBlock;
    }
}
