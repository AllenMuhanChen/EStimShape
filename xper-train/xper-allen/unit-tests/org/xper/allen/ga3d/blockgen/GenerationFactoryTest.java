package org.xper.allen.ga3d.blockgen;

import org.junit.Test;
import org.xper.allen.Trial;
import java.util.List;

import static org.junit.Assert.assertTrue;

public class GenerationFactoryTest {

    @Test
    public void createsFirstGeneration() {
        GenerationFactory factory = new GenerationFactory(40);
        List<Trial> trials = factory.createFirstGenerationTrials();
        assertTrue(trials.stream().count()==40);
        for (Trial trial: trials){
            assertTrue(trial instanceof RandTrial);
        }
    }

    @Test
    public void addsNthGeneration() {
    }
}