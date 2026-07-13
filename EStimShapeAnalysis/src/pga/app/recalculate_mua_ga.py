"""
Offline: backfill MUAChannelResponses for the whole current session, then
recompute driving responses from it.

Why this exists
---------------
`recalculate_ga` only re-runs the response *processor* over rows that already
exist; it never re-parses the raw wideband. The live `MuaIntanResponseParser`
only fills the *current* generation's folders. So to reprocess an
already-recorded session with MUA responses, you first have to detect MUA across
*all* of the session's recording folders. This script does that (k=4 MAD,
100-task blocks per folder, all 32 channels — from the same GAVars the live
pipeline uses), then clears and recomputes the driving responses reading from
MUAChannelResponses.

It works whether or not `use_mua_response_processor` is set, because it builds a
MUA-reading processor explicitly (honoring the baseline-normalization toggle).
"""

from statistics import mean

from clat.util import connection

from src.analysis.ga.repo_ga_response_update import update_repository_with_ga_responses
from src.pga.app.recalculate_ga import clear_driving_responses
from src.pga.response_processing import GAResponseProcessor, RankBaselineNormalizeResponseProcessor
from src.pga.spike_parsing import MuaIntanResponseParser
from src.startup import context


def build_mua_processor(ga_config) -> GAResponseProcessor:
    """A response processor that reads MUAChannelResponses for the configured
    metric, layering rank-baseline normalization iff that toggle is on."""
    metric = ga_config.mua_metric()
    kwargs = dict(
        db_util=ga_config.db_util,
        repetition_combination_strategy=mean,
        cluster_combination_strategy=sum,
        mua_metric=metric,
    )
    if ga_config.is_use_normalized_ga_response_processor():
        return RankBaselineNormalizeResponseProcessor(**kwargs)
    return GAResponseProcessor(**kwargs)


def main():
    ga_config = context.ga_config
    metric = ga_config.mua_metric()
    print(f"Recalculating GA with MUA metric '{metric}' "
          f"(k={ga_config.mua_threshold_k()}, block={ga_config.mua_block_size()}).")

    # 1) Backfill MUAChannelResponses across every generation of the session.
    parser = MuaIntanResponseParser(
        ga_config.base_intan_path, ga_config.db_util,
        mua_metric=metric,
        threshold_k=ga_config.mua_threshold_k(),
        block_size=ga_config.mua_block_size(),
    )
    parser.parse_all_generations_to_mua(ga_config.ga_name)

    # 2) Recompute driving responses from the now-populated MUA table.
    processor = build_mua_processor(ga_config)
    clear_driving_responses(ga_config.connection())
    processor.process_to_db(ga_config.ga_name)

    # 3) Push the recomputed GA responses into the repository (best-effort).
    update_repository_with_ga_responses()
    print("Done: MUA backfill + driving-response recompute complete.")


if __name__ == "__main__":
    main()
