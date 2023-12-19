package org.xper.allen.app.fixation;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.app.nafc.TrialArgReader;
import org.xper.allen.fixation.blockgen.NoisyPngFixationBlockGen;
import org.xper.allen.fixation.blockgen.NoisyPngFixationBlockParameters;
import org.xper.allen.fixation.blockgen.NoisyPngFixationTrialParameters;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NoiseFormer;
import org.xper.allen.nafc.blockgen.TypeFrequency;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.util.FileUtil;

import java.awt.*;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;
import java.util.ListIterator;

public class NoisyPngFixationBlockGeneratorMain {

    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));

        NoisyPngFixationBlockGen gen = context.getBean(NoisyPngFixationBlockGen.class);

        try {
            gen.setUp(NoisyPngFixationBlockGenInputTranslator.translate(args));
            gen.generate();
        } catch (Exception e){
            e.printStackTrace();
            System.out.println("Failed to generate trials");
        }

    }

    public static class NoisyPngFixationBlockGenInputTranslator extends TrialArgReader {

        public static NoisyPngFixationBlockParameters translate(String[] args){
            List<String> argsList = Arrays.asList(args);
            iterator = argsList.listIterator();
            int numTrials = Integer.parseInt(iterator.next());
            Lims distanceLims = stringToLim(iterator.next());
            double size = Double.parseDouble(iterator.next());
            double noiseChance = Double.parseDouble(iterator.next());

            Color color = new Color(255, 255, 255);
            NoisyPngFixationTrialParameters trialParams = new NoisyPngFixationTrialParameters(noiseChance, distanceLims, size, color);

            return new NoisyPngFixationBlockParameters(trialParams, numTrials);
        }

    }
}