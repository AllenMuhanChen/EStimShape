package org.xper.allen.drawing.composition;

import org.junit.Test;

import static org.junit.Assert.*;

public class AllenMStickDataTest {

    @Test
    public void AllenMStickSpecGeneratesData() {
       AllenMatchStick matchStick = new AllenMatchStick();
       matchStick.genMatchStickRand();


       AllenMStickData data = new AllenMStickData();
       data.setMStickData(matchStick);



    }
}