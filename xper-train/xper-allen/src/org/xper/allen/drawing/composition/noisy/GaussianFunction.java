package org.xper.allen.drawing.composition.noisy;

public class GaussianFunction {

    /**
     * Computes the 2D Gaussian value at point (x,y).
     *
     * @param x       X-coordinate where the Gaussian value is computed.
     * @param y       Y-coordinate where the Gaussian value is computed.
     * @param x0      X-coordinate of the center of the Gaussian.
     * @param y0      Y-coordinate of the center of the Gaussian.
     * @param sigmaX  Standard deviation in the x direction.
     * @param sigmaY  Standard deviation in the y direction.
     * @param amplitude Peak value of the Gaussian.
     * @return Gaussian value at point (x,y).
     */
    public static double compute2DGaussian(double x, double y, double x0, double y0,
                                           double sigmaX, double sigmaY, double amplitude) {
        double gaussX = Math.exp(-0.5 * Math.pow((x - x0) / sigmaX, 2));
        double gaussY = Math.exp(-0.5 * Math.pow((y - y0) / sigmaY, 2));
        return amplitude * gaussX * gaussY;
    }
}