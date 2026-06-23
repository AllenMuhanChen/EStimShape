package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.nafc.NAFCStim;

import javax.sql.DataSource;
import java.util.LinkedList;
import java.util.List;

/**
 * Generates trials where the sample has the tuned-for component deleted; choices include the
 * variant (intact), the paired delta, and the deleted sample. Mirrors
 * {@link EStimExperimentVariantsDeltaGenType} for variant selection but emits a single
 * {@link EStimShapeVariantsDeletedNAFCStim} per variantId.
 */
public class EStimExperimentVariantsDeletedGenType extends EStimExperimentVariantsDeltaGenType {

    @Override
    public String getLabel() {
        return "EStimExperimentRemovedVariants";
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
            EStimShapeVariantsDeletedNAFCStim stim = new EStimShapeVariantsDeletedNAFCStim(
                    (EStimShapeExperimentTrialGenerator) generator,
                    parameters.getProceduralStimParameters(),
                    variantId,
                    parameters.isEStimEnabled,
                    parameters.eStimSpecId);
            stim.setIncludeRemovedChoice(parameters.includeRemovedChoice);
            newBlock.add(stim);
        }
        return newBlock;
    }
}
