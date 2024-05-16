package org.xper.allen.drawing.ga;

import org.xper.drawing.Coordinates2D;

import java.util.List;
import java.util.Random;

public class RandomPointInConvexPolygon {
    private static Random random = new Random();

    public static Coordinates2D generateRandomPoint(List<Coordinates2D> vertices) {
        // First, triangulate the convex polygon
        int n = vertices.size();
        double totalArea = 0;
        double[] areaCumulative = new double[n - 2];

        for (int i = 1; i < n - 1; i++) {
            double area = triangleArea(vertices.get(0), vertices.get(i), vertices.get(i + 1));
            totalArea += area;
            areaCumulative[i - 1] = totalArea;
        }

        // Randomly select a triangle weighted by its area
        double r = random.nextDouble() * totalArea;
        int selectedTriangle = 0;
        for (int i = 0; i < n - 2; i++) {
            if (r < areaCumulative[i]) {
                selectedTriangle = i;
                break;
            }
        }

        // Generate a random point in the selected triangle
        return randomPointInTriangle(vertices.get(0), vertices.get(selectedTriangle + 1), vertices.get(selectedTriangle + 2));
    }

    private static double triangleArea(Coordinates2D a, Coordinates2D b, Coordinates2D c) {
        return Math.abs(a.getX() * (b.getY() - c.getY()) + b.getX() * (c.getY() - a.getY()) + c.getX() * (a.getY() - b.getY())) / 2.0;
    }

    private static Coordinates2D randomPointInTriangle(Coordinates2D a, Coordinates2D b, Coordinates2D c) {
        double r1 = random.nextDouble();
        double r2 = random.nextDouble();
        double sqrtR1 = Math.sqrt(r1);
        double x = (1 - sqrtR1) * a.getX() + (sqrtR1 * (1 - r2)) * b.getX() + (sqrtR1 * r2) * c.getX();
        double y = (1 - sqrtR1) * a.getY() + (sqrtR1 * (1 - r2)) * b.getY() + (sqrtR1 * r2) * c.getY();
        return new Coordinates2D(x, y);
    }


}