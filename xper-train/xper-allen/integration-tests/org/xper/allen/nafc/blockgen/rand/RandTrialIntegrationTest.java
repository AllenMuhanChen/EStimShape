package org.xper.allen.nafc.blockgen.rand;


import java.io.File;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;


import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.RandTrialNoiseMapGenerator;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricTrialGenerator;
import org.xper.allen.nafc.blockgen.psychometric.PsychometricBlockGen;
import org.xper.time.TestTimeUtil;
import org.xper.allen.nafc.vo.NoiseForm;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.allen.specs.NAFCStimSpecSpec;
import org.xper.allen.specs.NoisyPngSpec;
import org.xper.db.vo.StimSpecEntry;
import org.xper.drawing.Coordinates2D;
import org.xper.util.FileUtil;

import javax.vecmath.Point2d;

import static junit.framework.Assert.assertEquals;
import static junit.framework.Assert.assertTrue;
import static org.junit.Assert.assertNotNull;

public class RandTrialIntegrationTest {

    AbstractMStickPngTrialGenerator generator;
    NumberOfDistractorsForRandTrial numDistractors;
    NumberOfMorphCategories numMorphCategories;
    NoiseType noiseType;
    double[] noiseChance;

    RandNoisyTrialParameters trialParameters;
    RandTrial trial;


    private int numQMDistractors;
    private int numRandDistractors;
    private int numMMCategories;
    private int numQMCategories;
    private Lims sampleDistanceLims;
    private Lims choiceDistanceLims;
    private double size;
    private double eyeWinSize;
    private NoiseParameters noiseParameters;
    private long sampleId;
    private long matchId;
    private List<Long> qmDistractorIds;
    private List<Long> randDistractorIds;
    private NoisyPngSpec matchSpec;
    private NoisyPngSpec sampleSpec;
    private List<NoisyPngSpec> qmDistractorSpecs;
    private List<NoisyPngSpec> randDistractorSpecs;



    private void given_classic_test_trial() {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));

        generator = (PsychometricBlockGen) context.getBean(AbstractPsychometricTrialGenerator.class);
        TestTimeUtil timeUtil = new TestTimeUtil();
        generator.setGlobalTimeUtil(timeUtil);
        sampleId = timeUtil.getTestTime();
        matchId = sampleId + 1;
        qmDistractorIds = new LinkedList<>();
        for (int i = 0; i < numQMDistractors; i++) {
            qmDistractorIds.add(matchId + 1 + i);
        }
        randDistractorIds = new LinkedList<>();
        for (int i = 0; i < numRandDistractors; i++) {
            qmDistractorIds.add(matchId + 1 + numQMDistractors + i);
        }
        numQMDistractors = 1;
        numRandDistractors = 1;
        numDistractors = new NumberOfDistractorsForRandTrial(numQMDistractors, numRandDistractors);
        numMMCategories = 1;
        numQMCategories = 1;
        numMorphCategories = new NumberOfMorphCategories(numMMCategories, numQMCategories);
        noiseType = NoiseType.NONE;
        noiseChance = new double[]{0.5, 0.5};

        sampleDistanceLims = new Lims(0, 5);
        choiceDistanceLims = new Lims(9, 10);
        size = 10;
        eyeWinSize = 10;
        noiseParameters = new NoiseParameters(noiseType, new double[]{0, 0}, noiseChance);

        trialParameters = new RandNoisyTrialParameters(
                sampleDistanceLims,
                choiceDistanceLims,
                size,
                eyeWinSize,
                noiseParameters,
                numDistractors,
                numMorphCategories);

        trial = new RandTrial(
                generator,
                trialParameters);

    }

    @Test
    public void generates_classic_random_trial() {
        //Arrange
        given_classic_test_trial();
        RandTrial randTrial = new RandTrial(generator, trialParameters);

        //Act
        randTrial.preWrite();
        randTrial.write();

        //Assert
        draws_pngs();
        writesStimObjData();
		writesStimSpec();

    }

    private void draws_pngs() {

        String samplePath = getSamplePath();
        String matchPath = getMatchPath();
        List<String> qmDistractorPaths = getQmDistractorPaths();
        List<String> randDistractorPaths = getRandDistractorPaths();

        assertFileExists(samplePath);
        assertFileExists(matchPath);
        assertFilesExist(qmDistractorPaths);
        assertFilesExist(randDistractorPaths);
    }

    private String getSamplePath() {
        String samplePath = generator.getGeneratorPngPath() + "/" + Long.toString(sampleId) + "_sample.png";
        return samplePath;
    }

    private String getMatchPath() {
        return generator.getGeneratorPngPath() + "/" + Long.toString(matchId) + "_match.png";
    }

    private List<String> getQmDistractorPaths() {
        List<String> qmDistractorPaths = new LinkedList<>();
        for (int i = 0; i < numQMDistractors; i++) {
            String path = generator.getGeneratorPngPath() + "/" + Long.toString(matchId + 1 + i) + "_qmDistractor.png";
            qmDistractorPaths.add(path);
        }
        return qmDistractorPaths;
    }

    private List<String> getRandDistractorPaths() {
        List<String> randDistractorPaths = new LinkedList<>();
        for (int i = 0; i < numRandDistractors; i++) {
            String path = generator.getGeneratorPngPath() + "/" + Long.toString(matchId + 1 + numQMDistractors + i) + "_randDistractor.png";
            randDistractorPaths.add(path);
        }
        return randDistractorPaths;
    }

    private void writesStimObjData() {
        sampleSpec = getPngSpec(sampleId);
        matchSpec = getPngSpec(matchId);
        qmDistractorSpecs = getPngSpecs(qmDistractorIds);
        randDistractorSpecs = getPngSpecs(randDistractorIds);

        assertPngDetails(sampleSpec, sampleDistanceLims, getSamplePath());
        assertTrue(!sampleSpec.getNoiseMapPath().isEmpty());

        assertPngDetails(matchSpec, choiceDistanceLims, getMatchPath());
        int i = 0;
        for (NoisyPngSpec spec : qmDistractorSpecs) {
            assertPngDetails(spec, choiceDistanceLims, getQmDistractorPaths().get(i));
            i++;
        }
        i = 0;
        for (NoisyPngSpec spec : randDistractorSpecs) {
            assertPngDetails(spec, choiceDistanceLims, getRandDistractorPaths().get(i));
            i++;
        }
    }

    private List<NoisyPngSpec> getPngSpecs(List<Long> ids) {
        List<NoisyPngSpec> specs = new LinkedList<>();
        for (Long id : ids) {
            specs.add(getPngSpec(id));
        }
        return specs;
    }

    private NoisyPngSpec getPngSpec(long id) {
        StimSpecEntry entry = generator.getDbUtil().readStimObjData(id);
        NoisyPngSpec spec = NoisyPngSpec.fromXml(entry.getSpec());
        return spec;
    }

    private void assertPngDetails(NoisyPngSpec spec, Lims distanceLims, String expectedPath) {
        assertLocationWithinBounds(spec, distanceLims);
        assertTrue(spec.getDimensions().getWidth() == size);
        assertTrue(spec.getPngPath().equals(expectedPath));
        assertTrue(spec.getAlpha() == 1);
    }

    private static void assertLocationWithinBounds(NoisyPngSpec actualSpec, Lims distanceLims) {
        Point2d location = new Point2d(actualSpec.getxCenter(), actualSpec.getyCenter());
        double radius = location.distance(new Point2d(0, 0));
        assertTrue((double) radius <= distanceLims.getUpperLim());
        assertTrue((double) radius >= distanceLims.getLowerLim());
    }


    private void writesStimSpec(){
        StimSpecEntry sse = generator.getDbUtil().readStimSpec(sampleId);
        NAFCStimSpecSpec stimSpec = NAFCStimSpecSpec.fromXml(sse.getSpec());
        target_eye_window_coords_match_with_stimuli(stimSpec);
        rewarded_trial_is_match(stimSpec);
    }

    private void target_eye_window_coords_match_with_stimuli(NAFCStimSpecSpec stimSpec) {
        Coordinates2D matchCoords = new Coordinates2D(matchSpec.getxCenter(), matchSpec.getyCenter());
        assertTrue(stimSpec.getTargetEyeWinCoords()[0].equals(matchCoords));
        for(int i=1; i<numQMDistractors; i++){
            NoisyPngSpec qmDistractorSpec = qmDistractorSpecs.get(i - 1);
            Coordinates2D qmDistractorCoords = new Coordinates2D(qmDistractorSpec.getxCenter(), qmDistractorSpec.getyCenter());
           assertTrue(stimSpec.getTargetEyeWinCoords()[i].equals(qmDistractorCoords));
        }
        for(int i=2+numQMDistractors; i<numRandDistractors; i++){
            NoisyPngSpec randDistractorSpec = randDistractorSpecs.get(i - (2+numQMDistractors));
            Coordinates2D randDistractorCoords = new Coordinates2D(randDistractorSpec.getxCenter(), randDistractorSpec.getyCenter());
            assertTrue(stimSpec.getTargetEyeWinCoords()[i].equals(randDistractorCoords));
        }
    }

    private void rewarded_trial_is_match(NAFCStimSpecSpec stimSpec) {
        int rewarded = stimSpec.getRewardList()[0];
        assertTrue(stimSpec.getChoiceObjData()[rewarded]==matchId);
    }

    private void assertFilesExist(List<String> paths) {
        for (String path : paths) {
            assertFileExists(path);
        }
    }

    private void assertFileExists(String pngPaths) {
        File sample = new File(pngPaths);
        assertTrue(sample.exists());
    }


    private Rand<String> drawPNGs(Rand<AllenMatchStick> mSticks, Rand<Long> stimObjIds) {
        PNGDrawerForRandTrial drawer = new PNGDrawerForRandTrial(
                generator,
                mSticks,
                stimObjIds
        );
        Rand<String> pngPaths = drawer.getPngPaths();
        return pngPaths;
    }

    @Test
    public void mSticks_generate_noiseMaps() {
        //Arrange
        long id = 1L;
        generator.getPngMaker().createDrawerWindow();
        MStickGeneratorForRandTrials mStickGenerator = new MStickGeneratorForRandTrials(
                generator.getMaxImageDimensionDegrees(),
                trialParameters, generator.getMmpGenerator(), generator.getQmpGenerator());
        AllenMatchStick mStick = mStickGenerator.getSample();
        NoiseParameters noiseParameters = new NoiseParameters(new NoiseForm(noiseType, new double[]{0, 0.8}), noiseChance);
        RandTrialNoiseMapGenerator noiseMapGenerator = new RandTrialNoiseMapGenerator(id, mStick, noiseParameters, generator);
        generator.getPngMaker().close();

        //Act
        String path = noiseMapGenerator.getNoiseMapPath();

        //Assert
        assertFileExists(path);
    }

    @Test
    public void coords_are_radially_spaced() {
        RandTrialCoordinateAssigner coordAssigner = new RandTrialCoordinateAssigner(trialParameters.getSampleDistanceLims(), trialParameters.getNumDistractors(), trialParameters.getChoiceDistanceLims());

        Rand<Coordinates2D> coords = coordAssigner.getCoords();

        coords_have_same_distance_from_origin(coords);

    }


    private void coords_have_same_distance_from_origin(Rand<Coordinates2D> coords) {
        Coordinates2D origin = new Coordinates2D(0, 0);
        List<Coordinates2D> choices = new LinkedList<Coordinates2D>();
        choices.add(coords.getMatch());
        choices.addAll(coords.getAllDistractors());

        List<Long> radii = new LinkedList<Long>();
        for (Coordinates2D choice : choices) {
            radii.add(Math.round(choice.distance(origin) * 100) / 100);
        }

        assertTrue(Collections.frequency(radii, radii.get(0)) == radii.size());
    }


//    @Test
//    public void stim_obj_data() {
//        String noiseMapPath = "foo";
//        MStickGeneratorForRandTrials mStickGenerator = new MStickGeneratorForRandTrials(
//                generator,
//                trialParameters);
//
//        Rand<AllenMatchStick> mSticks = mStickGenerator.getmSticks();
//        Rand<AllenMStickSpec> mStickSpecs = mStickGenerator.getmStickSpecs();
//        Rand<Long> stimObjIds = getStimObjIds();
//        Rand<String> pngPaths = drawPNGs(mSticks, stimObjIds);
//        RandTrialCoordinateAssigner coordAssigner = new RandTrialCoordinateAssigner(trialParameters.getSampleDistanceLims(), trialParameters.getNumDistractors(), trialParameters.getChoiceDistanceLims());
//        Rand<Coordinates2D> coords = coordAssigner.getCoords();
//
//        getmStickSpecs();
//        RandTrialStimObjDataWriter stimObjDataWriter = new RandTrialStimObjDataWriter(
//                noiseMapPath,
//                generator.getDbUtil(),
//                trialParameters,
//                pngPaths,
//                stimObjIds,
//                mStickSpecs,
//                coords
//        );
//
//
//        stimObjDataWriter.writeStimObjId();
//
//        Long stimObjId = stimObjIds.getSample();
//        NoisyPngSpec stimObjData = NoisyPngSpec.fromXml(generator.getDbUtil().readStimObjData(stimObjId).getSpec());
//        assertEquals(stimObjData.getPngPath(), pngPaths.getSample());
//
//
////		StimSpecEntry entry = generator.getDbUtil().readStimObjData(stimObjIds.getSample());
////		StimSpecEntryUtil sseu = new StimSpecEntryUtil(entry);
////		NAFCStimSpecSpec stimObjSpec = sseu.NAFCStimSpecSpecFromXmlSpec();
//
//    }


}