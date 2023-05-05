package org.xper.allen.app.fixation;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.app.nafc.TrialArgReader;
import org.xper.allen.fixation.blockgen.NoisyPngFixationBlockGen;
import org.xper.allen.fixation.blockgen.NoisyPngFixationBlockParameters;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NoiseFormer;
import org.xper.allen.nafc.blockgen.TypeFrequency;
import org.xper.allen.nafc.vo.NoiseParameters;
import org.xper.allen.nafc.vo.NoiseType;
import org.xper.util.FileUtil;

import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;
import java.util.ListIterator;

public class NoisyPngFixationBlockGeneratorMain {

    public static void main(String[] args) {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));

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
            TypeFrequency<Lims> randNoiseChancesTF = new TypeFrequency<>(nextLimsType(), nextFrequency());
            TypeFrequency<NoiseType> noiseTypesTF = new TypeFrequency<>(stringToNoiseTypes(iterator.next()), nextFrequency());
            Lims distanceLims = stringToLim(iterator.next());
            double size = Double.parseDouble(iterator.next());

            List<NoiseType> noiseTypes = noiseTypesTF.getShuffledTrialList(numTrials);
            List<Lims> noiseChances = randNoiseChancesTF.getShuffledTrialList(numTrials);
            List<NoiseParameters> noiseParameters = new LinkedList<>();
            for(int i = 0; i< numTrials; i++){
                noiseParameters.add(new NoiseParameters(NoiseFormer.getNoiseForm(noiseTypes.get(i)), noiseChances.get(i)));
            }

            return new NoisyPngFixationBlockParameters(noiseParameters, distanceLims, size);
        }

    }
}
