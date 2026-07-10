-- RFMappingResponse — live RF-mapping / tuning responses
-- =======================================================
-- One row per stimulus PRESENTATION x NEURAL CHANNEL. A "presentation" is one
-- flash of a frozen stimulus in the RF Plotter's controlled-presentation mode;
-- `tstamp` groups the per-channel rows of a single flash together.
--
-- The full stimulus spec + position are stored so any view (orientation tuning,
-- response-weighted RF heatmap, color tuning) can be rebuilt from this one table.
-- `orientation` and `hue` are optional convenience columns so the two headline
-- tuning views don't have to parse the spec XML; everything else is derivable
-- from stimType + stimSpec + position.
--
-- Same delivery model as the other RF tables: this table lives in the MySQL
-- template database and is cloned into new experiment databases by db_factory.
-- Run this once against the TEMPLATE ga database and against any existing ga
-- database you want to map in. CREATE TABLE IF NOT EXISTS makes it safe to
-- re-run.

CREATE TABLE IF NOT EXISTS RFMappingResponse (
  tstamp       bigint(20)   NOT NULL,              -- presentation id (micros); groups channels of one flash
  channel      varchar(16)  NOT NULL,              -- neural channel, e.g. 'A-000'

  -- Stimulus that was shown (frozen for the whole presentation)
  stimType     varchar(255) NOT NULL,              -- drawable class name (matches RFObjectData.object)
  stimSpec     longtext     NOT NULL,              -- full spec XML (round-trippable, redraw-able)
  xDeg         double       NOT NULL,              -- stimulus center X (degrees)
  yDeg         double       NOT NULL,              -- stimulus center Y (degrees)
  sizeDeg      double       DEFAULT NULL,          -- stimulus size (degrees), if applicable
  orientation  double       DEFAULT NULL,          -- convenience: orientation (deg) for orientation tuning
  hue          double       DEFAULT NULL,          -- convenience: hue for color tuning
  depth        int(11)      NOT NULL DEFAULT 0,    -- microns driven; 0 = final recording location

  -- Response window (marker epoch), on Intan's sample clock
  onTime       bigint(20)   DEFAULT NULL,          -- marker rising edge (Intan sample index)
  offTime      bigint(20)   DEFAULT NULL,          -- marker falling edge (Intan sample index)
  sampleRate   double       DEFAULT NULL,          -- Intan sample rate (Hz) for on/offTime

  -- Neural response for this channel in the response window
  spikeCount   int(11)      DEFAULT NULL,          -- spikes counted in the window
  rate         double       DEFAULT NULL,          -- spikes/sec over the window
  spikeTimes   longtext     DEFAULT NULL,          -- optional: relative spike times (ms) for re-analysis

  PRIMARY KEY (tstamp, channel),
  KEY idx_channel_depth (channel, depth)
) ENGINE=MyISAM;
