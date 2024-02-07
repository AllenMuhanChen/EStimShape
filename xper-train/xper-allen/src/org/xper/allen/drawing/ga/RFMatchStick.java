package org.xper.allen.drawing.ga;

import org.xper.allen.drawing.composition.morph.MorphedMatchStick;

import javax.vecmath.Point3d;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.function.Predicate;

public class RFMatchStick extends MorphedMatchStick {
    ReceptiveField rf;
    double thresholdPercentageInRF = .1;

    public RFMatchStick(ReceptiveField rf) {
        this.rf = rf;
    }

    public RFMatchStick() {
    }

    @Override
    protected boolean checkMStick() {
        if (rf != null)
            return checkInRF(thresholdPercentageInRF);
        else{
            return true;
        }
    }

    private boolean checkInRF(double thresholdPercentageInRF) {
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsInside = new ArrayList<>();

//        for (int i=1; i<=this.getnComponent(); i++){
//            pointsToCheck.addAll(Arrays.asList(this.getComp()[i].getVect_info()));
//        }
        pointsToCheck.addAll(Arrays.asList(this.getObj1().vect_info));
        pointsToCheck.removeIf(new Predicate<Point3d>() {
            @Override
            public boolean test(Point3d point) {
                return point == null;
            }
        });

        for (Point3d point: pointsToCheck){
            if (rf.isInRF(point.x, point.y)) {
                pointsInside.add(point);
            }
        }

        double percentageInRF = (double) pointsInside.size() / pointsToCheck.size();
        System.out.println("Percentage in RF: " + percentageInRF + " Threshold: " + thresholdPercentageInRF);
        return percentageInRF > thresholdPercentageInRF;
    }



}