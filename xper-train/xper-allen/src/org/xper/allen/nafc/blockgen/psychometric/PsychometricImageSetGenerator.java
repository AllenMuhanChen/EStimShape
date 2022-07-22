package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.qualitativemorphs.PsychometricQualitativeMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParameterGenerator;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;

public class PsychometricImageSetGenerator {
    private final PsychometricBlockGen psychometricBlockGen;

    public PsychometricImageSetGenerator(PsychometricBlockGen psychometricBlockGen) {
        this.psychometricBlockGen = psychometricBlockGen;
    }

    public void generateImageSet(int numPerSet, double size, double percentChangePosition, int numRand) {
        if (numRand > numPerSet) {
            throw new IllegalArgumentException("numRand should not be greater than numPerSet");
        }

        //Preallocation & Set-up
        List<StimType> stimTypes = new LinkedList<StimType>();
        boolean tryagain = true;
        int nTries = 0;
        AllenMatchStick objs_base = new AllenMatchStick();
        List<AllenMatchStick> objs = new ArrayList<AllenMatchStick>();
        for (int i = 0; i < numPerSet; i++) {
            objs.add(new AllenMatchStick());

            if (i == 0) {
                stimTypes.add(StimType.BASE);
            } else if (i > 0 && i < numPerSet - numRand) {
                stimTypes.add(StimType.QM);
            } else {
                stimTypes.add(StimType.RAND);
            }
        }

        int numQMMorphs = numPerSet - 1;
        List<QualitativeMorphParams> qmps = new LinkedList<QualitativeMorphParams>();
        PsychometricQualitativeMorphParameterGenerator qmpGenerator = new PsychometricQualitativeMorphParameterGenerator(psychometricBlockGen.getMaxImageDimensionDegrees());
        qmps = qmpGenerator.getQMP(numPerSet - 1 - numRand, percentChangePosition);

        //VETTING AND CHOOSING LEAF
        psychometricBlockGen.getPngMaker().createDrawerWindow();

        while (tryagain) {
            boolean firstObjSuccess = false;
            Boolean[] restObjSuccess = new Boolean[numPerSet - 1];
            for (int b = 0; b < restObjSuccess.length; b++) restObjSuccess[b] = false;
            boolean restOfObjsSuccess = false;

            objs_base.setProperties(psychometricBlockGen.getMaxImageDimensionDegrees());

            //LEAF
            int randomLeaf = -1;
            {

                int nTries_leaf = 0;

                while (true) {
                    System.out.println("In Leaf: Attempt " + (nTries_leaf + 1));
                    objs_base.genMatchStickRand();
                    randomLeaf = objs_base.chooseRandLeaf();
                    boolean leafSuccess = objs_base.vetLeaf(randomLeaf);
                    if (!leafSuccess) {
                        objs_base = new AllenMatchStick();
                    } else {
                        break;
                    }
                    nTries_leaf++;
                }
            }

            int maxAttemptsPerObj = 3;


            //FIRST OBJ
            int nTries_obj = 0;
            while (nTries_obj < maxAttemptsPerObj) {
                //				System.out.println("In Obj " + 0 + ": attempt " + nTries_obj + " out of " + maxAttemptsPerObj);
                objs.get(0).setProperties(psychometricBlockGen.getMaxImageDimensionDegrees());
                firstObjSuccess = objs.get(0).genMatchStickFromLeaf(randomLeaf, objs_base);
                if (!firstObjSuccess) {
                    objs.set(0, new AllenMatchStick());
                } else {
                    break;
                }
                nTries_obj++;
            }

            //REST OF THE OBJS
            if (firstObjSuccess) {
                int leafToMorphIndx = objs.get(0).getSpecialEndComp().get(0);
                for (int i = 1; i < numPerSet; i++) {
                    nTries_obj = 0;
                    while (nTries_obj < maxAttemptsPerObj) {
                        //						System.out.println("In Obj " + i + ": attempt " + nTries_obj + " out of " + maxAttemptsPerObj);
                        try {
                            objs.get(i).setProperties(psychometricBlockGen.getMaxImageDimensionDegrees());
                            if (stimTypes.get(i) == StimType.QM)
                                restObjSuccess[i - 1] = objs.get(i).genQualitativeMorphedLeafMatchStick(leafToMorphIndx, objs.get(0), qmps.get(i - 1));
                            else {
                                try {
                                    objs.get(i).genMatchStickRand();
                                    restObjSuccess[i - 1] = true;
                                } catch (Exception e) {
                                    restObjSuccess[i - 1] = false;
                                }
                            }
                        } catch (Exception e) {
                            e.printStackTrace();
                            restObjSuccess[i - 1] = false;
                        }
                        if (!restObjSuccess[i - 1]) {
                            objs.set(i, new AllenMatchStick());
                        } else {
                            break;
                        }
                        nTries_obj++;
                    }

                }
                restOfObjsSuccess = !Arrays.asList(restObjSuccess).contains(false);
            }
            if (restOfObjsSuccess) {
                tryagain = false;
                System.out.println("SUCCESS!");
            } else {
                tryagain = true;
                nTries++;
                System.out.println("TRYING AGAIN: " + nTries + " tries.");
            }
        }

        //DRAWING AND SAVING
        List<List<String>> labels = new LinkedList<List<String>>();
        List<Long> ids = new LinkedList<Long>();

        long setId = psychometricBlockGen.getGlobalTimeUtil().currentTimeMicros();
        for (int i = 0; i < numPerSet; i++) {
            List<String> label = new ArrayList<String>();
            label.add(Integer.toString(i));
            labels.add(label);
            ids.add(setId);
        }

        List<String> stimPaths = psychometricBlockGen.getPngMaker().createAndSaveBatchOfPNGs(objs, ids, labels, psychometricBlockGen.getGeneratorPsychometricPngPath());

        //SAVE SPECS.TXT
        for (int k = 0; k < objs.size(); k++) {
            AllenMStickSpec spec = new AllenMStickSpec();
            spec.setMStickInfo(objs.get(k));
            spec.writeInfo2File(psychometricBlockGen.getGeneratorPsychometricSpecPath() + "/" + ids.get(k) + "_" + labels.get(k).get(0), true);
        }
        psychometricBlockGen.getPngMaker().close();
    }

    private enum StimType {
        QM, RAND, BASE;
    }
}