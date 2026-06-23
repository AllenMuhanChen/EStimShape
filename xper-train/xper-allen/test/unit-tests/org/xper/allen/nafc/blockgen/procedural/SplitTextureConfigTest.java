package org.xper.allen.nafc.blockgen.procedural;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class SplitTextureConfigTest {

    @Test
    public void normalModeBodyIsOriginalLimbIsContrast() {
        SplitTextureConfig config = new SplitTextureConfig("2D", false, true);
        assertEquals("SPECULAR", config.bodyTexture("SPECULAR"));
        assertEquals("2D", config.splitLimbTexture("SPECULAR"));
        assertEquals("SHADE", config.bodyTexture("SHADE"));
        assertEquals("2D", config.splitLimbTexture("SHADE"));
    }

    @Test
    public void invertedModeBodyIsContrastLimbIsOriginal() {
        SplitTextureConfig config = new SplitTextureConfig("2D", true, true);
        assertEquals("2D", config.bodyTexture("SPECULAR"));
        assertEquals("SPECULAR", config.splitLimbTexture("SPECULAR"));
    }

    @Test
    public void splitRenderIsSampleTrue_sampleAndMatchSplit_foilPlain() {
        SplitTextureConfig config = new SplitTextureConfig("2D", false, true);
        assertTrue(config.sampleIsSplit());
        assertTrue(config.matchIsSplit());
        assertFalse(config.foilIsSplit());
    }

    @Test
    public void splitRenderIsSampleFalse_sampleAndMatchPlain_foilSplit() {
        SplitTextureConfig config = new SplitTextureConfig("2D", false, false);
        assertFalse(config.sampleIsSplit());
        assertFalse(config.matchIsSplit());
        assertTrue(config.foilIsSplit());
    }

    @Test
    public void sampleAndMatchAlwaysShareTreatment() {
        for (boolean inverted : new boolean[]{false, true}) {
            for (boolean splitIsSample : new boolean[]{false, true}) {
                SplitTextureConfig config = new SplitTextureConfig("2D", inverted, splitIsSample);
                assertEquals("sample and match must match (inverted=" + inverted + ", splitIsSample=" + splitIsSample + ")",
                        config.sampleIsSplit(), config.matchIsSplit());
                assertEquals("foil must be the opposite of the match",
                        !config.matchIsSplit(), config.foilIsSplit());
            }
        }
    }

    @Test
    public void nullOrEmptyContrastDefaultsTo2D() {
        assertEquals("2D", new SplitTextureConfig(null, false, true).getContrastTexture());
        assertEquals("2D", new SplitTextureConfig("", false, true).getContrastTexture());
        assertEquals("SHADE", new SplitTextureConfig("SHADE", false, true).getContrastTexture());
    }
}
