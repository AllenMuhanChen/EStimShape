package org.xper.allen.isoluminant;

import org.lwjgl.opengl.GL11;
import org.xper.allen.monitorlinearization.LookUpTableCorrector;
import org.xper.allen.monitorlinearization.SinusoidGainCorrector;
import org.xper.drawing.Context;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.gabor.Gabor;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

public class IsoluminantGabor extends Gabor {

    IsoGaborSpec spec;
    double luminanceCandela;
    private LookUpTableCorrector lutCorrector;
    private SinusoidGainCorrector sinusoidGainCorrector;

    public IsoluminantGabor(IsoGaborSpec spec, double luminanceCandela, LookUpTableCorrector lutCorrector, SinusoidGainCorrector sinusoidGainCorrector) {
        this.spec = spec;
        this.luminanceCandela = luminanceCandela;
        this.lutCorrector = lutCorrector;
        this.sinusoidGainCorrector = sinusoidGainCorrector;
    }

    @Override
    protected float[] modulateColor(float modFactor) {
        // Ensure modFactor is within 0 and 1
        modFactor = Math.max(0, Math.min(modFactor, 1));

        // get an angle of cosine out of the modFactor
        double angle = modFactor * 180;

        double gain;
        RGBColor corrected;
        if (spec.type.equals("RedGreen")) {
            double luminanceRed = luminanceCandela * (1 + Math.cos(Math.toRadians(angle)))/2;
            double luminanceGreen = luminanceCandela * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            gain = sinusoidGainCorrector.getGain(angle, "RedGreen");
            corrected = lutCorrector.correctRedGreen(luminanceRed * gain, luminanceGreen * gain);
        }
        else {
            throw new RuntimeException("Unknown color space: " + spec.type);
        }
        return new float[]{corrected.getRed(), corrected.getGreen(), corrected.getBlue()};
    }

    protected void initTexture(Context context) {
        double diameterDeg = getGaborSpec().getSize(); // Gabor patch diameter in degrees of visual angle
        double diameterMm = context.getRenderer().deg2mm(diameterDeg); // Convert diameter from degrees to millimeters

        // Calculate the fraction of the viewport width occupied by the Gabor patch in mm
        double viewportWidthMm = context.getRenderer().getVpWidthmm(); // Viewport width in millimeters
        double fractionOfViewportWidthMm = diameterMm / viewportWidthMm;

        // Since the normalized coordinate system spans 2 units (-1 to 1), calculate the normalized diameter
        double normalizedDiameter = fractionOfViewportWidthMm;

        // Specify the percentage of the diameter where the fade strength should be 3 sigmas
        double fadePercentOfDiameter = 0.5;

        // Calculate the number of sigmas based on the specified percentage of diameter
        int nSigmas = (int) Math.ceil(2 / (2 * fadePercentOfDiameter));

        // Calculate sigma as a fraction of the normalized diameter, divided by the desired number of sigmas
        // Here, sigma represents the spread of the Gaussian in terms of the normalized coordinate system
        double normalizedSigma = (normalizedDiameter / 2) / nSigmas;

        ByteBuffer texture = makeTexture(w, h, normalizedDiameter, normalizedSigma); // Adjust w, h, std as needed
        textureId = GL11.glGenTextures(); // Generate texture ID
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, textureId);

        GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 1);
        GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_ALPHA, w, h, 0, GL11.GL_ALPHA, GL11.GL_FLOAT, texture);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL11.GL_CLAMP);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL11.GL_CLAMP);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
        GL11.glTexEnvf(GL11.GL_TEXTURE_ENV, GL11.GL_TEXTURE_ENV_MODE, GL11.GL_MODULATE);
    }

    @Override
    public IsoGaborSpec getGaborSpec() {
        return spec;
    }

    public void setGaborSpec(IsoGaborSpec spec) {
        this.spec = spec;
    }

    @Override
    public void setDefaultSpec() {
    }

    /**
     *
     * @param w
     * @param h
     * @param diskDiameter, 0-1
     * @param std
     * @return
     */
    protected ByteBuffer makeTexture(int w, int h, double diskDiameter, double std) {
        ByteBuffer texture = ByteBuffer.allocateDirect(w * h * Float.SIZE / 8).order(ByteOrder.nativeOrder());
        double aspectRatio = (double) w / h;
        double circleRadius = diskDiameter/4; // Specify the radius of the disk where the texture is shown normally
        //we divide by four because one division by two converts to radius,
        //and another because the coordinate system we use here is -1 to 1, but the diameter
        //is specified as 0-1. So we divide by 2 to get the radius in the -1 to 1 coordinate system.

        double diskAlpha = 1.0; // Specify the alpha level within the disk
        double background = 0.0; // Specify the background intensity

        for (int i = 0; i < h; i++) {
            double y = ((double) i / (h - 1) * 2 - 1) / aspectRatio; // Adjust y-coordinate by aspect ratio
            for (int j = 0; j < w; j++) {
                double x = ((double) j / (w - 1) * 2 - 1);
                double distanceToCenter = Math.sqrt(x * x + y * y);

                float n;

                if (distanceToCenter <= circleRadius) {
                    // Within the disk
                    n = (float) diskAlpha;
                } else {
                    // Calculate Gaussian fade from the disk's edge
                    double offsetDistance = distanceToCenter - circleRadius;
                    double gaussValue = diskAlpha * Math.exp(-0.5 * (Math.pow(offsetDistance / std, 2)));
                    n = (float) Math.min(gaussValue, 1.0);
                }

                texture.putFloat(n);
            }
        }
        texture.flip();
        return texture;
    }


    public String getSpec() {
        return getGaborSpec().toXml();
    }

    public RGBColor getBackGroundColor() {
        double angle = 90;
        double gain;
        RGBColor corrected;
        if (spec.type.equals("RedGreen")) {
            double luminanceRed = luminanceCandela * (1 + Math.cos(Math.toRadians(angle)))/2;
            double luminanceGreen = luminanceCandela * (1 + Math.cos(Math.toRadians(angle-180)))/2;
            gain = sinusoidGainCorrector.getGain(angle, "RedGreen");
            corrected = lutCorrector.correctRedGreen(luminanceRed * gain, luminanceGreen * gain);
        }
        else {
            throw new RuntimeException("Unknown color space: " + spec.type);
        }
        return corrected;
    }
}