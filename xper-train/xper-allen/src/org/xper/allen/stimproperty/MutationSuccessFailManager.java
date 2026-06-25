package org.xper.allen.stimproperty;

import org.springframework.jdbc.core.JdbcTemplate;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Append-only log of delta-mutation generation attempts, keyed by (parent_id, mutated comp-set), with
 * the stim_id that attempted it and whether generation SUCCEEDED.
 *
 * "Success/fail" here is GENERATION feasibility, not behavioral response: a row is written from
 * {@code EStimShapeDeltaGAStim.createMStick()} when a delta that mutates a given comp-set either
 * produces a valid matchstick (success) or trips a {@code MorphException} (fail = the comp-set could
 * not be morphed into the parent-anchored noise circle). This is distinct from the response-based
 * "failed delta" notion used elsewhere (a responded delta that didn't drop the response).
 *
 * Because {@code createMStick()} is retried (and may pick a different comp-set each retry), a single
 * stim can produce several rows. The eventual use is for {@code chooseCompsToMutate()} to avoid
 * comp-sets that are effectively ungeneratable (only fails, no successes).
 *
 * The comp-set is the parent-numbered components, sorted and comma-joined, so {2,1} and {1,2} map to
 * the same key (matching {@link SharedNoiseCircleManager#key}).
 */
public class MutationSuccessFailManager {
    private static final String TABLE_NAME = "MutationSuccessFail";
    private final JdbcTemplate jdbcTemplate;

    public MutationSuccessFailManager(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
        createTableIfNotExists();
    }

    public void createTableIfNotExists() {
        jdbcTemplate.execute(
                "CREATE TABLE IF NOT EXISTS " + TABLE_NAME + " (" +
                        "id BIGINT AUTO_INCREMENT PRIMARY KEY, " +
                        "stim_id BIGINT NOT NULL, " +
                        "parent_id BIGINT NOT NULL, " +
                        "comps VARCHAR(255) NOT NULL, " +
                        "success BOOLEAN NOT NULL)"
        );
    }

    /** Canonical key for a comp-set: sorted, comma-joined, so order doesn't matter. */
    public static String key(List<Integer> comps) {
        List<Integer> sorted = new ArrayList<>(comps);
        Collections.sort(sorted);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < sorted.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append(sorted.get(i));
        }
        return sb.toString();
    }

    /** Log one generation attempt (one row, append-only). */
    public void writeOutcome(Long stimId, Long parentId, List<Integer> comps, boolean success) {
        jdbcTemplate.update(
                "INSERT INTO " + TABLE_NAME + " (stim_id, parent_id, comps, success) VALUES (?, ?, ?, ?)",
                new Object[]{stimId, parentId, key(comps), success}
        );
    }

    public int successCount(Long parentId, List<Integer> comps) {
        return countWhere(parentId, comps, true);
    }

    public int failCount(Long parentId, List<Integer> comps) {
        return countWhere(parentId, comps, false);
    }

    /**
     * A comp-set is treated as ungeneratable once it has been attempted at least once and has only
     * ever failed - never produced a valid stimulus.
     */
    public boolean isUngeneratable(Long parentId, List<Integer> comps) {
        return failCount(parentId, comps) > 0 && successCount(parentId, comps) == 0;
    }

    private int countWhere(Long parentId, List<Integer> comps, boolean success) {
        Integer count = (Integer) jdbcTemplate.queryForObject(
                "SELECT COUNT(*) FROM " + TABLE_NAME + " WHERE parent_id=? AND comps=? AND success=?",
                new Object[]{parentId, key(comps), success},
                Integer.class
        );
        return count == null ? 0 : count;
    }

    public String getTableName() {
        return TABLE_NAME;
    }
}
