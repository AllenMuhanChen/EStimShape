package org.xper.allen.nafc.blockgen.procedural;

import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;

import javax.swing.*;

/**
 * "Split texture" variant/delta NAFC trials: the hypothesized limb of the shape is rendered
 * in a contrasting texture, and an extra same-geometry "texture-foil" distractor occupies one
 * procedural choice slot (see {@link SplitTextureConfig} and the rendering in
 * {@link EStimShapeProceduralStim}).
 *
 * <p>This reuses {@link EStimExperimentVariantOrDeltaGenType} for everything about trial
 * assembly — including the {@code isDelta} variant/delta split and the {@code -1 = one rep of
 * every variant/delta} expansion — and only layers the split-texture rendering config on top.
 * Configure two beans with {@code setDelta(false)} / {@code setDelta(true)} to get
 * VariantSplitTexture / DeltaSplitTexture; the {@code splitRenderIsSample},
 * {@code invertedShading} and {@code contrastTexture} GUI fields let you control the rest per
 * block (e.g. add two blocks with opposite {@code splitRenderIsSample} to balance the ratio).
 */
public class EStimExperimentSplitTextureGenType extends EStimExperimentVariantOrDeltaGenType {

    protected JTextField splitRenderIsSampleField;
    protected JTextField invertedShadingField;
    protected JTextField contrastTextureField;

    /** Config for the block currently being generated; set at the start of {@link #readFromFields()}. */
    private SplitTextureConfig currentConfig = new SplitTextureConfig(null, false, true);

    @Override
    public String getLabel() {
        return isDelta() ? "EStimExperimentDeltaSplitTexture" : "EStimExperimentVariantSplitTexture";
    }

    @Override
    public EStimExperimentGenType.EStimExperimentGenParameters readFromFields() {
        EStimExperimentGenType.EStimExperimentGenParameters params = super.readFromFields();
        params.splitRenderIsSample = Boolean.parseBoolean(splitRenderIsSampleField.getText());
        params.invertedShading = Boolean.parseBoolean(invertedShadingField.getText());
        params.contrastTexture = contrastTextureField.getText();
        currentConfig = new SplitTextureConfig(
                params.contrastTexture, params.invertedShading, params.splitRenderIsSample);
        return params;
    }

    @Override
    protected EStimShapeVariantsNAFCStim createVariantOnlyStim(EStimShapeExperimentTrialGenerator generator,
            ProceduralStim.ProceduralStimParameters parameters, long variantId, boolean isEStimEnabled, Long eStimSpecId) {
        return new EStimShapeSplitTextureNAFCStim(generator, parameters, variantId, false, isEStimEnabled, eStimSpecId, currentConfig);
    }

    @Override
    protected EStimShapeVariantsNAFCStim createDeltaOnlyStim(EStimShapeExperimentTrialGenerator generator,
            ProceduralStim.ProceduralStimParameters parameters, long variantId, long sampleDeltaId, boolean isEStimEnabled, Long eStimSpecId) {
        return new EStimShapeSplitTextureNAFCStim(generator, parameters, variantId, Long.valueOf(sampleDeltaId), isEStimEnabled, eStimSpecId, currentConfig);
    }

    @Override
    public void initFields() {
        super.initFields();
        splitRenderIsSampleField = new JTextField("true", 10);
        invertedShadingField = new JTextField("false", 10);
        contrastTextureField = new JTextField(SplitTextureConfig.DEFAULT_CONTRAST_TEXTURE, 10);

        labelsForFields.put(splitRenderIsSampleField, "splitRenderIsSample (true/false):");
        defaultsForFields.put(splitRenderIsSampleField, "true");
        labelsForFields.put(invertedShadingField, "invertedShading (true/false):");
        defaultsForFields.put(invertedShadingField, "false");
        labelsForFields.put(contrastTextureField, "contrastTexture:");
        defaultsForFields.put(contrastTextureField, SplitTextureConfig.DEFAULT_CONTRAST_TEXTURE);
    }

    @Override
    public void loadParametersIntoFields(GenParameters blockParams) {
        super.loadParametersIntoFields(blockParams);
        EStimExperimentGenType.EStimExperimentGenParameters p =
                (EStimExperimentGenType.EStimExperimentGenParameters) blockParams;
        splitRenderIsSampleField.setText(String.valueOf(p.splitRenderIsSample));
        invertedShadingField.setText(String.valueOf(p.invertedShading));
        contrastTextureField.setText(
                (p.contrastTexture == null || p.contrastTexture.isEmpty())
                        ? SplitTextureConfig.DEFAULT_CONTRAST_TEXTURE : p.contrastTexture);
    }

    @Override
    public String getInfo() {
        return super.getInfo() +
                ", splitRenderIsSample: " + splitRenderIsSampleField.getText() +
                ", invertedShading: " + invertedShadingField.getText() +
                ", contrastTexture: " + contrastTextureField.getText();
    }

    @Override
    public String getInfo(GenParameters params) {
        String base = super.getInfo(params);
        if (params instanceof EStimExperimentGenType.EStimExperimentGenParameters) {
            EStimExperimentGenType.EStimExperimentGenParameters p =
                    (EStimExperimentGenType.EStimExperimentGenParameters) params;
            return base +
                    ", splitRenderIsSample: " + p.splitRenderIsSample +
                    ", invertedShading: " + p.invertedShading +
                    ", contrastTexture: " + p.contrastTexture;
        }
        return base;
    }
}
