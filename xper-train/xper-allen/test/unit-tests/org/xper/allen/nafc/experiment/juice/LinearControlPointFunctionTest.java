package org.xper.allen.nafc.experiment.juice;

import org.apache.commons.math.FunctionEvaluationException;
import org.junit.Test;

import java.util.Arrays;
import java.util.List;

import static org.junit.Assert.*;

public class LinearControlPointFunctionTest {

    @Test
    public void value() throws FunctionEvaluationException {
        List<Double> x = Arrays.asList(0.0, 0.3, 0.5, 1.0);
        List<Double> y = Arrays.asList(1.0, 2.0, 3.0, 4.0);
        LinearControlPointFunction f = new LinearControlPointFunction();
        f.setxValues(x);
        f.setyValues(y);

        //Test Interpolation
        assertEquals(1.0, f.value(0.0), 0.0001);
        assertEquals(1.5, f.value(0.15), 0.0001);
        assertEquals(2.0, f.value(0.3), 0.0001);
        assertEquals(2.5, f.value(0.4), 0.0001);
        assertEquals(3.0, f.value(0.5), 0.0001);
        assertEquals(3.5, f.value(0.75), 0.0001);
        assertEquals(4.0, f.value(1.0), 0.0001);

        //Test out of bounds
        assertEquals(1.0, f.value(-1), 0.0001);
        assertEquals(4.0, f.value(1.5), 0.0001);
    }
}