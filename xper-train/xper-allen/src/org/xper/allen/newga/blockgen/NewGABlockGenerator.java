package org.xper.allen.newga.blockgen;

import org.xper.Dependency;
import org.xper.allen.ga.Child;
import org.xper.allen.ga.MultiGaGenerationInfo;
import org.xper.allen.ga.SlotSelectionProcess;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;
import org.xper.allen.ga3d.blockgen.RandStim;
import org.xper.allen.ga3d.blockgen.ThreeDGAStim;
import org.xper.drawing.Coordinates2D;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class NewGABlockGenerator extends GABlockGenerator {
    public static String gaBaseName = "New3D";

    public enum Regime {
        ZERO, ONE, TWO, THREE, FOUR
    }

    public static final Map<Regime, String> stimTypeForRegime = new HashMap<>();
    static {
        stimTypeForRegime.put(Regime.ZERO, "RegimeZero");
        stimTypeForRegime.put(Regime.ONE, "RegimeOne");
        stimTypeForRegime.put(Regime.TWO, "RegimeTwo");
        stimTypeForRegime.put(Regime.THREE, "RegimeThree");
        stimTypeForRegime.put(Regime.FOUR, "RegimeFour");
    }

    @Dependency
    SlotSelectionProcess slotSelectionProcess;

    // Constructor
    int numStimuliPerGeneration;
    double initialSize;
    private Coordinates2D initialCoords;

    @Override
    protected void addTrials() {
        if (isFirstGeneration()) {
            addFirstGeneration();
        } else {
            addNthGeneration();
        }
    }

    private void addFirstGeneration() {
        getStims().addAll(createRandStim(this, numStimuliPerGeneration, initialSize, initialCoords));
    }

    private List<ThreeDGAStim> createRandStim(GABlockGenerator generator, int numTrials, double size, Coordinates2D coords) {
        List<ThreeDGAStim> trials = new LinkedList<>();
        for (int i = 0; i < numTrials; i++) {
            trials.add(new RandStim(generator, size, coords));
        }
        return trials;
    }

    private void addNthGeneration() {
        List<Child> selectedParents = slotSelectionProcess.select(getGaBaseName());
        for (Child child: selectedParents) {
            if (child.getRegime().equals(Regime.ONE)) {
                getStims().add(new RegimeOneStim(this, child.getParentId()));
            }
            else if (child.getRegime().equals(Regime.TWO)) {
                getStims().add(new RegimeTwoStim(this, child.getParentId()));
            } else if (child.getRegime().equals(Regime.THREE)) {

                getStims().add(new RegimeThreeStim(this, child.getParentId()));
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