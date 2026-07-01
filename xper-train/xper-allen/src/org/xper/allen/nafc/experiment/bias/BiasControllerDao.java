package org.xper.allen.nafc.experiment.bias;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Collection;
import java.util.List;

import javax.sql.DataSource;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;

/**
 * Persistence for the NAFC anti-bias controller, in the experiment database. Two tables:
 *
 * <ul>
 *   <li>{@code bias_controller_state} &mdash; one row per stimulus lineage id; the controller's
 *       resume-safe source of truth, loaded on startup and upserted after each trial.</li>
 *   <li>{@code bias_controller_events} &mdash; append-only per-trial log for Python diagnostics.</li>
 * </ul>
 *
 * Tables are created on demand ({@code CREATE TABLE IF NOT EXISTS}), matching the convention used for
 * the other NAFC side tables (e.g. NafcSampleRole).
 */
public class BiasControllerDao {

    private final DataSource dataSource;

    public BiasControllerDao(DataSource dataSource) {
        this.dataSource = dataSource;
        ensureTables();
    }

    private void ensureTables() {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.execute("CREATE TABLE IF NOT EXISTS bias_controller_state (" +
                "stim_id BIGINT PRIMARY KEY, " +
                "variant_id BIGINT, " +
                "num_choices INT, " +
                "ewma_chose DOUBLE, " +
                "ewma_chose_when_wrong DOUBLE, " +
                "ewma_hit_when_correct DOUBLE, " +
                "n_present INT, " +
                "n_distractor INT, " +
                "n_correct_present INT, " +
                "biased BOOLEAN, " +
                "bias_score DOUBLE, " +
                "last_updated BIGINT)");
        jt.execute("CREATE TABLE IF NOT EXISTS bias_controller_events (" +
                "id BIGINT AUTO_INCREMENT PRIMARY KEY, " +
                "tstamp BIGINT, " +
                "trial_stim_id BIGINT, " +
                "variant_id BIGINT, " +
                "sample_id BIGINT, " +
                "chosen_id BIGINT, " +
                "num_choices INT, " +
                "correct BOOLEAN, " +
                "chosen_biased BOOLEAN, " +
                "avoided_biased BOOLEAN, " +
                "bias_score DOUBLE, " +
                "reward_pulses_base DOUBLE, " +
                "reward_pulses_delivered DOUBLE, " +
                "extra_iti_ms INT, " +
                "shaping_applied BOOLEAN, " +
                "shadow_mode BOOLEAN)");
    }

    /** Load all persisted per-stimulus states (e.g. on experiment startup). */
    public List<BiasKeyState> loadState() {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        return jt.query("SELECT stim_id, variant_id, num_choices, ewma_chose, ewma_chose_when_wrong, " +
                        "ewma_hit_when_correct, n_present, n_distractor, n_correct_present, biased, bias_score " +
                        "FROM bias_controller_state",
                new RowMapper<BiasKeyState>() {
                    public BiasKeyState mapRow(ResultSet rs, int rowNum) throws SQLException {
                        BiasKeyState s = new BiasKeyState(rs.getLong("stim_id"), rs.getLong("variant_id"));
                        s.numChoices = rs.getInt("num_choices");
                        s.ewmaChose = rs.getDouble("ewma_chose");
                        s.ewmaChoseWhenWrong = rs.getDouble("ewma_chose_when_wrong");
                        s.ewmaHitWhenCorrect = rs.getDouble("ewma_hit_when_correct");
                        s.nPresent = rs.getInt("n_present");
                        s.nDistractor = rs.getInt("n_distractor");
                        s.nCorrectPresent = rs.getInt("n_correct_present");
                        s.biased = rs.getBoolean("biased");
                        s.biasScore = rs.getDouble("bias_score");
                        return s;
                    }
                });
    }

    /** Upsert the given per-stimulus states, stamping them with the trial timestamp. */
    public void saveState(Collection<BiasKeyState> states, long tstamp) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        for (BiasKeyState s : states) {
            jt.update("INSERT INTO bias_controller_state (stim_id, variant_id, num_choices, ewma_chose, " +
                            "ewma_chose_when_wrong, ewma_hit_when_correct, n_present, n_distractor, " +
                            "n_correct_present, biased, bias_score, last_updated) " +
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) " +
                            "ON DUPLICATE KEY UPDATE variant_id = ?, num_choices = ?, ewma_chose = ?, " +
                            "ewma_chose_when_wrong = ?, ewma_hit_when_correct = ?, n_present = ?, " +
                            "n_distractor = ?, n_correct_present = ?, biased = ?, bias_score = ?, last_updated = ?",
                    new Object[] {
                            s.stimId, s.variantId, s.numChoices, s.ewmaChose, s.ewmaChoseWhenWrong,
                            s.ewmaHitWhenCorrect, s.nPresent, s.nDistractor, s.nCorrectPresent, s.biased,
                            s.biasScore, tstamp,
                            s.variantId, s.numChoices, s.ewmaChose, s.ewmaChoseWhenWrong,
                            s.ewmaHitWhenCorrect, s.nPresent, s.nDistractor, s.nCorrectPresent, s.biased,
                            s.biasScore, tstamp });
        }
    }

    /** Append one per-trial diagnostics row. */
    public void logEvent(BiasEvent e) {
        JdbcTemplate jt = new JdbcTemplate(dataSource);
        jt.update("INSERT INTO bias_controller_events (tstamp, trial_stim_id, variant_id, sample_id, " +
                        "chosen_id, num_choices, correct, chosen_biased, avoided_biased, bias_score, " +
                        "reward_pulses_base, reward_pulses_delivered, extra_iti_ms, shaping_applied, shadow_mode) " +
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                new Object[] {
                        e.tstamp, e.trialStimId, e.variantId, e.sampleId, e.chosenId, e.numChoices,
                        e.correct, e.chosenBiased, e.avoidedBiased, e.biasScore, e.rewardPulsesBase,
                        e.rewardPulsesDelivered, e.extraItiMs, e.shapingApplied, e.shadowMode });
    }
}
