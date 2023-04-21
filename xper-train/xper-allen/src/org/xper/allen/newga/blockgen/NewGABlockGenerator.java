package org.xper.allen.newga.blockgen;

import org.xper.Dependency;
import org.xper.allen.ga.Child;
import org.xper.allen.ga.MultiGaGenerationInfo;
import org.xper.allen.ga.SlotSelectionProcess;
import org.xper.allen.ga.regimescore.Regime;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;
import org.xper.allen.ga3d.blockgen.RandStim;
import org.xper.allen.ga3d.blockgen.ThreeDGAStim;
import org.xper.allen.util.TikTok;
import org.xper.drawing.Coordinates2D;

import java.util.*;

public class NewGABlockGenerator extends GABlockGenerator {
    public static String gaBaseName = "New3D";


    public static final Map<Regime, String> stimTypeForRegime = createMap();

    private static Map<Regime, String> createMap() {
        HashMap<Regime, String> stimTypeForRegime = new HashMap<Regime, String>();
        stimTypeForRegime.put(Regime.ZERO, "RegimeZero");
        stimTypeForRegime.put(Regime.ONE, "RegimeOne");
        stimTypeForRegime.put(Regime.TWO, "RegimeTwo");
        stimTypeForRegime.put(Regime.THREE, "RegimeThree");
        stimTypeForRegime.put(Regime.FOUR, "RegimeFour");
        return Collections.unmodifiableMap(stimTypeForRegime);
    }


    @Dependency
    SlotSelectionProcess slotSelectionProcess;

    // Constructor
    double initialSize = 5.0;
    private Coordinates2D initialCoords = new Coordinates2D(0, 0);

    @Override
    protected void addTrials() {
        if (isFirstGeneration()) {
            addFirstGeneration();
        } else {
            addNthGeneration();
        }
    }

    private void addFirstGeneration() {
        getStims().addAll(createRandStim(this, slotSelectionProcess.getNumChildrenToSelect(), initialSize, initialCoords));
    }

    private List<ThreeDGAStim> createRandStim(NewGABlockGenerator generator, int numTrials, double size, Coordinates2D coords) {
        List<ThreeDGAStim> trials = new LinkedList<>();
        for (int i = 0; i < numTrials; i++) {
            trials.add(new RegimeZeroStim(generator, size, coords));
        }
        return trials;
    }

    private void addNthGeneration() {
        System.out.println("Selecting Parents");
        TikTok selecingParentsTimer = new TikTok("Selecting Parents");
        List<Child> selectedParents = slotSelectionProcess.select(getGaBaseName());
        selecingParentsTimer.stop();
        for (Child child: selectedParents) {
            System.out.println("Attemptins regime " + child.getRegime() + " for parent " + child.getParentId() + "");
            if (child.getRegime().equals(Regime.ZERO)) {
                TikTok timer = new TikTok("Adding Regime Zero Stim");
                System.out.println("Adding Regime Zero Stim");
                getStims().add(new RegimeZeroStim(this, initialSize, initialCoords));
                timer.stop();
            }
            else if (child.getRegime().equals(Regime.ONE)) {
                TikTok timer = new TikTok("Adding Regime One Stim");
                System.out.println("Adding Regime One Stim");
                getStims().add(new RegimeOneStim(this, child.getParentId()));
                timer.stop();
            }
            else if (child.getRegime().equals(Regime.TWO)) {
                TikTok timer = new TikTok("Adding Regime Two Stim");
                System.out.println("Adding Regime Two Stim");
                getStims().add(new RegimeTwoStim(this, child.getParentId()));
                timer.stop();
            } else if (child.getRegime().equals(Regime.THREE)) {
                TikTok timer = new TikTok("Adding Regime Three Stim");
                System.out.println("Adding Regime Three Stim");
                getStims().add(new OldRegimeThreeStim(this, child.getParentId()));
                timer.stop();
            } else {
                throw new RuntimeException("Invalid Regime");
            }
        }

    }

    private boolean isFirstGeneration() {
        MultiGaGenerationInfo info = dbUtil.readReadyGAsAndGenerationsInfo();
        Map<String, Long> readyGens = info.getGenIdForGA();

        return readyGens.getOrDefault(getGaBaseName(), 0L) == 0;
    }

    public String getGaBaseName() {
        return gaBaseName;
    }

    public SlotSelectionProcess getSlotSelectionProcess() {
        return slotSelectionProcess;
    }

    public void setSlotSelectionProcess(SlotSelectionProcess slotSelectionProcess) {
        this.slotSelectionProcess = slotSelectionProcess;
    }
}