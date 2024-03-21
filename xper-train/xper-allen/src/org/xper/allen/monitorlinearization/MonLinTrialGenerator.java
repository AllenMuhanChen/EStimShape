package org.xper.allen.monitorlinearization;

import org.xper.Dependency;
import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.drawing.RGBColor;

import java.util.*;

public class MonLinTrialGenerator extends AbstractTrialGenerator<MonLinStim> {
    @Dependency
    LookUpTableCorrector lutCorrect;

    @Dependency
    SinusoidGainCorrector sinusoidGainCorrector;

    public String mode;


    @Override
    protected void addTrials() {
        if (mode.equals("Isoluminant")){
            int numRepeats = 5;
            for (int i = 0; i < numRepeats; i++) {
                addIsoluminantTrials();
            }
        }
        else if (mode.equals("Linear")){
            addLinearTrials(256);
        }
        else if (mode.equals("RedGreenSinusoidal")){
            int numRepeats = 5;
            for (int i = 0; i < numRepeats; i++) {
                addRedGreenSinusoidalTrials();
            }
        }
        else if (mode.equals("RedGreenSinusoidalLargeSpan")){
            int numRepeats = 1;
            for (int i = 0; i < numRepeats; i++) {
                addRedGreenSinusoidalTrialsLargeSpan();
            }
        }
        else if (mode.equals("LinearRepeats")){
            int numRepeats = 5;
            for (int i = 0; i < numRepeats; i++) {
                addLinearTrials(256);
            }
        }


    }

    /**
     * For isoluminance calibration of various angles on red/green sinusoid
     * at various gains to find the gain that will make the red and green combinations
     * equal to a target luminance.
     */
    private void addRedGreenSinusoidalTrials() {
        double targetLuminance = 150;

        //define some angles on a sine wave
//        List<Double> angles = Arrays.asList(0.0, 22.5, 45.0, 67.5, 90.0, 112.5, 135.0, 157.5, 180.0);
//        List<Double> angles = range(0, 180, 100);
        List<Double> angles = range(0, 180, 100);

        //calculate red and green luminances for each angle
        List<Double> redLuminances = new LinkedList<>();
        List<Double> greenLuminances = new LinkedList<>();
        for (double angle : angles) {
            //each pair of red and green luminances should add to up to the target luminance
            double redLuminance = targetLuminance * (1 + Math.cos(Math.toRadians(angle)))/2;
            double greenLuminance = targetLuminance * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            redLuminances.add(redLuminance);
            greenLuminances.add(greenLuminance);
            System.out.println("Sum of red and green luminances: " + (redLuminance + greenLuminance));
        }

        //GAINS
        List<Double> gains = range(0.85, 1.05, 20);

        //for each angle, create a trial for each gain
        for (int i = 0; i < angles.size(); i++) {
            for (double gain : gains) {
                double redLuminance = redLuminances.get(i) * gain;
                double greenLuminance = greenLuminances.get(i) * gain;
                RGBColor corrected = lutCorrect.correctRedGreen(redLuminance, greenLuminance);
//                int R = (int) Math.round(correction.redGamma.correct((float) redLuminance));
//                int G = (int) Math.round(correction.greenGamma.correct((float) greenLuminance));
//                RGBColor corrected = new RGBColor(R/255.0f, G/255.0f, 0);
                stims.add(new MonLinStim(this, corrected, angles.get(i), gain));
            }
        }


    }

    /**
     * Run before running the red green sinusoidal trials to find the range of gains
     * that should be tested
     */
    private void addRedGreenSinusoidalTrialsLargeSpan() {
        double targetLuminance = 150;

        //define some angles on a sine wave
//        List<Double> angles = Arrays.asList(0.0, 22.5, 45.0, 67.5, 90.0, 112.5, 135.0, 157.5, 180.0);
//        List<Double> angles = range(0, 180, 100);
        List<Double> angles = range(0, 180, 16);

        //calculate red and green luminances for each angle
        List<Double> redLuminances = new LinkedList<>();
        List<Double> greenLuminances = new LinkedList<>();
        for (double angle : angles) {
            //each pair of red and green luminances should add to up to the target luminance
            double redLuminance = targetLuminance * (1 + Math.cos(Math.toRadians(angle)))/2;
            double greenLuminance = targetLuminance * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            redLuminances.add(redLuminance);
            greenLuminances.add(greenLuminance);
            System.out.println("Sum of red and green luminances: " + (redLuminance + greenLuminance));
        }

        //GAINS
        List<Double> gains = range(0.6, 1.4, 10);

        //for each angle, create a trial for each gain
        for (int i = 0; i < angles.size(); i++) {
            for (double gain : gains) {
                double redLuminance = redLuminances.get(i) * gain;
                double greenLuminance = greenLuminances.get(i) * gain;
                RGBColor corrected = lutCorrect.correctRedGreen(redLuminance, greenLuminance);
//                int R = (int) Math.round(correction.redGamma.correct((float) redLuminance));
//                int G = (int) Math.round(correction.greenGamma.correct((float) greenLuminance));
//                RGBColor corrected = new RGBColor(R/255.0f, G/255.0f, 0);
                stims.add(new MonLinStim(this, corrected, angles.get(i), gain));
            }
        }


    }

    public static List<Double> range(double start, double end, int n) {
        if (n <= 0) {
            throw new IllegalArgumentException("n must be a positive integer");
        }

        List<Double> numbers = new ArrayList<>();
        double step = (end - start) / (n - 1);

        for (int i = 0; i < n; i++) {
            numbers.add(start + i * step);
        }

        return numbers;
    }

    /**
     * Tests if the isoluminant correction is working (as a combination of look-up-table and sinusoidal gain correction)
     */
    private void addIsoluminantTrials() {
        float targetLuminance = 150;
        int steps = 100;
        double r;
        double g;
        double b;
        for (int i = 0; i < steps; i++) {
            double angle = 180 * i / steps;
            //each pair of red and green luminances should add to up to the target luminance
            double luminanceRed = targetLuminance * (1 + Math.cos(Math.toRadians(angle)))/2;
            double luminanceGreen = targetLuminance * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            System.out.println("Target Lum REd: " + luminanceRed);
            System.out.println("Target Lum Green: " + luminanceGreen);
            double gain = sinusoidGainCorrector.getGain(angle, "'RedGreen'");
            System.out.println("GAIN: " + gain);
            RGBColor lookUpCorrected = lutCorrect.correctRedGreen(luminanceRed * gain, luminanceGreen * gain);

            System.out.println(lookUpCorrected.getRed());
            System.out.println(lookUpCorrected.getGreen());


//            int R = (int) Math.round(correction.redGamma.correct(luminanceRed));
//            int G = (int) Math.round(correction.greenGamma.correct(luminanceGreen));

            stims.add(new MonLinStim(this, lookUpCorrected, angle, gain));
//            float modFactor = (float) i / (steps-1);
//            r = interpolate(1.0, 0, modFactor);
//            g = 1 - r;
//            b = 0;
//            RGBColor corrected = correction.correct(new RGBColor((float) r, (float) g, (float) b), 200);
//            stims.add(new MonLinStim(this, corrected));
        }
    }

    private void addLinearTrials(int numSteps) {

        for (int i = 0; i < numSteps; i++) {
            RGBColor newColor = new RGBColor(
            (float) i / (numSteps -1),
                0f,
                0f
            );

            stims.add(new MonLinStim(this, newColor));
        }

        for (int i = 0; i < numSteps; i++) {
            RGBColor newColor = new RGBColor(
                0f,
                (float) i / (numSteps -1),
                0f
            );

            stims.add(new MonLinStim(this, newColor));
        }

        for (int i = 0; i < numSteps; i++) {
            RGBColor newColor = new RGBColor(
                0f,
                0f,
                (float) i / (numSteps -1)
            );

            stims.add(new MonLinStim(this, newColor));
        }
        System.out.println("Added " + stims.size() + " trials");

    }

    protected void shuffleTrials() {
//        Collections.shuffle(stims);
    }

    private double interpolate(double value1, double value2, float factor) {
        return value1 + (value2 - value1) * factor;
    }

    public LookUpTableCorrector getLutCorrect() {
        return lutCorrect;
    }

    public void setLutCorrect(LookUpTableCorrector lutCorrect) {
        this.lutCorrect = lutCorrect;
    }

    public void setSinusoidCorrect(SinusoidGainCorrector sinusoidGainCorrector) {
        this.sinusoidGainCorrector = sinusoidGainCorrector;
    }
}