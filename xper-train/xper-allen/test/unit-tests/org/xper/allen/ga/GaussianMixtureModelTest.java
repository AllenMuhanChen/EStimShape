package org.xper.allen.ga;

import org.apache.commons.math3.analysis.BivariateFunction;
import org.junit.Ignore;
import org.junit.Test;
import org.xper.util.ThreadUtil;

import javax.swing.*;
import java.awt.*;
import java.awt.geom.Point2D;
import java.awt.geom.Rectangle2D;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.List;

public class GaussianMixtureModelTest {

    @Test
    @Ignore
    public void testGaussianMixtureModel() {
        List<Point2D> controlPoints = new ArrayList<Point2D>();
        controlPoints.add(new Point2D.Double(0, 0));
        controlPoints.add(new Point2D.Double(0.5, 0.5));
        controlPoints.add(new Point2D.Double(1, 1));


        List<Double> sigmas = new ArrayList<Double>();
        sigmas.add(radiusToSigma(0.5));
        sigmas.add(radiusToSigma(0.3));
        sigmas.add(radiusToSigma(0.2));

        List<Double> values = new ArrayList<Double>();
        values.add(1.0);
        values.add(1.0);
        values.add(1.0);

        GaussianMixtureModel gmm = new GaussianMixtureModel(controlPoints, values, sigmas);

        // Draw the Gaussian mixture model
        drawGaussianMixtureModel(gmm, 0, 1, 0, 1, 300, 300);

        ThreadUtil.sleep(100000);
    }

    private double radiusToSigma(double radius) {
        return radius / 2;
    }

    public void drawGaussianMixtureModel(BivariateFunction gmm, double xMin, double xMax, double yMin, double yMax, int width, int height) {
        // Create a new image buffer and graphics context
        BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
        Graphics2D g2d = image.createGraphics();
        g2d.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g2d.setBackground(Color.WHITE);
        g2d.clearRect(0, 0, width, height);

        // Draw the Gaussian mixture model
        double dx = (xMax - xMin) / (width - 1);
        double dy = (yMax - yMin) / (height - 1);
        double max = Double.MIN_VALUE;
        double min = Double.MAX_VALUE;
        for (int i = 0; i < width; i++) {
            double x = xMin + i * dx;
            for (int j = 0; j < height; j++) {
                double y = yMin + j * dy;
                double value = gmm.value(x, y);
                max = Math.max(max, value);
                min = Math.min(min, value);
            }
        }
        double range = max - min;
        for (int i = 0; i < width; i++) {
            double x = xMin + i * dx;
            for (int j = 0; j < height; j++) {
                double y = yMin + j * dy;
                double value = gmm.value(x, y);
                int colorValue = (int) (255.0 * (value - min) / range);
                colorValue = Math.max(0, Math.min(255, colorValue));
                Color color = new Color(colorValue, colorValue, colorValue);
                g2d.setColor(color);
                g2d.fill(new Rectangle2D.Double(i, height - j - 1, 1, 1));
            }
        }

        // Show the image in a window
        JFrame frame = new JFrame("Gaussian Mixture Model");
        frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
        JLabel label = new JLabel(new ImageIcon(image));
        frame.getContentPane().add(label);
        frame.pack();
        frame.setLocationRelativeTo(null);
        frame.setVisible(true);
    }
}