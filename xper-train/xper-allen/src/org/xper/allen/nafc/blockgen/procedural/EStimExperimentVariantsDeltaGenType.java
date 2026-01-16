package org.xper.allen.nafc.blockgen.procedural;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.nafc.NAFCStim;

import javax.sql.DataSource;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.Random;

public class EStimExperimentVariantsDeltaGenType extends EStimExperimentVariantsGenType{

    public String getLabel() {
        return "EStimExperimentDeltaVariants";
    }

    @Override
    protected List<NAFCStim> genTrials(EStimExperimentGenType.EStimExperimentGenParameters parameters) {
        List<NAFCStim> newBlock = new LinkedList<>();

        int morphIndex = parameters.compId;
        int noiseIndex = morphIndex;
        List<Long> assignedVariantIds = new  LinkedList<>();
        int numTrials;
        if (parameters.getNumTrials() <= 0){
            int numSets = parameters.getNumTrials() * -1;

            DataSource gaDataSource = ((EStimShapeExperimentTrialGenerator) generator).getGaDataSource();
            JdbcTemplate gaJDBCTemplate = new JdbcTemplate(gaDataSource);

            // Get all non-excluded variants that have included deltas
            List<Long> allVariantIds = gaJDBCTemplate.queryForList(
                    "SELECT DISTINCT variant_id FROM IncludedDeltas WHERE included = TRUE",
                    Long.class
            );

            if (allVariantIds.isEmpty()) {
                throw new RuntimeException("No variants with included deltas found in IncludedDeltas table. " +
                        "Run the PlotVariantDeltas analysis pipeline first to populate this table.");
            }

            numTrials = allVariantIds.size();
            for  (int i = 0; i < numSets; i++) {
                assignedVariantIds.addAll(allVariantIds);
            }
        } else{
            numTrials = parameters.getNumTrials();
            assignedVariantIds = distributeVariantIds(parameters.getNumTrials());
        }


        //use that trial's base matchstick to generate the rest of the trials

        for (int i = 0; i < numTrials; i++) {
            if (parameters.stimId == 0){
                long variantId = assignedVariantIds.get(i);

                EStimShapeVariantsNAFCStim stim = new EStimShapeVariantsDeltaNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        variantId,
                        false,
                        parameters.isEStimEnabled, parameters.eStimSpecId);
                newBlock.add(stim);

                EStimShapeVariantsNAFCStim deltaStim = new EStimShapeVariantsDeltaNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        variantId,
                        true,
                        parameters.isEStimEnabled, parameters.eStimSpecId);
                newBlock.add(deltaStim);
            } else {
                //using estim value from the GUI field
                EStimShapeVariantsNAFCStim stim = new EStimShapeVariantsDeltaNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        parameters.stimId,
                        false,
                        parameters.isEStimEnabled,
                        parameters.eStimSpecId);
                newBlock.add(stim);

                EStimShapeVariantsNAFCStim deltaStim = new EStimShapeVariantsDeltaNAFCStim(
                        (EStimShapeExperimentTrialGenerator) generator,
                        parameters.getProceduralStimParameters(),
                        parameters.stimId,
                        true,
                        parameters.isEStimEnabled,
                        parameters.eStimSpecId);
                newBlock.add(deltaStim);
            }
        }
//        Collections.shuffle(newBlock);
        return newBlock;
    }

    private List<Long> distributeVariantIds(int numTrials) {
        // HERE WE ARE GOING TO DISTRIBUTE THE VARIANT IDS
        List<Long> variantIds = new LinkedList<>();
        DataSource gaDataSource = ((EStimShapeExperimentTrialGenerator) generator).getGaDataSource();
        JdbcTemplate gaJDBCTemplate = new JdbcTemplate(gaDataSource);

        // Get all non-excluded variants that have included deltas
        List<Long> allVariantIds = gaJDBCTemplate.queryForList(
                "SELECT DISTINCT variant_id FROM IncludedDeltas WHERE included = TRUE",
                Long.class
        );

        if (allVariantIds.isEmpty()) {
            throw new RuntimeException("No variants with included deltas found in IncludedDeltas table. " +
                    "Run the PlotVariantDeltas analysis pipeline first to populate this table.");
        }

        //Shuffle variantIds, so if we have less trials than variants, we don't randomly sample the same variant twice.
        Collections.shuffle(allVariantIds);
        for (int i = 0; i < allVariantIds.size(); i++) {     //if we have same number of trials and variants, then we'll sample
            if (i >= numTrials)
                break;
            variantIds.add(allVariantIds.get(i));
        }

        //Sample remaining after putting one full list
        int remaining = numTrials - variantIds.size();
        Collections.shuffle(allVariantIds);
        for (int i = 0; i < remaining; i++) {
            variantIds.add(allVariantIds.get(i));
        }

        return variantIds;
    }
}
