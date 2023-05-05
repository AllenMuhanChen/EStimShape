package org.xper.allen.nafc.blockgen.rand;

import org.junit.Test;
import org.xper.time.TestTimeUtil;

import static junit.framework.Assert.assertTrue;

public class StimObjIdAssignerForRandTrialsTest {

    @Test
    public void given_classic_case() {
        //Arrange
        TestTimeUtil globalTimeUtil = new TestTimeUtil();
        int numQMDistractors = 1;
        int numRandDistractors = 1;
        NumberOfDistractorsForRandTrial numDistractors = new NumberOfDistractorsForRandTrial(numQMDistractors, numRandDistractors);

        then_stim_obj_ids_are_in_correct_order(globalTimeUtil, numDistractors);
    }

    @Test
    public void given_no_qm_case() {
        //Arrange
        TestTimeUtil globalTimeUtil = new TestTimeUtil();
        int numQMDistractors = 0;
        int numRandDistractors = 1;
        NumberOfDistractorsForRandTrial numDistractors = new NumberOfDistractorsForRandTrial(numQMDistractors, numRandDistractors);

        then_stim_obj_ids_are_in_correct_order(globalTimeUtil, numDistractors);
    }

    @Test
    public void given_no_rand_case() {
        //Arrange
        TestTimeUtil globalTimeUtil = new TestTimeUtil();
        int numQMDistractors = 1;
        int numRandDistractors = 0;
        NumberOfDistractorsForRandTrial numDistractors = new NumberOfDistractorsForRandTrial(numQMDistractors, numRandDistractors);

        then_stim_obj_ids_are_in_correct_order(globalTimeUtil, numDistractors);
    }

    @Test
    public void given_many_distractors_case() {
        //Arrange
        TestTimeUtil globalTimeUtil = new TestTimeUtil();
        int numQMDistractors = 5;
        int numRandDistractors = 5;
        NumberOfDistractorsForRandTrial numDistractors = new NumberOfDistractorsForRandTrial(numQMDistractors, numRandDistractors);

        then_stim_obj_ids_are_in_correct_order(globalTimeUtil, numDistractors);
    }

    private void then_stim_obj_ids_are_in_correct_order(TestTimeUtil globalTimeUtil, NumberOfDistractorsForRandTrial numDistractors) {
        //Act
        Rand<Long> stimObjIds = getStimObjIds(globalTimeUtil, numDistractors);

        //Assert
        assertTrue(stimObjIds.getSample() < stimObjIds.getMatch());
        assertTrue(stimObjIds.getMatch() < stimObjIds.getAllDistractors().get(0));

        for (int i = 0; i < stimObjIds.getAllDistractors().size() - 1; i++) {
            Long firstId = stimObjIds.getAllDistractors().get(i);
            Long nextId = stimObjIds.getAllDistractors().get(i + 1);
            assertTrue(firstId + " was not < " + nextId, firstId < nextId);
        }
    }


    private Rand<Long> getStimObjIds(TestTimeUtil globalTimeUtil, NumberOfDistractorsForRandTrial numDistractors) {
        //Assign
        StimObjIdAssignerForRandTrials stimObjIdAssigner = new StimObjIdAssignerForRandTrials(globalTimeUtil, numDistractors);

        //Act
        Rand<Long> stimObjIds = stimObjIdAssigner.getStimObjIds();
        return stimObjIds;
    }
}
