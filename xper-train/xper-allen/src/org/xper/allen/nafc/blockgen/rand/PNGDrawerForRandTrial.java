package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.drawing.composition.AllenMStickSpec;
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

    Rand<String> pngPaths = new Rand<>();

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
        List<String> randDistractorLabels = Arrays.asList(new String[]{"Rand Distractor"});
        index=0;
        for(AllenMatchStick mStick:mSticks.getRandDistractors()){
            String randDistractorPath = pngMaker.createAndSavePNG(mStick, stimObjIds.getRandDistractors().get(index), randDistractorLabels, generatorPngPath);
            pngPaths.addRandDistractor(randDistractorPath);
            index++;
        }
    }

    private void drawQMDistractorPNGs(AllenPNGMaker pngMaker, String generatorPngPath) {
        List<String> qmDistractorLabels = Arrays.asList(new String[]{"QM Distractor"});
        int index=0;
        for(AllenMatchStick mStick:mSticks.getQualitativeMorphDistractors()){
            String qmDistractorPath = pngMaker.createAndSavePNG(mStick, stimObjIds.getQualitativeMorphDistractors().get(index), qmDistractorLabels, generatorPngPath);
            pngPaths.addQualitativeMorphDistractor(qmDistractorPath);
            index++;
        }
    }

    private void drawMatchPNG(AllenPNGMaker pngMaker, String generatorPngPath) {
        List<String> matchLabels =  Arrays.asList(new String[] {"Match"});
        String matchPath = pngMaker.createAndSavePNG(mSticks.getMatch(),stimObjIds.getMatch(), matchLabels, generatorPngPath);
        pngPaths.setMatch(matchPath);
    }

    private void drawSamplePNG(AllenPNGMaker pngMaker, String generatorPngPath) {
        List<String> sampleLabels = Arrays.asList(new String[] {"Sample"});
        String samplePath = pngMaker.createAndSavePNG(mSticks.getSample(),stimObjIds.getSample(), sampleLabels, generatorPngPath);
        pngPaths.setSample(samplePath);
    }

    public Rand<String> getPngPaths() {
        return pngPaths;
    }


}
