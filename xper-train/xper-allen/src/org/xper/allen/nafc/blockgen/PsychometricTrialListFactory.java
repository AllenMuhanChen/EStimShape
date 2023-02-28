package org.xper.allen.nafc.blockgen;

import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.psychometric.*;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class PsychometricTrialListFactory implements TrialListFactory {

    private final List<NumberOfDistractorsForPsychometricTrial> numDistractors;
    private final int numTrialsPerImage;
    private final List<NoisyTrialParameters> trialParameters;
    AbstractPsychometricTrialGenerator generator;
    PsychometricFactoryParameters parameters;

    public PsychometricTrialListFactory(AbstractPsychometricTrialGenerator generator, PsychometricFactoryParameters parameters) {
        this.generator = generator;
        this.parameters = parameters;
        numDistractors = parameters.getNumDistractors();

        numTrialsPerImage = parameters.getNumTrialsPerImage();
        trialParameters = parameters.getTrialParameters();
    }

    private List<Long> setIds;
    private List<Integer> stimIds;


    @Override
    public List<Stim> createTrials() {
        List<NumberOfDistractorsForPsychometricTrial> numDistractors = this.numDistractors;

        fetchSetInfo();

        List<Stim> stims = new LinkedList<>();
        for(long setId:setIds)
            for(int stimId:stimIds)
                for(int i=0; i<numTrialsPerImage; i++){
                    PsychometricTrialParameters psychometricTrialParameters = new PsychometricTrialParameters(
                            trialParameters.get(i),
                            numDistractors.get(i),
                            new PsychometricIds(setId, stimId, stimIds)
                    );
                    stims.add(new PsychometricStim(
                            generator,
                            psychometricTrialParameters));
                }
        return stims;
    }

    int numSets;
    int numStimPerSet;

    private void fetchSetInfo(){
        //Getting all files in path
        File folder = new File(generator.getGeneratorPsychometricPngPath());
        File[] fileArray = folder.listFiles();
        List<File> pngs = new ArrayList<>();
        List<String> generatorPngs = new ArrayList<>();

        //Making sure all the files are png
        for(File file:fileArray) {
            if(file.toString().contains(".png")) {
                pngs.add(file);
            }
        }

        //Load filenames
        List<String> filenames = new ArrayList<String>();
        for (File png:pngs) {
            filenames.add(png.getName());
        }
        //For each png, finds the set number and stim number
        setIds = new ArrayList<Long>();
        stimIds = new ArrayList<Integer>();
        for(String filename: filenames) {
            Pattern p = Pattern.compile("([0-9]{16})_(\\d)");
            Matcher m = p.matcher(filename);

            if(m.find()) {
                setIds.add(Long.parseLong(m.group(1)));
                stimIds.add(Integer.parseInt(m.group(2)));
            } else {
                throw new IllegalStateException("Can't find any pngs with name pattern regex ([0-9]{16})_(\\d)");
            }
        }

        //Removing non-distinct setIds and stimNums
        removeNonDistinct(setIds);
        removeNonDistinct(stimIds);

        numSets = setIds.size();
        numStimPerSet = stimIds.size();

    }

    private static void removeNonDistinct(List<? extends Comparable<?>> list)
    {
        int n = list.size();
        // First sort the array so that all
        // occurrences become consecutive
        list.sort(null);

        List<Integer> removeList = new ArrayList<Integer>();
        // Traverse the sorted array
        for (int i = 0; i < n; i++)
        {

            // Move the index ahead while
            // there are duplicates
            while (i < n - 1 &&
                    list.get(i).equals(list.get(i+1)))
            {
                removeList.add(i+1);
                i++;
            }

        }

        //Remove in reverse order to avoid indcs to remove changing every removal.
        //We can't copy a generic List easily so we have to do it this way.
        Collections.reverse(removeList);
        for(int removeIndx : removeList) {
            list.remove(removeIndx);
        }
    }
}
