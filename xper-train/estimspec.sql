# JK 15 Jan 2020
CREATE TABLE `V1Microstim`.`EStimSpec` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `chan` INT UNSIGNED NOT NULL,
  `trig_src` VARCHAR(45) NULL,
  `num_pulses` INT UNSIGNED NOT NULL,
  `pulse_train_period` DECIMAL(7,3) UNSIGNED NULL,
  `post_stim_refractory_period` DECIMAL(7,3) UNSIGNED NULL,
  `stim_shape` VARCHAR(19) NOT NULL,
  `stim_polarity` VARCHAR(8) NOT NULL,
  `d1` DECIMAL(7,1) UNSIGNED NOT NULL,
  `d2` DECIMAL(7,1) UNSIGNED NOT NULL,
  `dp` DECIMAL(7,1) UNSIGNED NULL,
  `a1` DECIMAL(5,2) UNSIGNED NOT NULL,
  `a2` DECIMAL(5,2) UNSIGNED NOT NULL,
  `pre_stim_amp_settle` DECIMAL(6,3) UNSIGNED NULL,
  `post_stim_amp_settle` DECIMAL(6,3) UNSIGNED NULL,
  `maintain_amp_settle_during_pulse_train` TINYINT UNSIGNED NULL,
  `post_stim_charge_recovery_on` DECIMAL(7,3) UNSIGNED NULL,
  `post_stim_charge_recovery_off` DECIMAL(7,3) UNSIGNED NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE);

