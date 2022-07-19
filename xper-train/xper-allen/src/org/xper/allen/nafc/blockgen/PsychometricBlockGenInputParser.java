package org.xper.allen.nafc.blockgen;

import org.xper.allen.app.nafc.TrialGenerator;
import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricFactoryParameters;
import org.xper.allen.nafc.blockgen.rand.NumberOfDistractorsForRandTrial;
import org.xper.allen.nafc.blockgen.rand.NumberOfMorphCategories;
import org.xper.allen.nafc.blockgen.rand.RandFactoryParameters;
import org.xper.allen.nafc.vo.NoiseForm;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;

import java.util.Arrays;
import java.util.List;
import java.util.ListIterator;

public class PsychometricBlockGenInputParser extends TrialGenerator {

    private static final NoiseForm defaultPsychometricNoiseForm = new NoiseForm(NoiseType.PRE_JUNC, new double[]{0.5, 0.9});
    private static ListIterator<String> iterator;
    private final PsychometricBlockGen generator;
    private int numPsychometricTrialsPerImage;
    private int numRandTrials;
    private TypeFrequency<Integer> numPsychometricDistractors;
    private TypeFrequency<Integer> numRandDisractors;
    private TypeFrequency<Lims> psychometricNoiseChances;
    private TypeFrequency<Integer> numQMDistractors;
    private TypeFrequency<Integer> numRandDistractors;
    private TypeFrequency<Integer> numMMCategories;
    private TypeFrequency<Integer> numQMCategories;
    private TypeFrequency<Lims> randNoiseChances;
    private TypeFrequency<NoiseType> noiseTypes;
    private Lims sampleDistanceLims;
    private Lims choiceDistanceLims;
    private double size;
    private double eyeWinSize;
    private NAFCTrialParameters nafcTrialParameters;

    public PsychometricBlockGenInputParser(PsychometricBlockGen generator) {
        this.generator = generator;
    }

    private void readArgs(String[] args) {
        List<String> argsList = Arrays.asList(args);
        iterator = argsList.listIterator();

        //BLOCK
        numPsychometricTrialsPerImage = Integer.parseInt(iterator.next());
        numRandTrials = Integer.parseInt(iterator.next());

        //PSYCHOMETRIC TRIALS
        numPsychometricDistractors = new TypeFrequency<>(nextIntegerType(), nextFrequency());
        numRandDisractors = new TypeFrequency<>(nextIntegerType(), nextFrequency());
        psychometricNoiseChances = new TypeFrequency<>(nextLimsType(), nextFrequency());


        //RAND TRIALS
        numQMDistractors = new TypeFrequency<>(nextIntegerType(), nextFrequency());
        numRandDistractors = new TypeFrequency<>(nextIntegerType(), nextFrequency());
        numMMCategories = new TypeFrequency<>(nextIntegerType(), nextFrequency());
        numQMCategories = new TypeFrequency<>(nextIntegerType(), nextFrequency());
        randNoiseChances = new TypeFrequency<>(nextLimsType(), nextFrequency());
        noiseTypes = new TypeFrequency<>(stringToNoiseTypes(iterator.next()), nextFrequency());


        //ALL TRIALS
        sampleDistanceLims = stringToLim(iterator.next());
        choiceDistanceLims = stringToLim(iterator.next());
        size = Double.parseDouble(iterator.next());
        eyeWinSize = Double.parseDouble(iterator.next());
    }

    public void parse(String[] args){

        readArgs(args);

        nafcTrialParameters = new NAFCTrialParameters(
                sampleDistanceLims,
                choiceDistanceLims,
                size,
                eyeWinSize
        );

        PsychometricFactoryParameters psychometricFactorParameters = createPsychometricFactoryParameters();

        TypeFrequency<NumberOfDistractorsForRandTrial> numDistractors
                = getNumDistractorsMixedTypeFrequency(numQMDistractors, numRandDistractors);
        TypeFrequency<NumberOfMorphCategories> numMorphs
                = getNumMorphMixedTypeFrequency(numMMCategories, numQMCategories);

        TypeFrequency<NoiseParameters> noiseParameters = new TypeFrequency<>();
        TypeFrequency<Lims> randNoiseChances1 = this.randNoiseChances;
        noiseParameters.add();

        TypeFrequency<NoisyTrialParameters> trialParameters
                = getNumNoisyTrialParametersTypeFrequency(noiseParameters, nafcTrialParameters);

        RandFactoryParameters randFactoryParameters =
                new RandFactoryParameters(
                        numRandTrials,
                        numDistractors,
                        numMorphs,
                        trialParametersTypeFrequency
                );


        generator.setUp(
                psychometricFactorParameters,
                randFactoryParameters);
    }

    private PsychometricFactoryParameters createPsychometricFactoryParameters() {
        TypeFrequency<NoisyTrialParameters> trialParameters = new TypeFrequency<>();
        for(Lims noiseChance: randNoiseChances.getTypes()){
            NoiseParameters noiseParameters = new NoiseParameters(defaultPsychometricNoiseForm, noiseChance);
            trialParameters.getTypes().add(new NoisyTrialParameters(noiseParameters, nafcTrialParameters));
        }
        trialParameters.setFrequencies(randNoiseChances.getFrequencies());


        PsychometricFactoryParameters psychometricFactorParameters =
                new PsychometricFactoryParameters(
                        numPsychometricTrialsPerImage,
                        numPsychometricDistractors,
                        numRandDisractors,
                        trialParameters
                );
        return psychometricFactorParameters;
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

    private static TypeFrequency<NumberOfDistractorsForRandTrial> getNumDistractorsMixedTypeFrequency(TypeFrequency<Integer> numQMDistractorsTF, TypeFrequency<Integer> numRandDistractorsTF){
        TypeFrequency<NumberOfDistractorsForRandTrial> output = new TypeFrequency<>();
        for(Integer numQMDistractorsType:numQMDistractorsTF.getTypes()){
            for(Integer numRandDistractorsType :numRandDistractorsTF.getTypes()){
                NumberOfDistractorsForRandTrial compositeType = new NumberOfDistractorsForRandTrial(numQMDistractorsType, numRandDistractorsType);
                output.getTypes().add(compositeType);
            }
        }

        for(Double numQMDistractorsFrequency:numQMDistractorsTF.getFrequencies()){
            for(Double numRandDistractorsFrequency :numRandDistractorsTF.getFrequencies()){
                Double compositeFrequency = numQMDistractorsFrequency * numRandDistractorsFrequency;
                output.getFrequencies().add(compositeFrequency);
            }
        }

        return output;
    }

    private static TypeFrequency<NumberOfMorphCategories> getNumMorphMixedTypeFrequency(TypeFrequency<Integer> numMMCategoriesTF, TypeFrequency<Integer> numQMCategoriesTF){
        TypeFrequency<NumberOfMorphCategories> output = new TypeFrequency<>();
        for(Integer numMMCategoriesType:numMMCategoriesTF.getTypes()){
            for(Integer numQMCategoriesType :numQMCategoriesTF.getTypes()){
                NumberOfMorphCategories compositeType = new NumberOfMorphCategories(numMMCategoriesType, numQMCategoriesType);
                output.getTypes().add(compositeType);
            }
        }

        for(Double numMMDistractorsFrequency:numMMCategoriesTF.getFrequencies()){
            for(Double numQMCategoriesFrequency :numQMCategoriesTF.getFrequencies()){
                Double compositeFrequency = numMMDistractorsFrequency * numQMCategoriesFrequency;
                output.getFrequencies().add(compositeFrequency);
            }
        }

        return output;
    }

    private static TypeFrequency<NoisyTrialParameters> getNumNoisyTrialParametersTypeFrequency(TypeFrequency<NoiseParameters> noiseParameters, TypeFrequency<NAFCTrialParameters> nafcTrialParameters){
        TypeFrequency<NoisyTrialParameters> output = new TypeFrequency<>();
        for(NoiseParameters noiseParametersType:noiseParameters.getTypes()){
            for(NAFCTrialParameters nafcTrialParametersType :nafcTrialParameters.getTypes()){
                NoisyTrialParameters compositeType = new NoisyTrialParameters(noiseParametersType, nafcTrialParametersType);
                output.getTypes().add(compositeType);
            }
        }

        for(Double noiseParametersFrequency:noiseParameters.getFrequencies()){
            for(Double nafcTrialParametersFrequency :nafcTrialParameters.getFrequencies()){
                Double compositeFrequency = noiseParametersFrequency * nafcTrialParametersFrequency;
                output.getFrequencies().add(compositeFrequency);
            }
        }

        return output;
    }


}
