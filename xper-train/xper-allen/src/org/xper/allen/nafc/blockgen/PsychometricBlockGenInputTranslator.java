package org.xper.allen.nafc.blockgen;

import org.xper.allen.app.nafc.TrialGenerator;
import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGenSetUpParameters;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricFactoryParameters;
import org.xper.allen.nafc.blockgen.rand.NumberOfDistractorsForRandTrial;
import org.xper.allen.nafc.blockgen.rand.NumberOfMorphCategories;
import org.xper.allen.nafc.blockgen.rand.RandFactoryParameters;
import org.xper.allen.nafc.vo.NoiseForm;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;

import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;
import java.util.ListIterator;

public class PsychometricBlockGenInputTranslator extends TrialGenerator {

    private static final NoiseForm defaultPsychometricNoiseForm = NoiseFormer.getNoiseForm(NoiseType.PRE_JUNC);
    private static ListIterator<String> iterator;
    private final PsychometricBlockGen generator;
    private int numPsychometricTrialsPerImage;
    private int numRandTrials;
    private TypeFrequency<Integer> numPsychometricDistractorsTF;
    private TypeFrequency<Integer> numPsychometricRandDisractorsTF;
    private TypeFrequency<Lims> psychometricNoiseChances;
    private TypeFrequency<Integer> numQMDistractorsTF;
    private TypeFrequency<Integer> numRandDistractorsTF;
    private TypeFrequency<Integer> numMMCategoriesTF;
    private TypeFrequency<Integer> numQMCategoriesTF;
    private TypeFrequency<Lims> randNoiseChancesTF;
    private TypeFrequency<NoiseType> noiseTypesTF;
    private Lims sampleDistanceLims;
    private Lims choiceDistanceLims;
    private double size;
    private double eyeWinSize;
    private NAFCTrialParameters nafcTrialParameters;

    public PsychometricBlockGenInputTranslator(PsychometricBlockGen generator) {
        this.generator = generator;
    }

    private void readArgs(String[] args) {
        List<String> argsList = Arrays.asList(args);
        iterator = argsList.listIterator();

        //BLOCK
        numPsychometricTrialsPerImage = Integer.parseInt(iterator.next());
        numRandTrials = Integer.parseInt(iterator.next());

        //PSYCHOMETRIC TRIALS
        numPsychometricDistractorsTF = new TypeFrequency<>(nextIntegerType(), nextFrequency());
        numPsychometricRandDisractorsTF = new TypeFrequency<>(nextIntegerType(), nextFrequency());
        psychometricNoiseChances = new TypeFrequency<>(nextLimsType(), nextFrequency());


        //RAND TRIALS
        numQMDistractorsTF = new TypeFrequency<>(nextIntegerType(), nextFrequency());
        numRandDistractorsTF = new TypeFrequency<>(nextIntegerType(), nextFrequency());
        numMMCategoriesTF = new TypeFrequency<>(nextIntegerType(), nextFrequency());
        numQMCategoriesTF = new TypeFrequency<>(nextIntegerType(), nextFrequency());
        randNoiseChancesTF = new TypeFrequency<>(nextLimsType(), nextFrequency());
        noiseTypesTF = new TypeFrequency<>(stringToNoiseTypes(iterator.next()), nextFrequency());


        //ALL TRIALS
        sampleDistanceLims = stringToLim(iterator.next());
        choiceDistanceLims = stringToLim(iterator.next());
        size = Double.parseDouble(iterator.next());
        eyeWinSize = Double.parseDouble(iterator.next());
    }

    public PsychometricBlockGenSetUpParameters translate(String[] args){

        readArgs(args);
        createSharedParameters();
        PsychometricFactoryParameters psychometricFactorParameters
                = createPsychometricFactoryParameters();
        RandFactoryParameters randFactoryParameters
                = createRandFactoryParameters();

        return new PsychometricBlockGenSetUpParameters(psychometricFactorParameters, randFactoryParameters);
    }

    private void createSharedParameters() {
        nafcTrialParameters = new NAFCTrialParameters(
                sampleDistanceLims,
                choiceDistanceLims,
                size,
                eyeWinSize
        );
    }

    private PsychometricFactoryParameters createPsychometricFactoryParameters() {
        //TRIAL PARAMETERS
        List<Lims> psychometricNoiseChances = this.psychometricNoiseChances.getShuffledTrialList(numPsychometricTrialsPerImage);
        List<NoisyTrialParameters> trialParameters = new LinkedList<>();
        for(Lims noiseChance: psychometricNoiseChances){
            NoiseParameters noiseParameters = new NoiseParameters(defaultPsychometricNoiseForm, noiseChance);
            trialParameters.add(new NoisyTrialParameters(noiseParameters, nafcTrialParameters));
        }

        //DISTRACTORS
        List<Integer> numRandDistractors = numPsychometricRandDisractorsTF.getShuffledTrialList(numPsychometricTrialsPerImage);
        List<Integer> numPsychometricDistractors = numPsychometricDistractorsTF.getShuffledTrialList(numPsychometricTrialsPerImage);
        List<NumberOfDistractorsForPsychometricTrial> numDistractors = new LinkedList<>();
        for(int i=0; i<numPsychometricTrialsPerImage; i++){
            numDistractors.add(new NumberOfDistractorsForPsychometricTrial(numPsychometricDistractors.get(i),numRandDistractors.get(i)));
        }

        PsychometricFactoryParameters psychometricFactorParameters =
                PsychometricFactoryParameters.create(
                        numPsychometricTrialsPerImage, trialParameters, numDistractors);
        return psychometricFactorParameters;
    }

    private RandFactoryParameters createRandFactoryParameters(){
        //NUM DISTRACTORS
        List<Integer> numQMDistractors = numQMDistractorsTF.getShuffledTrialList(numRandTrials);
        List<Integer> numRandDistractors = numRandDistractorsTF.getShuffledTrialList(numRandTrials);
        List<NumberOfDistractorsForRandTrial> numDistractors = new LinkedList<>();
        for (int i=0; i<numRandTrials; i++){
            numDistractors.add(new NumberOfDistractorsForRandTrial(numQMDistractors.get(i),numRandDistractors.get(i)));
        }

        //NUM MORPHS
        List<Integer> numMMCategories = numMMCategoriesTF.getShuffledTrialList(numRandTrials);
        List<Integer> numQMCategories = numQMCategoriesTF.getShuffledTrialList(numRandTrials);
        List<NumberOfMorphCategories> numMorphs = new LinkedList<>();
        for(int i=0; i<numRandTrials; i++){
            numMorphs.add(new NumberOfMorphCategories(numMMCategories.get(i), numQMCategories.get(i)));
        }

        //TRIAL PARAMETERS
        List<Lims> noiseChances = randNoiseChancesTF.getShuffledTrialList(numRandTrials);
        List<NoiseType> noiseTypes = noiseTypesTF.getShuffledTrialList(numRandTrials);
        List<NoiseParameters> noiseParameters = new LinkedList<>();
        for(int i=0; i<numRandTrials; i++){
            noiseParameters.add(
                    new NoiseParameters(NoiseFormer.getNoiseForm(noiseTypes.get(i)),
                            noiseChances.get(i)));
        }
        List<NoisyTrialParameters> trialParameters = new LinkedList<>();
        for(int i=0; i<numRandTrials; i++){
            trialParameters.add(new NoisyTrialParameters(noiseParameters.get(i), nafcTrialParameters));
        }

        RandFactoryParameters randFactoryParameters =
                new RandFactoryParameters(
                        numRandTrials,
                        numDistractors,
                        numMorphs,
                        trialParameters
                );

        return randFactoryParameters;

    }

    private static List<Double> nextFrequency() {
        return stringToDoubles(iterator.next());
    }

    private static List<Integer> nextIntegerType() {
        return stringToIntegers(iterator.next());
    }

    private static List<Lims> nextLimsType(){
        return stringToLims(iterator.next());
    }


}