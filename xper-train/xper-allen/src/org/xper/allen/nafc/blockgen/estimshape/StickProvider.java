package org.xper.allen.nafc.blockgen.estimshape;

import org.xper.allen.drawing.composition.AllenMatchStick;

public interface StickProvider<T extends AllenMatchStick> {

    public T makeStick();
}