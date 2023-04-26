package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.morph.PruningMatchStick.PruningMStickData;
import org.xper.allen.ga.Branch;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.ga.regimescore.Regime;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.*;
import java.util.function.Consumer;

import static org.xper.allen.newga.blockgen.NewGABlockGenerator.STIM_TYPE_FOR_REGIME;

public class RegimeThreeComponentChooser {

    private final MultiGaDbUtil dbUtil;
    private final SpikeRateSource spikeRateSource;
    private double confidence;

    public RegimeThreeComponentChooser(MultiGaDbUtil dbUtil, SpikeRateSource spikeRateSource) {
        this.dbUtil = dbUtil;
        this.spikeRateSource = spikeRateSource;
    }

    /**
     * USE IF PARENT IS REGIME ONE
     * @param parentId
     * @param numComponentsToChoose
     * @return
     */
    public List<Integer> choose(Long parentId, int numComponentsToChoose) {
        List<Long> regimeTwoChildren = findRegimeTwoFamily(parentId);

        Map<Integer, Double> avgSpikeRateForCompsPreserved =
                calculateAverageSpikeRateAcrossComponentsPreservedIn(regimeTwoChildren);

       // Sort components by spike rate descending
         List<Integer> sortedComponents = new LinkedList<>(avgSpikeRateForCompsPreserved.keySet());
        sortedComponents.sort(new Comparator<Integer>() {
            @Override
            public int compare(Integer o1, Integer o2) {
                return avgSpikeRateForCompsPreserved.get(o2).compareTo(avgSpikeRateForCompsPreserved.get(o1));
            }
        });

        calculateConfidence(sortedComponents, avgSpikeRateForCompsPreserved);

//        // Choose the top numComponentsToChoose components
//        List<Integer> compsToChoose = new LinkedList<>();
//        ProbabilityTable<Integer> probTable = new ProbabilityTable<>(avgSpikeRateForCompsPreserved);
//        for (int i = 0; i < numComponentsToChoose; i++) {
//            compsToChoose.add(probTable.sampleWithoutReplacement());
//        }

        // Choose the top numComponentsToChoose components
        List<Integer> compsToChoose = new LinkedList<>();
        for (int i = 0; i < numComponentsToChoose; i++) {
            compsToChoose.add(sortedComponents.get(i));
        }

        return compsToChoose;
    }

    private void calculateConfidence(List<Integer> sortedComponents, Map<Integer, Double> avgSpikeRateForCompsPreserved) {
        // calculate
        Double topComponentSpikeRate = avgSpikeRateForCompsPreserved.get(sortedComponents.get(0));
        if (sortedComponents.size()>1) {
            Double secondComponentSpikeRate = avgSpikeRateForCompsPreserved.get(sortedComponents.get(1));
            confidence = (topComponentSpikeRate - secondComponentSpikeRate) / topComponentSpikeRate;
        }
        else {
            confidence = 1.0;
        }

    }

    public double getConfidence() {
        return confidence;
    }

    /**
     * Refers to the regime two ancestors or descendants whose preserved components
     * will be analyzed to determine what component to morph in a regime three child.
     * @param parentId
     * @return
     */
    private List<Long> findRegimeTwoFamily(long parentId) {
        Long lineageId = dbUtil.readLineageId(parentId);
        String lineageTreeXml = dbUtil.readLineageTreeSpec(lineageId);
        Branch<Long> lineageTree = Branch.fromXml(lineageTreeXml);
        LinkedList<Long> family = new LinkedList<>();

        // Find closest regime two ancestor if it has one.
        Branch<Long> closestRegimeTwoAncestor = lineageTree.find(parentId);
        boolean hasRegimeTwoAncestor = true;
        while(!getStimTypeFor(closestRegimeTwoAncestor).equals(STIM_TYPE_FOR_REGIME.get(Regime.TWO))) {
            Branch<Long> parent = lineageTree.findParentOf(closestRegimeTwoAncestor.getIdentifier());
            if (!(parent == null)) {
                closestRegimeTwoAncestor = parent;
            } else {
                hasRegimeTwoAncestor = false;
                break;
            }
        }

        // If stim has a regime two ancestor, consider that ancestor
        // and all the siblings of the closest ancestor that are stimType TWO
        if (hasRegimeTwoAncestor) {
            family.add(closestRegimeTwoAncestor.getIdentifier());

            // find all siblings of that parent tree
            List<Long> closestRegimeTwoUncles = lineageTree.findSiblingsOf(closestRegimeTwoAncestor.getIdentifier());

            System.err.println("Closest Regime Two Uncles: " + closestRegimeTwoUncles);
            for (Long uncle : closestRegimeTwoUncles) {
                if (dbUtil.readStimTypeFor(uncle).equals(STIM_TYPE_FOR_REGIME.get(Regime.TWO))) {
                    if (dbUtil.readGenIdForStimId(uncle) < dbUtil.readLatestGenIdForLineage(lineageId)) {
                        family.add(uncle);
                    }
                }
            }
        }

        // If Stim doesn't have any ancestors that are regime two (most likely a regime one or zero stimulus)
        // consider all of its siblings.
        else {
            System.err.println("No Regime Two Ancestor");
            System.err.println("Parent: " + parentId);
            Branch<Long> familyTree = lineageTree.find(parentId);
            Collection<Branch<Long>> immediateChildren = familyTree.getChildren();
            for (Branch<Long> child : immediateChildren) {
                if (dbUtil.readStimTypeFor(child.getIdentifier()).equals(STIM_TYPE_FOR_REGIME.get(Regime.TWO))) {
                    if (dbUtil.readGenIdForStimId(child.getIdentifier()) < dbUtil.readLatestGenIdForLineage(lineageId)) {
                        family.add(child.getIdentifier());
                    }
                }
            }

        }


        // If there are no immediate regime two descendents of the parent
        // consider all the descendants of the parent
        if (family.isEmpty()){
            Branch<Long> familyTree = lineageTree.find(parentId);
            familyTree.forEach(new Consumer<Branch<Long>>() {
                @Override
                public void accept(Branch<Long> branch) {
                    if (dbUtil.readStimTypeFor(branch.getIdentifier()).equals(STIM_TYPE_FOR_REGIME.get(Regime.TWO))) {
                        if (dbUtil.readGenIdForStimId(branch.getIdentifier()) < dbUtil.readLatestGenIdForLineage(lineageId)) {
                            family.add(branch.getIdentifier());
                        }
                    }
                }
            });
        }

        // If the whole descendent tree of the parent has no regime two descendents,
        // then we just consider all regime two descendents of the lineage
        if (family.isEmpty()) {
            System.err.println("No Regime Two Ancestors or Descendents");
            lineageTree.forEach(new Consumer<Branch<Long>>() {
                @Override
                public void accept(Branch<Long> branch) {
                    if (dbUtil.readStimTypeFor(branch.getIdentifier()).equals(STIM_TYPE_FOR_REGIME.get(Regime.TWO))) {
                        if (dbUtil.readGenIdForStimId(branch.getIdentifier()) < dbUtil.readLatestGenIdForLineage(lineageId)) {
                            family.add(branch.getIdentifier());
                        }
                    }
                }
            });
        }
        return family;
    }

    private String getStimTypeFor(Branch<Long> member) {
        return dbUtil.readStimTypeFor(member.getIdentifier());
    }

    private Map<Integer, Double> calculateAverageSpikeRateAcrossComponentsPreservedIn(List<Long> regimeTwoChildren) {
        // find responses of all regime two children and associate with preserved component
        Map<Integer, List<Double>> responsesForCompsPreserved = new HashMap<>();
        for (Long childId : regimeTwoChildren) {
            System.err.println("childId: " + childId);
            PruningMStickData childMStickData = PruningMStickData.fromXml(dbUtil.readStimSpecDataFor(childId));
            List<Integer> compsPreserved = childMStickData.getComponentsToPreserve();
            for (Integer compPreserved : compsPreserved) {
                if (!responsesForCompsPreserved.containsKey(compPreserved)) {
                    responsesForCompsPreserved.put(compPreserved, new LinkedList<>());
                }
                responsesForCompsPreserved.get(compPreserved).add(spikeRateSource.getSpikeRate(childId));
            }

        }

        // calculate average spike rate for each preserved component
        Map<Integer, Double> avgSpikeRateForCompsPreserved = new HashMap<>();
        for (Integer compPreserved : responsesForCompsPreserved.keySet()) {
            List<Double> responses = responsesForCompsPreserved.get(compPreserved);
            double avgSpikeRate = 0;
            for (Double response : responses) {
                avgSpikeRate += response;
            }
            avgSpikeRate /= responses.size();
            avgSpikeRateForCompsPreserved.put(compPreserved, avgSpikeRate);
        }
        return avgSpikeRateForCompsPreserved;
    }
}