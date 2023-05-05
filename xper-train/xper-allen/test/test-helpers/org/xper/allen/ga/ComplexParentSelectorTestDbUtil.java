package org.xper.allen.ga;

import org.xper.allen.util.MultiGaDbUtil;

import java.util.ArrayList;
import java.util.List;

public class ComplexParentSelectorTestDbUtil extends MultiGaDbUtil {

    @Override
    public List<Long> readAllStimIdsForGa(String gaName) {
        List<Long> allStimIds = new ArrayList<Long>();

        //generate 10 random 5 digit stimIds
        for (int i = 0; i < 10; i++) {
            long stimId = (long) (Math.random() * 100000);
            allStimIds.add(stimId);
        }

        return allStimIds;

    }
}