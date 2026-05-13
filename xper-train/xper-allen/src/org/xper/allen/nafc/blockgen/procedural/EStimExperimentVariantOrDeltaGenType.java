package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.nafc.NAFCStim;

import javax.sql.DataSource;
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
                    isDelta,
                    parameters.isEStimEnabled,
                    parameters.eStimSpecId);
            stim.setIncludeRemovedChoice(parameters.includeRemovedChoice);
            newBlock.add(stim);
        }
        return newBlock;
    }
}
