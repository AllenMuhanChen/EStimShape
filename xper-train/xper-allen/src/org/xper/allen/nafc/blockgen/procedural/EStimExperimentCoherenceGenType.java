package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.nafc.NAFCStim;
import org.xper.allen.nafc.blockgen.procedural.EStimExperimentGenType.EStimExperimentGenParameters;

import javax.sql.DataSource;
import javax.swing.*;
import java.util.LinkedList;
import java.util.List;

/**
 * Generates coherence trials: one {@link EStimShapeCoherenceNAFCStim} per variant. Mirrors
 * {@link EStimExperimentVariantsDeletedGenType} for variant selection (a single variant-role trial
 * per variantId), and adds a {@code coherence} field read from the GUI and threaded onto each stim.
 */
public class EStimExperimentCoherenceGenType extends EStimExperimentVariantsDeltaGenType {

    protected JTextField coherenceField;

    @Override
    public String getLabel() {
        return "EStimExperimentCoherence";
    }

    @Override
    public void initFields() {
        super.initFields();
        coherenceField = new JTextField("0.0", 10);
        labelsForFields.put(coherenceField, "coherence (-1..1, 0=balanced):");
        defaultsForFields.put(coherenceField, "0.0");
    }

    @Override
    public EStimExperimentGenParameters readFromFields() {
        EStimExperimentGenParameters params = super.readFromFields();
        params.coherence = Double.parseDouble(coherenceField.getText());
        return params;
    }

    @Override
    public void loadParametersIntoFields(GenParameters blockParams) {
        super.loadParametersIntoFields(blockParams);
        if (coherenceField != null && blockParams instanceof EStimExperimentGenParameters) {
            coherenceField.setText(String.valueOf(((EStimExperimentGenParameters) blockParams).coherence));
        }
    }

    @Override
    protected List<NAFCStim> genTrials(EStimExperimentGenParameters parameters) {
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

        // One coherence trial per (variant, included-delta) pair, so every delta of a variant is
        // tested as its own mixture rather than only the first.
        for (int i = 0; i < numTrials; i++) {
            long variantId = parameters.stimId == 0 ? assignedVariantIds.get(i) : parameters.stimId;
            for (Long deltaId : getIncludedDeltaIds(variantId)) {
                EStimShapeCoherenceNAFCStim stim = new EStimShapeCoherenceNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        variantId, deltaId,
                        parameters.isEStimEnabled, parameters.eStimSpecId,
                        parameters.coherence);
                stim.setIncludeRemovedChoice(parameters.includeRemovedChoice);
                newBlock.add(stim);
            }
        }
        return newBlock;
    }

    private List<Long> getIncludedDeltaIds(long variantId) {
        DataSource gaDataSource = ((EStimShapeExperimentTrialGenerator) generator).getGaDataSource();
        JdbcTemplate gaJDBCTemplate = new JdbcTemplate(gaDataSource);
        List<Long> deltaIds = gaJDBCTemplate.queryForList(
                "SELECT delta_id FROM IncludedDeltas WHERE variant_id = ? AND included = TRUE",
                new Object[]{variantId}, Long.class);
        if (deltaIds.isEmpty()) {
            throw new RuntimeException("No included deltas found for variant_id: " + variantId);
        }
        return deltaIds;
    }
}
