# ************************************************************
# Sequel Pro SQL dump
# Version 4541
#
# http://www.sequelpro.com/
# https://github.com/sequelpro/sequelpro
#
# Host: 172.30.6.27 (MySQL 5.7.11-log)
# Database: jk_StimSpecram_train
# Generation Time: 2017-11-03 16:48:36 +0000
# ************************************************************


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


# Dump of table AcqData
# ------------------------------------------------------------

DROP TABLE IF EXISTS `AcqData`;

CREATE TABLE `AcqData` (
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `data` longblob NOT NULL,
  PRIMARY KEY (`tstamp`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci MAX_ROWS=4294967295 AVG_ROW_LENGTH=16384 COMMENT='Timestamp: when the first data record is saved.';



# Dump of table AcqSession
# ------------------------------------------------------------

DROP TABLE IF EXISTS `AcqSession`;

CREATE TABLE `AcqSession` (
  `start_time` bigint(20) NOT NULL DEFAULT '0',
  `stop_time` bigint(20) NOT NULL DEFAULT '0',
  PRIMARY KEY (`start_time`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci COMMENT='Timestamp: start and stop of each trial.';



# Dump of table BehMsg
# ------------------------------------------------------------

DROP TABLE IF EXISTS `BehMsg`;

CREATE TABLE `BehMsg` (
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `type` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `msg` longtext COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`tstamp`,`type`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;



# Dump of table BehMsgEye
# ------------------------------------------------------------

DROP TABLE IF EXISTS `BehMsgEye`;

CREATE TABLE `BehMsgEye` (
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `type` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `msg` longtext COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`tstamp`,`type`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;



# Dump of table ExpLog
# ------------------------------------------------------------

DROP TABLE IF EXISTS `ExpLog`;

CREATE TABLE `ExpLog` (
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `memo` text COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`tstamp`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;



# Dump of table InternalState
# ------------------------------------------------------------

DROP TABLE IF EXISTS `InternalState`;

CREATE TABLE `InternalState` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL DEFAULT '',
  `arr_ind` int(11) NOT NULL DEFAULT '0',
  `val` text COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`name`,`arr_ind`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

LOCK TABLES `InternalState` WRITE;
/*!40000 ALTER TABLE `InternalState` DISABLE KEYS */;

INSERT INTO `InternalState` (`name`, `arr_ind`, `val`)
VALUES
	('task_to_do_gen_ready',0,'<GenerationInfo>\n  <genId>0</genId>\n  <taskCount>0</taskCount>\n</GenerationInfo>');

/*!40000 ALTER TABLE `InternalState` ENABLE KEYS */;
UNLOCK TABLES;


# Dump of table RFInfo
# ------------------------------------------------------------

DROP TABLE IF EXISTS `RFInfo`;

CREATE TABLE `RFInfo` (
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `info` longtext COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`tstamp`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;



# Dump of table RFStimSpec
# ------------------------------------------------------------

DROP TABLE IF EXISTS `RFStimSpec`;

CREATE TABLE `RFStimSpec` (
  `id` bigint(20) NOT NULL DEFAULT '0',
  `spec` longtext COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;



# Dump of table StimSpec
# ------------------------------------------------------------

DROP TABLE IF EXISTS `StimSpec`;

CREATE TABLE `StimSpec` (
  `id` bigint(20) NOT NULL DEFAULT '0',
  `spec` longtext COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;



# Dump of table SystemVar
# ------------------------------------------------------------

DROP TABLE IF EXISTS `SystemVar`;

CREATE TABLE `SystemVar` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL DEFAULT '',
  `arr_ind` int(11) NOT NULL DEFAULT '0',
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `val` text COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`tstamp`,`name`,`arr_ind`),
  KEY `name_arr_ind` (`name`,`arr_ind`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

LOCK TABLES `SystemVar` WRITE;
/*!40000 ALTER TABLE `SystemVar` DISABLE KEYS */;

INSERT INTO `SystemVar` (`name`, `arr_ind`, `tstamp`, `val`)
VALUES
	('xper_slide_length',0,1097009302111741,'750'),
	('xper_inter_slide_interval',0,1097009302112036,'250'),
	('xper_inter_trial_interval',0,1097009302112331,'2000'),
	('xper_delay_after_trial_complete',0,1097009302112331,'500'),
	('xper_time_before_fixation_point_on',0,1097009302112331,'100'),
	('xper_time_allowed_for_initial_eye_in',0,1097009302112331,'1000'),
	('xper_required_eye_in_and_hold_time',0,1097009302112331,'200'),
	('xper_slides_per_trial',0,1097009302112331,'4'),
	('xper_do_empty_task',0,1097009302112331,'true'),
	('xper_eye_window_center',0,1097009302112331,'0'),
	('xper_eye_window_center',1,1097009302112331,'0'),
	('xper_eye_window_algorithm_base_window_size',0,1097009302112331,'1'),
	('xper_eye_window_algorithm_initial_window_size',0,1097009302112331,'10'),
	('xper_eye_window_algorithm_ramp_length',0,1097009302112331,'10'),
	('xper_left_iscan_channel',0,1097009302112331,'0'),
	('xper_left_iscan_channel',1,1097009302112331,'1'),
	('xper_left_iscan_channel_min_value',0,1097009302112331,'-10'),
	('xper_left_iscan_channel_min_value',1,1097009302112331,'-10'),
	('xper_left_iscan_channel_max_value',0,1097009302112331,'10'),
	('xper_left_iscan_channel_max_value',1,1097009302112331,'10'),
	('xper_left_iscan_channel_reference',0,1097009302112331,'diff'),
	('xper_left_iscan_channel_reference',1,1097009302112331,'diff'),
	('xper_left_iscan_eye_zero',0,1097009302112331,'0'),
	('xper_left_iscan_eye_zero',1,1097009302112331,'0'),
	('xper_left_iscan_eye_zero_update_enabled',0,1097009302112331,'true'),
	('xper_left_iscan_eye_zero_algorithm_eye_window_threshold',0,1097009302112331,'1'),
	('xper_left_iscan_eye_zero_algorithm_min_sample',0,1097009302112331,'10'),
	('xper_left_iscan_eye_zero_algorithm_span',0,1097009302112331,'10'),
	('xper_left_iscan_mapping_algorithm_parameter',0,1097009302112331,'1'),
	('xper_left_iscan_mapping_algorithm_parameter',1,1097009302112331,'0'),
	('xper_left_iscan_mapping_algorithm_parameter',2,1097009302112331,'0'),
	('xper_left_iscan_mapping_algorithm_parameter',3,1097009302112331,'1'),
	('xper_right_iscan_channel',0,1097009302112331,'2'),
	('xper_right_iscan_channel',1,1097009302112331,'3'),
	('xper_right_iscan_channel_min_value',0,1097009302112331,'-10'),
	('xper_right_iscan_channel_min_value',1,1097009302112331,'-10'),
	('xper_right_iscan_channel_max_value',0,1097009302112331,'10'),
	('xper_right_iscan_channel_max_value',1,1097009302112331,'10'),
	('xper_right_iscan_channel_reference',0,1097009302112331,'diff'),
	('xper_right_iscan_channel_reference',1,1097009302112331,'diff'),
	('xper_right_iscan_eye_zero',0,1097009302112331,'0'),
	('xper_right_iscan_eye_zero',1,1097009302112331,'0'),
	('xper_right_iscan_eye_zero_update_enabled',0,1097009302112331,'true'),
	('xper_right_iscan_eye_zero_algorithm_eye_window_threshold',0,1097009302112331,'1'),
	('xper_right_iscan_eye_zero_algorithm_min_sample',0,1097009302112331,'10'),
	('xper_right_iscan_eye_zero_algorithm_span',0,1097009302112331,'10'),
	('xper_right_iscan_mapping_algorithm_parameter',0,1097009302112331,'1'),
	('xper_right_iscan_mapping_algorithm_parameter',1,1097009302112331,'0'),
	('xper_right_iscan_mapping_algorithm_parameter',2,1097009302112331,'0'),
	('xper_right_iscan_mapping_algorithm_parameter',3,1097009302112331,'1'),
	('xper_eye_monitor_in_time_threshold',0,1097009302112331,'100'),
	('xper_eye_monitor_out_time_threshold',0,1097009302112331,'100'),
	('xper_eye_sampling_interval',0,1097009302112331,'10'),
	('xper_monkey_screen_width',0,1097009302112331,'812'),
	('xper_monkey_screen_height',0,1097009302112331,'305'),
	('xper_monkey_screen_depth',0,1097009302112331,'6000'),
	('xper_monkey_screen_distance',0,1097009302112331,'525'),
	('xper_monkey_pupil_distance',0,1097009302112331,'34'),
	('xper_monkey_screen_inverted',0,1097009302112331,'true'),
	('xper_fixation_position',0,1097009302112331,'0'),
	('xper_fixation_position',1,1097009302112331,'0'),
	('xper_fixation_point_color',0,1097009302112331,'1'),
	('xper_fixation_point_color',1,1097009302112331,'1'),
	('xper_fixation_point_color',2,1097009302112331,'0'),
	('xper_fixation_point_size',0,1097009302112331,'5'),
	('xper_fixation_on_with_stimuli',0,1097009302112331,'true'),
	('xper_screen_marker_size',0,1097009302112331,'20'),
	('xper_screen_marker_viewport_index',0,1097009302112331,'1'),
	('xper_time_allowed_for_initial_target_selection',0,1097009302112331,'1000'),
	('xper_required_target_selection_hold_time',0,1097009302112331,'250'),
	('xper_target_selection_eye_in_time_threshold',0,1097009302112331,'200'),
	('xper_target_selection_eye_out_time_threshold',0,1097009302112331,'100'),
	('xper_target_selection_eye_monitor_start_delay',0,1097009302112331,'200'),
	('xper_choice_target_size',0,1097009302112331,'2.0'),
	('xper_choice_target_distance_from_origin',0,1097009302112331,'5.0'),
	('xper_choice_target_eye_window_size',0,1097009302112331,'3.0'),
	('xper_juice_channel',0,1097009302130475,'0'),
	('xper_juice_channel_min_value',0,1097009302130475,'-10'),
	('xper_juice_channel_max_value',0,1097009302130475,'10'),
	('xper_juice_channel_reference',0,1097009302130475,'diff'),
	('xper_juice_delay',0,1097009302130734,'100'),
	('xper_juice_reward_length',0,1097094313592905,'170'),
	('xper_juice_bonus_delay',0,1097009302129752,'100'),
	('xper_juice_bonus_probability',0,1097009302130084,'0.2'),
	('xper_device',0,1097009302131117,'/dev/comedi0'),
	('acq_device',0,1097009302131117,'/dev/comedi0'),
	('acq_data_chan',0,1097009302131117,'0'),
	('acq_master_frequency',0,1097009302131117,'25000'),
	('acq_even_marker_chan',0,1097009302131117,'1'),
	('acq_odd_marker_chan',0,1097009302131117,'2'),
	('acq_device_buffer_size',0,1097009302131117,'25000'),
	('acq_device_buffer_count',0,1097009302131117,'1000'),
	('acq_data_block_size',0,1097009302131117,'10000'),
	('acq_n_channel',0,1097009302131117,'8'),
	('acq_channel',0,1097009302131117,'0'),
	('acq_channel',1,1097009302131117,'1'),
	('acq_channel',2,1097009302131117,'2'),
	('acq_channel',3,1097009302131117,'3'),
	('acq_channel',4,1097009302131117,'4'),
	('acq_channel',5,1097009302131117,'5'),
	('acq_channel',6,1097009302131117,'6'),
	('acq_channel',7,1097009302131117,'7'),
	('acq_channel_type',0,1097009302131117,'half_digital'),
	('acq_channel_min_value',0,1097009302130475,'-10'),
	('acq_channel_max_value',0,1097009302130475,'10'),
	('acq_channel_digital_v0',0,1097009302131117,'1.0'),
	('acq_channel_digital_v1',0,1097009302131117,'4.0'),
	('acq_channel_frequency',0,1097009302131117,'10000'),
	('acq_channel_reference',0,1097009302131117,'diff'),
	('acq_channel_type',1,1097009302131117,'half_digital'),
	('acq_channel_min_value',1,1097009302130475,'-10'),
	('acq_channel_max_value',1,1097009302130475,'10'),
	('acq_channel_digital_v0',1,1097009302131117,'1.0'),
	('acq_channel_digital_v1',1,1097009302131117,'4.0'),
	('acq_channel_frequency',1,1097009302131117,'10000'),
	('acq_channel_reference',1,1097009302131117,'diff'),
	('acq_channel_type',2,1097009302131117,'half_digital'),
	('acq_channel_min_value',2,1097009302130475,'-10'),
	('acq_channel_max_value',2,1097009302130475,'10'),
	('acq_channel_digital_v0',2,1097009302131117,'1.0'),
	('acq_channel_digital_v1',2,1097009302131117,'4.0'),
	('acq_channel_frequency',2,1097009302131117,'10000'),
	('acq_channel_reference',2,1097009302131117,'diff'),
	('acq_channel_type',3,1097009302131117,'analog'),
	('acq_channel_min_value',3,1097009302130475,'-10'),
	('acq_channel_max_value',3,1097009302130475,'10'),
	('acq_channel_digital_v0',3,1097009302131117,'1.0'),
	('acq_channel_digital_v1',3,1097009302131117,'4.0'),
	('acq_channel_frequency',3,1097009302131117,'10000'),
	('acq_channel_reference',3,1097009302131117,'diff'),
	('acq_channel_type',4,1097009302131117,'analog'),
	('acq_channel_min_value',4,1097009302130475,'-10'),
	('acq_channel_max_value',4,1097009302130475,'10'),
	('acq_channel_digital_v0',4,1097009302131117,'1.0'),
	('acq_channel_digital_v1',4,1097009302131117,'4.0'),
	('acq_channel_frequency',4,1097009302131117,'10000'),
	('acq_channel_reference',4,1097009302131117,'diff'),
	('acq_channel_type',5,1097009302131117,'analog'),
	('acq_channel_min_value',5,1097009302130475,'-10'),
	('acq_channel_max_value',5,1097009302130475,'10'),
	('acq_channel_digital_v0',5,1097009302131117,'1.0'),
	('acq_channel_digital_v1',5,1097009302131117,'4.0'),
	('acq_channel_frequency',5,1097009302131117,'10000'),
	('acq_channel_reference',5,1097009302131117,'diff'),
	('acq_channel_type',6,1097009302131117,'analog'),
	('acq_channel_min_value',6,1097009302130475,'-10'),
	('acq_channel_max_value',6,1097009302130475,'10'),
	('acq_channel_digital_v0',6,1097009302131117,'1.0'),
	('acq_channel_digital_v1',6,1097009302131117,'4.0'),
	('acq_channel_frequency',6,1097009302131117,'10000'),
	('acq_channel_reference',6,1097009302131117,'diff'),
	('acq_channel_type',7,1097009302131117,'analog'),
	('acq_channel_min_value',7,1097009302130475,'-10'),
	('acq_channel_max_value',7,1097009302130475,'10'),
	('acq_channel_digital_v0',7,1097009302131117,'1.0'),
	('acq_channel_digital_v1',7,1097009302131117,'4.0'),
	('acq_channel_frequency',7,1097009302131117,'10000'),
	('acq_channel_reference',7,1097009302131117,'diff'),
	('xper_rds_fixation_point_color',0,1097009302112331,'1'),
	('xper_rds_fixation_point_color',1,1097009302112331,'1'),
	('xper_rds_fixation_point_color',2,1097009302112331,'1'),
	('xper_rds_fixation_point_size',0,1097009302112331,'20'),
	('xper_rds_background_color',0,1097009302112331,'0.2'),
	('xper_rds_background_color',1,1097009302112331,'0.2'),
	('xper_rds_background_color',2,1097009302112331,'0.2'),
	('xper_rds_background_size',0,1097009302112331,'100'),
	('xper_fixation_sync_channel',0,1097000000000400,'1'),
	('xper_fixation_sync_channel_reference',0,1097000000000400,'common'),
	('xper_fixation_sync_high_volt',0,1097000000000400,'4');

/*!40000 ALTER TABLE `SystemVar` ENABLE KEYS */;
UNLOCK TABLES;


# Dump of table TaskDone
# ------------------------------------------------------------

DROP TABLE IF EXISTS `TaskDone`;

CREATE TABLE `TaskDone` (
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `task_id` bigint(20) NOT NULL DEFAULT '0',
  `part_done` tinyint(4) NOT NULL DEFAULT '0',
  PRIMARY KEY (`tstamp`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci COMMENT='Timestamp: when the stim is shown.';



# Dump of table TaskToDo
# ------------------------------------------------------------

DROP TABLE IF EXISTS `TaskToDo`;

CREATE TABLE `TaskToDo` (
  `task_id` bigint(20) NOT NULL DEFAULT '0',
  `stim_id` bigint(20) NOT NULL DEFAULT '0',
  `xfm_id` bigint(20) NOT NULL DEFAULT '0',
  `gen_id` bigint(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`task_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;



# Dump of table thumbnail
# ------------------------------------------------------------

DROP TABLE IF EXISTS `thumbnail`;

CREATE TABLE `Thumbnail` (
  `id` bigint(20) NOT NULL DEFAULT '0',
  `data` longblob NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;



# Dump of table xfmspec
# ------------------------------------------------------------

DROP TABLE IF EXISTS `XfmSpec`;

CREATE TABLE `XfmSpec` (
  `id` bigint(20) NOT NULL DEFAULT '0',
  `spec` longtext COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;




/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
