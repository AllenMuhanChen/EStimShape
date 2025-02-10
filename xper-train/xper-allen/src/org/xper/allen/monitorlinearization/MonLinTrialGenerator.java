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
        int targetLuminance = 400;
        if (mode.equals("RedGreenIsoluminant")){
            int numRepeats = 2;
            for (int i = 0; i < numRepeats; i++) {
                addRedGreenIsoluminantTrials(targetLuminance);
            }
        }
        else if (mode.equals("CyanYellowIsoluminant")){
            int numRepeats = 1;
            for (int i = 0; i < numRepeats; i++) {
                addCyanYellowIsoluminantTrials(targetLuminance);
            }
        }
        else if (mode.equals("CyanOrangeIsoluminant")){
            int numRepeats = 1;
            for (int i = 0; i < numRepeats; i++) {
                addCyanOrangeIsoluminantTrials(targetLuminance);
            }
        }
        else if (mode.equals("Linear")){
            addLinearTrials(256);
        }
        else if (mode.equals("RedGreenSinusoidal")){
            int numRepeats = 1;
            for (int i = 0; i < numRepeats; i++) {
                addRedGreenSinusoidalTrials(targetLuminance);
            }
        }
        else if (mode.equals("RedGreenSinusoidalLargeSpan")){
            int numRepeats = 1;
            for (int i = 0; i < numRepeats; i++) {
                addRedGreenSinusoidalTrialsLargeSpan(targetLuminance);
            }
        }
        else if (mode.equals("CyanOrangeSinusoidal")){
            int numRepeats = 1;
            for (int i = 0; i < numRepeats; i++) {
                addCyanOrangeSinusoidalTrials(targetLuminance);
            }
        }
        else if (mode.equals("CyanYellowSinusoidal")){
            int numRepeats = 1;
            for (int i = 0; i < numRepeats; i++) {
                addCyanYellowSinusoidalTrials(targetLuminance);
            }
        }
        else if (mode.equals("CyanYellowSinusoidalLargeSpan")){
            int numRepeats = 1;
            for (int i = 0; i < numRepeats; i++) {
                addCyanYellowSinusoidalTrialsLargeSpan(targetLuminance);
            }
        }
        else if (mode.equals("LinearRepeats")){
            int numRepeats = 5;
            for (int i = 0; i < numRepeats; i++) {
                addLinearTrials(256);
            }
        }
        else if (mode.equals("Gray")){
            int numRepeats = 1;
            for (int i = 0; i < numRepeats; i++) {
                addGrayCalibrationTrials(256);
            }
        }
        else {
            throw new RuntimeException("Unknown mode: " + mode);
        }


    }

    /**
     * For isoluminance calibration of various angles on red/green sinusoid
     * at various gains to find the gain that will make the red and green combinations
     * equal to a target luminance.
     * @param targetLuminance
     */
    private void addRedGreenSinusoidalTrials(double targetLuminance) {

        //define some angles on a sine wave
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
        }

        //GAINS
        List<Double> gains = range(0.96, 1.04, 10);

        //for each angle, create a trial for each gain
        for (int i = 0; i < angles.size(); i++) {
            for (double gain : gains) {
                double redLuminance = redLuminances.get(i) * gain;
                double greenLuminance = greenLuminances.get(i) * gain;
                RGBColor corrected = lutCorrect.correctRedGreen(redLuminance, greenLuminance);
                stims.add(new MonLinStim(this, corrected, angles.get(i), gain));
            }
        }
    }
    private void addCyanOrangeSinusoidalTrials(double targetLuminance){
        //define some angles on a sine wave
        List<Double> angles = range(0, 180, 100);

        //calculate red and green luminances for each angle
        List<Double> cyanLuminances = new LinkedList<>();
        List<Double> orangeLuminances = new LinkedList<>();
        for (double angle : angles) {
            //each pair of red and green luminances should add to up to the target luminance
            double cyanLuminance = targetLuminance * (1 + Math.cos(Math.toRadians(angle)))/2;
            double orangeLuminance = targetLuminance * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            cyanLuminances.add(cyanLuminance);
            orangeLuminances.add(orangeLuminance);
        }

        //GAINS
        List<Double> gains = range(0.4, 1.0, 20);
        if (!gains.contains(1.0)){
            gains.add(1.0);
        }

        //for each angle, create a trial for each gain
        for (int i = 0; i < angles.size(); i++) {
            for (double gain : gains) {
                double cyanLuminance = cyanLuminances.get(i) * gain;
                double orangeLuminance = orangeLuminances.get(i) * gain;
                RGBColor corrected = lutCorrect.correctCyanOrange(cyanLuminance, orangeLuminance);
                stims.add(new MonLinStim(this, corrected, angles.get(i), gain));
            }
        }
    }

    private void addCyanYellowSinusoidalTrials(double targetLuminance) {

        //define some angles on a sine wave
        List<Double> angles = range(0, 180, 100);

        //calculate red and green luminances for each angle
        List<Double> cyanLuminances = new LinkedList<>();
        List<Double> yellowLuminances = new LinkedList<>();
        for (double angle : angles) {
            //each pair of red and green luminances should add to up to the target luminance
            double redLuminance = targetLuminance * (1 + Math.cos(Math.toRadians(angle)))/2;
            double greenLuminance = targetLuminance * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            cyanLuminances.add(redLuminance);
            yellowLuminances.add(greenLuminance);
        }

        //GAINS
        List<Double> gains = range(0.8, 1.8, 20);

        //for each angle, create a trial for each gain
        for (int i = 0; i < angles.size(); i++) {
            for (double gain : gains) {
                double cyanLuminance = cyanLuminances.get(i) * gain;
                double yellowLuminance = yellowLuminances.get(i) * gain;
                RGBColor corrected = lutCorrect.correctCyanYellow(cyanLuminance, yellowLuminance);
                stims.add(new MonLinStim(this, corrected, angles.get(i), gain));
            }
        }
    }

    private void addCyanYellowSinusoidalTrialsLargeSpan(double targetLuminance) {

        //define some angles on a sine wave
        List<Double> angles = range(0, 180, 16);

        //calculate red and green luminances for each angle
        List<Double> cyanLuminances = new LinkedList<>();
        List<Double> yellowLuminances = new LinkedList<>();
        for (double angle : angles) {
            //each pair of red and green luminances should add to up to the target luminance
            double cyanLuminance = targetLuminance * (1 + Math.cos(Math.toRadians(angle)))/2;
            double yellowLuminance = targetLuminance * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            cyanLuminances.add(cyanLuminance);
            yellowLuminances.add(yellowLuminance);
        }

        //GAINS
        List<Double> gains = range(0.2, 2.0, 10);

        //for each angle, create a trial for each gain
        for (int i = 0; i < angles.size(); i++) {
            for (double gain : gains) {
                double cyanLuminance = cyanLuminances.get(i) * gain;
                double yellowLuminance = yellowLuminances.get(i) * gain;
                RGBColor corrected = lutCorrect.correctCyanYellow(cyanLuminance, yellowLuminance);
                stims.add(new MonLinStim(this, corrected, angles.get(i), gain));
            }
        }
    }



    /**
     * Run before running the red green sinusoidal trials to find the range of gains
     * that should be tested
     * @param targetLuminance
     */
    private void addRedGreenSinusoidalTrialsLargeSpan(double targetLuminance) {

        //define some angles on a sine wave
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
                stims.add(new MonLinStim(this, corrected, angles.get(i), gain));
            }
        }
    }

    private void addGrayCalibrationTrials(int numSteps){
        float min = 0.1f;
        float max = 0.5f;
        for (int i = 0; i < numSteps; i++) {
            RGBColor newColor = new RGBColor(
                    (float) interpolate(min, max, (float) i / (numSteps -1)),
                    (float) interpolate(min, max, (float) i / (numSteps -1)),
                    (float) interpolate(min, max, (float) i / (numSteps -1))
            );

            stims.add(new MonLinStim(this, newColor));
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
     * @param targetLuminance
     */
    private void addRedGreenIsoluminantTrials(float targetLuminance) {
        int steps = 100;
        for (int i = 0; i < steps; i++) {
            double angle = (double) (180 * i) / steps;
            //each pair of red and green luminances should add to up to the target luminance
            double luminanceRed = targetLuminance * (1 + Math.cos(Math.toRadians(angle)))/2;
            double luminanceGreen = targetLuminance * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            System.out.println("Target Lum REd: " + luminanceRed);
            System.out.println("Target Lum Green: " + luminanceGreen);
            double gain = sinusoidGainCorrector.getGain(angle, "RedGreen");
            System.out.println("GAIN: " + gain);
            RGBColor lookUpCorrected = lutCorrect.correctRedGreen(luminanceRed * gain, luminanceGreen * gain);

            System.out.println(lookUpCorrected.getRed());
            System.out.println(lookUpCorrected.getGreen());


            stims.add(new MonLinStim(this, lookUpCorrected, angle, gain));
        }
    }

    private void addCyanYellowIsoluminantTrials(float targetLuminance){
        int steps = 100;
        for (int i = 0; i < steps; i++) {
            double angle = (double) (180 * i) / steps;
            //each pair of red and green luminances should add to up to the target luminance
            double luminanceCyan = targetLuminance * (1 + Math.cos(Math.toRadians(angle))) / 2;
            double luminanceYellow = targetLuminance * (1 + Math.cos(Math.toRadians(angle - 180))) / 2;
            System.out.println("Target Lum Cyan: " + luminanceCyan);
            System.out.println("Target Lum Yellow: " + luminanceYellow);
            double gain = sinusoidGainCorrector.getGain(angle, "CyanYellow");
            System.out.println("GAIN: " + gain);
            RGBColor lookUpCorrected = lutCorrect.correctCyanYellow(luminanceCyan * gain, luminanceYellow * gain);


            System.out.println(lookUpCorrected.getRed());
            System.out.println(lookUpCorrected.getGreen());

            stims.add(new MonLinStim(this, lookUpCorrected, angle, gain));
        }
    }

    private void addCyanOrangeIsoluminantTrials(float targetLuminnance){
        int steps = 100;
        for (int i = 0; i < steps; i++) {
            double angle = (double) (180 * i) / steps;
            //each pair of red and green luminances should add to up to the target luminance
            double luminanceCyan = targetLuminnance * (1 + Math.cos(Math.toRadians(angle))) / 2;
            double luminanceOrange = targetLuminnance * (1 + Math.cos(Math.toRadians(angle - 180))) / 2;
            System.out.println("Target Lum Cyan: " + luminanceCyan);
            System.out.println("Target Lum Orange: " + luminanceOrange);
            double gain = sinusoidGainCorrector.getGain(angle, "CyanOrange");
            System.out.println("GAIN: " + gain);
            RGBColor lookUpCorrected = lutCorrect.correctCyanOrange(luminanceCyan * gain, luminanceOrange * gain);

            stims.add(new MonLinStim(this, lookUpCorrected, angle, gain));
        }
    }

    private void addLinearTrials(int numSteps) {
        //Cyan
        float[] cyanHSV = rgbToHsv(0, 1, 1);
        float cyanHue = cyanHSV[0]; //degrees 0-360
        float cyanSaturation = cyanHSV[1]; //0-1
        float cyanValue; //0-1

        for (int i = 0; i < numSteps; i++) {
            cyanValue = (float) i / (numSteps -1);
            int[] RGB = hsvToRgb(cyanHue, cyanSaturation, cyanValue);
            System.out.println("Cyan: " + RGB[0] + " " + RGB[1] + " " + RGB[2]);
            stims.add(new MonLinStim(this, new RGBColor((float) RGB[0]/255f, (float) RGB[1]/255f, (float) RGB[2]/255f)));
        }

        //Yellow
//        float[] yellowHSV = rgbToHsv(1, 1, 0);
//        double yellowHue = yellowHSV[0]; //degrees 0-360
//        double yellowSaturation = yellowHSV[1]; //0-1
//        double yellowValue; //0-1
//
//        for (int i = 0; i < numSteps; i++) {
//            yellowValue = (float) i / (numSteps -1);
//            int[] RGB = hsvToRgb((float) yellowHue, (float) yellowSaturation, (float) yellowValue);
//            System.out.println("Yellow: " + RGB[0] + " " + RGB[1] + " " + RGB[2]);
//            stims.add(new MonLinStim(this, new RGBColor((float) RGB[0]/255f, (float) RGB[1]/255f, (float) RGB[2]/255f)));
//        }

        //Orange
        float[] orangeHSV = rgbToHsv(2, 1, 0);
        float orangeHue = orangeHSV[0]; //degrees 0-360
        float orangeSaturation = orangeHSV[1]; //0-1
        float orangeValue; //0-1

        for (int i = 0; i < numSteps; i++) {
            orangeValue = (float) i / (numSteps -1);
            int[] RGB = hsvToRgb(orangeHue, orangeSaturation, orangeValue);
            System.out.println("Orange: " + RGB[0] + " " + RGB[1] + " " + RGB[2]);
            stims.add(new MonLinStim(this, new RGBColor((float) RGB[0]/255f, (float) RGB[1]/255f, (float) RGB[2]/255f)));
        }

        //RED
        for (int i = 0; i < numSteps; i++) {
            RGBColor newColor = new RGBColor(
            (float) i / (numSteps -1),
                0f,
                0f
            );

            stims.add(new MonLinStim(this, newColor));
        }

        //GREEN
        for (int i = 0; i < numSteps; i++) {
            RGBColor newColor = new RGBColor(
                0f,
                (float) i / (numSteps -1),
                0f
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

    public static float[] rgbToHsv(int r, int g, int b) {
        float rPrime = r / 255f;
        float gPrime = g / 255f;
        float bPrime = b / 255f;

        float cMax = Math.max(rPrime, Math.max(gPrime, bPrime));
        float cMin = Math.min(rPrime, Math.min(gPrime, bPrime));
        float delta = cMax - cMin;

        float hue = 0;
        if (delta != 0) {
            if (cMax == rPrime) {
                hue = 60 * (((gPrime - bPrime) / delta) % 6);
            } else if (cMax == gPrime) {
                hue = 60 * (((bPrime - rPrime) / delta) + 2);
            } else if (cMax == bPrime) {
                hue = 60 * (((rPrime - gPrime) / delta) + 4);
            }
        }
        hue = (hue < 0) ? hue + 360 : hue;

        float saturation = (cMax == 0) ? 0 : delta / cMax;

        float value = cMax;

        return new float[]{hue, saturation, value};
    }

    public static int[] hsvToRgb(float h, float s, float v) {
        float c = v * s;
        float x = c * (1 - Math.abs((h / 60) % 2 - 1));
        float m = v - c;

        float rPrime = 0, gPrime = 0, bPrime = 0;

        if (h >= 0 && h < 60) {
            rPrime = c;
            gPrime = x;
            bPrime = 0;
        } else if (h >= 60 && h < 120) {
            rPrime = x;
            gPrime = c;
            bPrime = 0;
        } else if (h >= 120 && h < 180) {
            rPrime = 0;
            gPrime = c;
            bPrime = x;
        } else if (h >= 180 && h < 240) {
            rPrime = 0;
            gPrime = x;
            bPrime = c;
        } else if (h >= 240 && h < 300) {
            rPrime = x;
            gPrime = 0;
            bPrime = c;
        } else if (h >= 300 && h < 360) {
            rPrime = c;
            gPrime = 0;
            bPrime = x;
        }

        int r = (int) ((rPrime + m) * 255);
        int g = (int) ((gPrime + m) * 255);
        int b = (int) ((bPrime + m) * 255);

        return new int[]{r, g, b};
    }


}