package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;

import java.util.Arrays;
import java.util.List;

public class PNGDrawerForRandTrial {
    private AbstractMStickPngTrialGenerator generator;
    private Rand<AllenMatchStick> mSticks;

    Rand<Long> stimObjIds;

    public PNGDrawerForRandTrial(AbstractMStickPngTrialGenerator generator, Rand<AllenMatchStick> mSticks, Rand<Long> stimObjIds) {
        this.generator = generator;
        this.mSticks = mSticks;
        this.stimObjIds = stimObjIds;
        drawPNGs();
    }

    Rand<String> experimentPngPaths = new Rand<>();

    private void drawPNGs(){
        AllenPNGMaker pngMaker = generator.getPngMaker();
        String generatorPngPath = generator.getGeneratorPngPath();

        pngMaker.createDrawerWindow();
        drawSamplePNG(pngMaker, generatorPngPath);
        drawMatchPNG(pngMaker, generatorPngPath);
        drawQMDistractorPNGs(pngMaker, generatorPngPath);
        drawRandDistractorPNGs(pngMaker, generatorPngPath);
        pngMaker.close();
    }
    private void drawRandDistractorPNGs(AllenPNGMaker pngMaker, String generatorPngPath) {
        int index;
        List<String> randDistractorLabels = Arrays.asList(new String[]{"randDistractor"});
        index=0;
        for(AllenMatchStick mStick:mSticks.getRandDistractors()){
            String randDistractorPath = pngMaker.createAndSavePNG(mStick, stimObjIds.getRandDistractors().get(index), randDistractorLabels, generatorPngPath);
            experimentPngPaths.addRandDistractor(generator.convertPathToExperiment(randDistractorPath));
            index++;
        }
    }

    private void drawQMDistractorPNGs(AllenPNGMaker pngMaker, String generatorPngPath) {
        List<String> qmDistractorLabels = Arrays.asList(new String[]{"qmDistractor"});
        int index=0;
        for(AllenMatchStick mStick:mSticks.getQualitativeMorphDistractors()){
            String qmDistractorPath = pngMaker.createAndSavePNG(mStick, stimObjIds.getQualitativeMorphDistractors().get(index), qmDistractorLabels, generatorPngPath);
            experimentPngPaths.addQualitativeMorphDistractor(generator.convertPathToExperiment(qmDistractorPath));
            index++;
        }
    }

    private void drawMatchPNG(AllenPNGMaker pngMaker, String generatorPngPath) {
        List<String> matchLabels =  Arrays.asList(new String[] {"match"});
        String matchPath = pngMaker.createAndSavePNG(mSticks.getMatch(),stimObjIds.getMatch(), matchLabels, generatorPngPath);
        experimentPngPaths.setMatch(generator.convertPathToExperiment(matchPath));
    }

    private void drawSamplePNG(AllenPNGMaker pngMaker, String generatorPngPath) {
        List<String> sampleLabels = Arrays.asList(new String[] {"sample"});
        String samplePath = pngMaker.createAndSavePNG(mSticks.getSample(),stimObjIds.getSample(), sampleLabels, generatorPngPath);
        experimentPngPaths.setSample(generator.convertPathToExperiment(samplePath));
    }

    public Rand<String> getExperimentPngPaths() {
        return experimentPngPaths;
    }


}
