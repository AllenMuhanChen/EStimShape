package org.xper.allen.nafc.experiment.bias;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import java.util.Arrays;
import java.util.List;

import org.junit.Test;

/**
 * Spec for the DB-free mapping in {@link LineageResolver} (the port of classify_choice_path /
 * reconstruct_picked_lineage_id). The DB-backed {@code resolve} path is exercised by integration
 * testing against a real experiment/GA database.
 */
public class LineageResolverTest {

    @Test
    public void classifyUsesFilenameTag_withDeltaDistractorBeforeDelta() {
        assertEquals("match", LineageResolver.classifyChoicePath("/x/123_match.png"));
        assertEquals("delta", LineageResolver.classifyChoicePath("/x/123_delta.png"));
        // "_delta" is a substring of "_delta_distractor": the more specific tag must win.
        assertEquals("delta_distractor", LineageResolver.classifyChoicePath("/x/123_delta_distractor.png"));
        assertEquals("rand", LineageResolver.classifyChoicePath("/x/123_rand.png"));
        assertEquals("removed", LineageResolver.classifyChoicePath("/x/123_removed.png"));
        assertEquals("variant", LineageResolver.classifyChoicePath("/x/123_variant.png"));
        assertEquals("textureFoil", LineageResolver.classifyChoicePath("/x/123_textureFoil.png"));
        assertEquals("None", LineageResolver.classifyChoicePath("/x/123_sample.png"));
        assertEquals("None", LineageResolver.classifyChoicePath(null));
    }

    @Test
    public void variantSampleTrial_mapsMatchAndDeltasInOrder() {
        // Variant is the sample; its two included deltas are the lineage distractors, in order.
        List<String> categories = Arrays.asList("match", "delta", "delta", "rand");
        List<Long> distractorOrder = Arrays.asList(101L, 102L); // included deltas of variant 100
        long sampleId = 100L;

        assertEquals(Long.valueOf(100L), LineageResolver.reconstructPickedLineageId(categories, 0, sampleId, distractorOrder));
        assertEquals(Long.valueOf(101L), LineageResolver.reconstructPickedLineageId(categories, 1, sampleId, distractorOrder));
        assertEquals(Long.valueOf(102L), LineageResolver.reconstructPickedLineageId(categories, 2, sampleId, distractorOrder));
        // A rand pick is not a lineage member.
        assertNull(LineageResolver.reconstructPickedLineageId(categories, 3, sampleId, distractorOrder));
    }

    @Test
    public void deltaSampleTrial_mapsVariantFirstThenOtherDeltas() {
        // A delta is the sample; distractors are [variant, other delta], labeled delta / delta_distractor.
        List<String> categories = Arrays.asList("match", "delta", "delta_distractor");
        List<Long> distractorOrder = Arrays.asList(100L, 102L); // [variant, other delta]
        long sampleId = 101L;

        assertEquals(Long.valueOf(101L), LineageResolver.reconstructPickedLineageId(categories, 0, sampleId, distractorOrder));
        assertEquals(Long.valueOf(100L), LineageResolver.reconstructPickedLineageId(categories, 1, sampleId, distractorOrder));
        assertEquals(Long.valueOf(102L), LineageResolver.reconstructPickedLineageId(categories, 2, sampleId, distractorOrder));
    }

    @Test
    public void nonLineagePicksAndOutOfRangeReturnNull() {
        List<String> categories = Arrays.asList("match", "procedural", "removed");
        List<Long> distractorOrder = Arrays.asList(101L);
        assertNull(LineageResolver.reconstructPickedLineageId(categories, 1, 100L, distractorOrder));
        assertNull(LineageResolver.reconstructPickedLineageId(categories, 2, 100L, distractorOrder));
        assertNull(LineageResolver.reconstructPickedLineageId(categories, -1, 100L, distractorOrder));
        assertNull(LineageResolver.reconstructPickedLineageId(categories, 5, 100L, distractorOrder));
    }
}
