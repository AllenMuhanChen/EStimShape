package org.xper.allen.app.nafc;

import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.allen.util.AllenDbUtil;
import org.xper.db.vo.TaskToDoEntry;
import org.xper.util.FileUtil;

import java.io.File;
import java.util.Map;

import static org.junit.Assert.assertEquals;

public class PsychometricBlockGeneratorMainIntegrationTest {

    String half = "0.5,0.5";

    //BLOCK


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


    private PsychometricBlockGen generator;
    private AllenDbUtil dbUtil;
    private Long startTime;
    private Long endTime;
    private String numRandTrials;
    private String numPsychometricTrialsPerImage;


    @Test
    public void generates_classic_use_case_trials(){
        startTime = System.currentTimeMillis()*1000;
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));

        generator = context.getBean(PsychometricBlockGen.class);


        //ACT
        PsychometricBlockGeneratorMain.main(classicArgs());

        //ASSERTs
        //Test Number of Trials in Database
        endTime = System.currentTimeMillis()*1000;
        dbUtil = generator.getDbUtil();
        generates_correct_total_amount_of_trials();
        generates_correct_distribution_of_trials();
    }

    @Test
    public void generates_rand_only_use_case_trials(){
        startTime = System.currentTimeMillis()*1000;
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));

        generator = context.getBean(PsychometricBlockGen.class);


        //ACT
        PsychometricBlockGeneratorMain.main(randOnlyArgs());

        //ASSERTs
        //Test Number of Trials in Database
        endTime = System.currentTimeMillis()*1000;
        dbUtil = generator.getDbUtil();
        generates_correct_total_amount_of_trials();
        generates_correct_distribution_of_trials();
    }

    private String[] classicArgs(){
        this.numRandTrials = "2";
        this.numPsychometricTrialsPerImage = "2";
        return getArgs();
    }

    private String[] randOnlyArgs(){
        this.numRandTrials = "2";
        this.numPsychometricTrialsPerImage = "0";
        return getArgs();
    }

    private void generates_correct_total_amount_of_trials() {
        Map<Long, TaskToDoEntry> tasksToDo = dbUtil.readTaskToDoByIdRangeAsMap(startTime, endTime);
        assertEquals(tasksToDo.size(), expectedNumTrials());
    }


    private void generates_correct_distribution_of_trials() {
        Map<Long, String> stimSpecData = dbUtil.readStimSpecDataByIdRangeAsMap(startTime, endTime);

        int actualNumPsychometricTrials = 0;
        int actualNumRandTrials = 0;
        for(String spec: stimSpecData.values()){
            if (spec.contains("PsychometricTrialParameters")){
                actualNumPsychometricTrials++;
            } else if(spec.contains("RandNoisyTrialParameters")){
                actualNumRandTrials++;
            } else{

            }
        }
        assertEquals(expectedNumPsychometricTrials(), actualNumPsychometricTrials);
        assertEquals(expectedNumRandTrials(), actualNumRandTrials);
    }


    private int expectedNumTrials(){
        return expectedNumRandTrials() + expectedNumPsychometricTrials();
    }

    private int expectedNumRandTrials() {
        return Integer.parseInt(numRandTrials);
    }

    private int expectedNumPsychometricTrials(){
        File psychometricFolder = new File(generator.getGeneratorPsychometricPngPath());
        int numImages = psychometricFolder.list().length;
        return Integer.parseInt(numPsychometricTrialsPerImage)*numImages;
    }

    private String[] getArgs(){
        String[] args = new String[]{
                //BLOCK
                numPsychometricTrialsPerImage,
                numRandTrials,
                //PSYCHOMETRIC
                numPsychometricDistractors, numPsychometricDistractorsFreqs,
                numPsychometricRandDistractors, numRandDistractorsFreqs,
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

        return args;
    }
}