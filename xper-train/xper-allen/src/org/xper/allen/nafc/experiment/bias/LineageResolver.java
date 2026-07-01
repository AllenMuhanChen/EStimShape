package org.xper.allen.nafc.experiment.bias;

import java.util.ArrayList;
import java.util.List;

import javax.sql.DataSource;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.allen.specs.NoisyPngSpec;

/**
 * Resolves a completed NAFC trial's choices to lineage ids (variant id / delta id), so the
 * {@link BiasTracker} can measure bias per stimulus. This is the runtime Java counterpart of the
 * Python analysis reconstruction (PickedBaseMStickIdField / reconstruct_picked_lineage_id in
 * nafc_database_fields.py) and must stay in step with it.
 *
 * <p>Data sources: the trial's choice PNG paths come from the in-memory task (no DB), the sample's
 * lineage id and per-trial role come from the experiment DB (BaseMStickId, NafcSampleRole), and the
 * variant&rarr;delta membership/order comes from the GA DB (IncludedDeltas). Any failure degrades to
 * an {@link TrialLineage#unresolved()} result rather than throwing, so one odd trial never disrupts
 * the experiment.
 */
public class LineageResolver {

    private final JdbcTemplate experimentDb;
    private final JdbcTemplate gaDb;
    private Boolean sampleRoleExists;

    public LineageResolver(DataSource experimentDataSource, DataSource gaDataSource) {
        this.experimentDb = new JdbcTemplate(experimentDataSource);
        this.gaDb = new JdbcTemplate(gaDataSource);
    }

    /** Resolve one trial given the animal's selection index (0-based into the choice list). */
    public TrialLineage resolve(NAFCExperimentTask task, int selection) {
        try {
            String[] choiceSpecs = task.getChoiceSpec();
            if (choiceSpecs == null || choiceSpecs.length == 0) {
                return TrialLineage.unresolved();
            }
            int numChoices = choiceSpecs.length;

            List<String> categories = new ArrayList<>(numChoices);
            for (String choiceSpec : choiceSpecs) {
                categories.add(classifyChoicePath(pngPathOrNull(choiceSpec)));
            }

            long trialStimId = task.getStimId();
            Long sampleId = nullableLong(experimentDb,
                    "SELECT base_mstick_stim_spec_id FROM BaseMStickId WHERE stim_id = ? LIMIT 1",
                    trialStimId);
            if (sampleId == null) {
                return TrialLineage.unresolved();
            }

            Boolean isDelta = resolveIsDelta(trialStimId, sampleId);
            if (isDelta == null) {
                return TrialLineage.unresolved();
            }
            Long variantId = resolveVariantId(trialStimId, sampleId, isDelta);
            if (variantId == null) {
                return TrialLineage.unresolved();
            }

            List<Long> distractorOrder = distractorLineageOrder(variantId, sampleId, isDelta);

            // Present lineage members = the sample (the "match" choice) plus each lineage-distractor
            // choice mapped, in order, onto the generator's distractor list.
            List<Long> presentIds = new ArrayList<>();
            presentIds.add(sampleId);
            int k = 0;
            for (String category : categories) {
                if (isLineageDistractor(category)) {
                    if (k < distractorOrder.size()) {
                        presentIds.add(distractorOrder.get(k));
                    }
                    k++;
                }
            }

            Long chosenId = reconstructPickedLineageId(categories, selection, sampleId, distractorOrder);
            return TrialLineage.resolved(variantId, sampleId, chosenId, presentIds, numChoices);
        } catch (Exception e) {
            return TrialLineage.unresolved();
        }
    }

    /** Distractor lineage ids in the generator's slot order (mirrors _distractor_lineage_order). */
    private List<Long> distractorLineageOrder(long variantId, long sampleId, boolean isDelta) {
        List<Long> included = gaDb.queryForList(
                "SELECT delta_id FROM IncludedDeltas WHERE variant_id = ? AND included = 1",
                Long.class, variantId);
        if (!isDelta) {
            // Variant-sample trial: distractors are the variant's included deltas, in order.
            return included;
        }
        // Delta-sample trial: distractors are [variant, then the other included deltas].
        List<Long> order = new ArrayList<>(included.size() + 1);
        order.add(variantId);
        for (Long d : included) {
            if (!d.equals(sampleId)) {
                order.add(d);
            }
        }
        return order;
    }

    private Boolean resolveIsDelta(long trialStimId, long sampleId) {
        if (hasSampleRoleTable()) {
            Long role = nullableLong(experimentDb,
                    "SELECT is_sample_delta FROM NafcSampleRole WHERE stim_id = ? LIMIT 1", trialStimId);
            if (role != null) {
                return role != 0L;
            }
        }
        // Fallback via global IncludedDeltas membership (unambiguous pre-delta->delta-chain data).
        if (nullableLong(gaDb,
                "SELECT delta_id FROM IncludedDeltas WHERE delta_id = ? AND included = 1 LIMIT 1",
                sampleId) != null) {
            return true;
        }
        if (nullableLong(gaDb,
                "SELECT variant_id FROM IncludedDeltas WHERE variant_id = ? AND included = 1 LIMIT 1",
                sampleId) != null) {
            return false;
        }
        return null;
    }

    private Long resolveVariantId(long trialStimId, long sampleId, boolean isDelta) {
        if (hasSampleRoleTable()) {
            Long variantId = nullableLong(experimentDb,
                    "SELECT variant_id FROM NafcSampleRole WHERE stim_id = ? LIMIT 1", trialStimId);
            if (variantId != null) {
                return variantId;
            }
        }
        if (!isDelta) {
            return sampleId; // the sample IS the variant
        }
        return nullableLong(gaDb,
                "SELECT variant_id FROM IncludedDeltas WHERE delta_id = ? AND included = 1 LIMIT 1",
                sampleId);
    }

    private boolean hasSampleRoleTable() {
        if (sampleRoleExists == null) {
            try {
                List<String> tables = experimentDb.query("SHOW TABLES LIKE 'NafcSampleRole'",
                        (rs, rowNum) -> rs.getString(1));
                sampleRoleExists = !tables.isEmpty();
            } catch (Exception e) {
                sampleRoleExists = Boolean.FALSE;
            }
        }
        return sampleRoleExists;
    }

    private static Long nullableLong(JdbcTemplate db, String sql, Object... args) {
        List<Long> results = db.queryForList(sql, Long.class, args);
        return results.isEmpty() ? null : results.get(0);
    }

    private static String pngPathOrNull(String choiceSpecXml) {
        try {
            return NoisyPngSpec.fromXml(choiceSpecXml).getPngPath();
        } catch (Exception e) {
            return null;
        }
    }

    // ---- Pure, DB-free mapping (mirrors classify_choice_path / reconstruct_picked_lineage_id) ----

    /** Category of a choice from the tag the generator appended to its PNG filename. */
    public static String classifyChoicePath(String choicePath) {
        if (choicePath == null) {
            return "None";
        }
        if (choicePath.contains("_match")) {
            return "match";
        } else if (choicePath.contains("_textureFoil")) {
            return "textureFoil";
        } else if (choicePath.contains("_procedural")) {
            return "procedural";
        } else if (choicePath.contains("_variant")) {
            return "variant";
        } else if (choicePath.contains("_removed")) {
            return "removed";
        } else if (choicePath.contains("_delta_distractor")) {
            // Must precede "_delta": "_delta" is a substring of "_delta_distractor".
            return "delta_distractor";
        } else if (choicePath.contains("_delta")) {
            return "delta";
        } else if (choicePath.contains("_rand")) {
            return "rand";
        }
        return "None";
    }

    /**
     * Map a trial's choice layout to the lineage id of the picked shape. A "match" pick is the sample;
     * a delta-category pick is the k-th lineage distractor, where k is its rank among the trial's
     * delta-category choices in choice order. Returns null when the pick is not a plain lineage member
     * or the layout can't be mapped.
     */
    public static Long reconstructPickedLineageId(List<String> categories, int pickedIndex,
                                                  long sampleId, List<Long> distractorOrder) {
        if (pickedIndex < 0 || pickedIndex >= categories.size()) {
            return null;
        }
        String pickedCategory = categories.get(pickedIndex);
        if ("match".equals(pickedCategory)) {
            return sampleId;
        }
        if (!isLineageDistractor(pickedCategory) || distractorOrder == null) {
            return null;
        }
        int k = 0;
        for (int i = 0; i < pickedIndex; i++) {
            if (isLineageDistractor(categories.get(i))) {
                k++;
            }
        }
        if (k >= distractorOrder.size()) {
            return null;
        }
        return distractorOrder.get(k);
    }

    private static boolean isLineageDistractor(String category) {
        return "delta".equals(category) || "delta_distractor".equals(category);
    }
}
