package org.xper.allen.app.procedural;

import java.awt.*;
import java.util.ArrayList;
import java.util.List;

public class RadialSquares {

    public static void main(String[] args) {
        int numberOfSquares = 8; // Example number of squares
        double squareSize = 10;  // Example size of the squares
        double gap = 5;          // Example gap between enclosing circles

        double requiredRadius = calculateRequiredRadius(numberOfSquares, squareSize, gap);

        System.out.println("Required radius to position the squares without overlap and with the specified gap: " + requiredRadius);
    }

    /**
     * Calculates the required radius to position the squares without overlap and with the specified gap.
     * @param numberOfSquares
     * @param squareSize
     * @param gap
     * @return
     */
    public static double calculateRequiredRadius(int numberOfSquares, double squareSize, double gap) {
        double halfDiagonal = Math.sqrt(2) * squareSize / 2;
        double radiusWithGap = halfDiagonal + gap;
        double angleBetweenSquares = 2 * Math.PI / numberOfSquares;

        // Ensuring no overlap and considering the gap
        double requiredRadius = radiusWithGap / Math.sin(angleBetweenSquares / 2);
        return requiredRadius;
    }
}