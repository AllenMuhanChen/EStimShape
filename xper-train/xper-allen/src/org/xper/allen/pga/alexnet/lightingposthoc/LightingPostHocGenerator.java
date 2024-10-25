package org.xper.allen.pga.alexnet.lightingposthoc;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.allen.pga.alexnet.AlexNetDrawingManager;
import org.xper.allen.util.MultiGaDbUtil;

public class LightingPostHocGenerator extends AbstractTrialGenerator<Stim> {
    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    protected String generatorPngPath;

    @Dependency
    protected String generatorSpecPath;

    @Dependency
    AlexNetDrawingManager drawingManager;

    @Override
    protected void addTrials() {
        //read StimInstruction

        //check if stim has an entry in StimPath

        //if not:

        //if type is TEXTURE_3D_VARIATION
            //Generate stimuli using instructions and save to StimSpec and StimPath

        //if type is 2D
            // Generate using new contrast and 2D instructions


    }

    @Override
    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public String getGeneratorPngPath() {
        return generatorPngPath;
    }

    public void setGeneratorPngPath(String generatorPngPath) {
        this.generatorPngPath = generatorPngPath;
    }

    public String getGeneratorSpecPath() {
        return generatorSpecPath;
    }

    public void setGeneratorSpecPath(String generatorSpecPath) {
        this.generatorSpecPath = generatorSpecPath;
    }

    public AlexNetDrawingManager getDrawingManager() {
        return drawingManager;
    }

    public void setDrawingManager(AlexNetDrawingManager drawingManager) {
        this.drawingManager = drawingManager;
    }
}