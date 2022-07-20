package org.xper.allen.app.nafc;

import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.app.nafc.PsychometricBlockGeneratorMain;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.allen.util.AllenDbUtil;
import org.xper.db.vo.TaskToDoEntry;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TestTimeUtil;
import org.xper.util.FileUtil;

import java.io.File;
import java.util.Map;

import static org.junit.Assert.assertEquals;

public class PsychometricBlockGeneratorMainIntegrationTest {

    String half = "0.5,0.5";

    //BLOCK
    String numPsychometricTrialsPerImage = "2";
    String numRandTrials = "10";

    //PSYCHOMETRIC
    String numPsychometricDistractors = "1,2"; String numPsychometricDistractorsFreqs = half;
    String numPsychometricRandDistractors = "1,2"; String numRandDistractorsFreqs = half;
    String psychometricNoiseChances = "(0.5,0.1),(0.8,0.1)"; String psychometricNoiseChancesFreqs = half;

    //RAND
    String numQMDistractors = "1,2"; String numQMDistractorsFreqs = half;
    String numRandDistractors = "1,2"; String numRandTrialsFreqs = half;
    String numMMCategories = "1,2"; String numMMCategoriesFreqs = half;
    String numQMCategories = "1,2"; String numQMCategoriesFreqs = half;
    String randNoiseChances = psychometricNoiseChances; String randNoiseChancesFreqs = half;
    String noiseTypes = "NONE,PRE_JUNC"; String noiseTypesFreqs = half;


    //ALL TRIALS
    String sampleDistanceLims = "0,1";
    String choiceDistanceLims = "8,10";
    String size = "8";
    String eyeWinSize = "10";

    String[] args = new String[]{
            //BLOCK
            numPsychometricTrialsPerImage,
            numRandTrials,
            //PSYCHOMETRIC
            numPsychometricDistractors, numPsychometricDistractorsFreqs,
            numPsychometricRandDistractors, numPsychometricDistractorsFreqs,
            psychometricNoiseChances, psychometricNoiseChancesFreqs,
            //RAND
            numQMDistractors, numQMDistractorsFreqs,
            numRandDistractors, numRandDistractorsFreqs,
            numMMCategories, numMMCategoriesFreqs,
            numQMCategories, numQMCategoriesFreqs,
            randNoiseChances, randNoiseChancesFreqs,
            noiseTypes, noiseTypesFreqs,
            //ALL TRIALS
            sampleDistanceLims,
            choiceDistanceLims,
            size,
            eyeWinSize
    };
    private PsychometricBlockGen generator;

    @Test
    public void test(){
        Long startTime = System.currentTimeMillis()*1000;
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));

        generator = context.getBean(PsychometricBlockGen.class);

        //ACT
        PsychometricBlockGeneratorMain.main(args);

        //ASSERT
        //Test Number of Trials in Database
        Long endTime = System.currentTimeMillis()*1000;
        AllenDbUtil dbUtil = generator.getDbUtil();
        Map<Long, TaskToDoEntry> tasksToDo = dbUtil.readTaskToDoByIdRangeAsMap(startTime, endTime);
        assertEquals(tasksToDo.size(), expectedNumTrials());

    }

    private int expectedNumTrials(){
        File psychometricFolder = new File(generator.getGeneratorPsychometricPngPath());
        int numImages = psychometricFolder.list().length;
        return Integer.parseInt(numRandTrials) +Integer.parseInt(numPsychometricTrialsPerImage)*numImages;
    }
}