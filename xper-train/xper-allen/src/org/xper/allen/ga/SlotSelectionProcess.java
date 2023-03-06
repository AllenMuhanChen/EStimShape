package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class SlotSelectionProcess {

    private String string;

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    Integer numChildrenToSelect;

    @Dependency
    RegimeScoreSource regimeScoreSource;

    public List<Child> select(String gaName) {
        string = gaName;
        // Get all lineages for gaName
        List<Long> lineageIds = fetchLineageIds(gaName);

        // Calculate Regime Scores For All Lineages
        Map<Long, Double> regimeScoreForLineages = new LinkedHashMap<>();
        for (Long lineageId : lineageIds){
            regimeScoreForLineages.put(lineageId, regimeScoreSource.getRegimeScore(lineageId));
        }

        // Use Regime Scores to Assign slots among lineages

        // Use Regime Scores to Assign slots among regimes

        // For Each slot, use the lineage to choose parents, and use the regime to assign fitness score


        return null;
    }

    private List<Long> fetchLineageIds(String gaName) {
        List<String> treeSpecs = dbUtil.readAllTreeSpecsForGa(gaName);
        List<Long> lineageIds = treeSpecsToLineageIds(treeSpecs);
        return lineageIds;
    }

    private List<Long> treeSpecsToLineageIds(List<String> treeSpecs) {
        List<Long> founderIds = new LinkedList<>();
        for (String treeSpec : treeSpecs) {
            Branch<Long> tree = Branch.fromXml(treeSpec);
            founderIds.add(tree.getIdentifier());
        }
        return founderIds;
    }

}