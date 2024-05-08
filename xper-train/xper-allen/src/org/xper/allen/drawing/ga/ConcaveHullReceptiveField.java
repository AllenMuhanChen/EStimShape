package org.xper.allen.drawing.ga;

import org.xper.allen.drawing.composition.noisy.ConcaveHull;
import org.xper.drawing.Coordinates2D;

import java.util.ArrayList;
import java.util.List;

public class ConcaveHullReceptiveField extends ReceptiveField {


    private ArrayList<ConcaveHull.Point> concaveHullPoints = new ArrayList<>();

    public ConcaveHullReceptiveField(List<Coordinates2D> hullPointsAsCoords) {
        this.outline = hullPointsAsCoords;
        System.out.println("Outline setter called: " + this.outline.size());
        for (Coordinates2D point : hullPointsAsCoords) {
            concaveHullPoints.add(new ConcaveHull.Point(point.getX(), point.getY()));
        }
    }

    @Override
    public boolean isInRF(double x, double y) {
        return ConcaveHull.pointInPolygon(new ConcaveHull.Point(x,y), concaveHullPoints);
    }


}