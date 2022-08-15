-- MySQL dump 10.13  Distrib 5.7.22, for Linux (x86_64)
--
-- Host: localhost    Database: allen_estimshape_ga_dev_220812
-- ------------------------------------------------------
-- Server version	5.7.22-0ubuntu0.16.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `acqdata`
--

DROP TABLE IF EXISTS `acqdata`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `acqdata` (
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `data` longblob NOT NULL,
  PRIMARY KEY (`tstamp`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci MAX_ROWS=4294967295 AVG_ROW_LENGTH=16384 COMMENT='Timestamp: when the first data record is saved.';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `acqdata`
--

LOCK TABLES `acqdata` WRITE;
/*!40000 ALTER TABLE `acqdata` DISABLE KEYS */;
/*!40000 ALTER TABLE `acqdata` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `acqsession`
--

DROP TABLE IF EXISTS `acqsession`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `acqsession` (
  `start_time` bigint(20) NOT NULL DEFAULT '0',
  `stop_time` bigint(20) NOT NULL DEFAULT '0',
  PRIMARY KEY (`start_time`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci COMMENT='Timestamp: start and stop of each trial.';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `acqsession`
--

LOCK TABLES `acqsession` WRITE;
/*!40000 ALTER TABLE `acqsession` DISABLE KEYS */;
/*!40000 ALTER TABLE `acqsession` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `behmsg`
--

DROP TABLE IF EXISTS `behmsg`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `behmsg` (
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `type` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `msg` longtext COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`tstamp`,`type`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `behmsg`
--

LOCK TABLES `behmsg` WRITE;
/*!40000 ALTER TABLE `behmsg` DISABLE KEYS */;
/*!40000 ALTER TABLE `behmsg` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `behmsgeye`
--

DROP TABLE IF EXISTS `behmsgeye`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `behmsgeye` (
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `type` varchar(255) COLLATE utf8_unicode_ci NOT NULL,
  `msg` longtext COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`tstamp`,`type`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `behmsgeye`
--

LOCK TABLES `behmsgeye` WRITE;
/*!40000 ALTER TABLE `behmsgeye` DISABLE KEYS */;
/*!40000 ALTER TABLE `behmsgeye` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `descriptiveinfo`
--

DROP TABLE IF EXISTS `descriptiveinfo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `descriptiveinfo` (
  `tstamp` bigint(20) NOT NULL,
  `currentExptPrefix` bigint(11) NOT NULL,
  `gaRun` int(11) NOT NULL DEFAULT '1',
  `genNum` int(11) NOT NULL DEFAULT '1',
  `isRealExpt` tinyint(1) NOT NULL DEFAULT '0',
  `firstTrial` bigint(20) NOT NULL DEFAULT '0',
  `lastTrial` bigint(20) NOT NULL DEFAULT '0',
  `containsAnimation` int(11) NOT NULL DEFAULT '0'
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `descriptiveinfo`
--

LOCK TABLES `descriptiveinfo` WRITE;
/*!40000 ALTER TABLE `descriptiveinfo` DISABLE KEYS */;
/*!40000 ALTER TABLE `descriptiveinfo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `explog`
--

DROP TABLE IF EXISTS `explog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `explog` (
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `memo` text COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`tstamp`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `explog`
--

LOCK TABLES `explog` WRITE;
/*!40000 ALTER TABLE `explog` DISABLE KEYS */;
/*!40000 ALTER TABLE `explog` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `internalstate`
--

DROP TABLE IF EXISTS `internalstate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `internalstate` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL DEFAULT '',
  `arr_ind` int(11) NOT NULL DEFAULT '0',
  `val` text COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`name`,`arr_ind`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `internalstate`
--

LOCK TABLES `internalstate` WRITE;
/*!40000 ALTER TABLE `internalstate` DISABLE KEYS */;
INSERT INTO `internalstate` VALUES ('task_to_do_gen_ready',0,'<GenerationInfo>\n  <genId>0</genId>\n  <taskCount>102</taskCount>\n  <stimPerLinCount>40</stimPerLinCount>\n  <repsPerStim>5</repsPerStim>\n  <stimPerTrial>4</stimPerTrial>\n</GenerationInfo>');
/*!40000 ALTER TABLE `internalstate` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rfinfo`
--

DROP TABLE IF EXISTS `rfinfo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `rfinfo` (
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `sessionNum` text COLLATE utf8_unicode_ci NOT NULL,
  `cellNum` int(11) NOT NULL,
  `info` longtext COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`tstamp`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rfinfo`
--

LOCK TABLES `rfinfo` WRITE;
/*!40000 ALTER TABLE `rfinfo` DISABLE KEYS */;
/*!40000 ALTER TABLE `rfinfo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rfstimspec`
--

DROP TABLE IF EXISTS `rfstimspec`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `rfstimspec` (
  `id` bigint(20) NOT NULL DEFAULT '0',
  `descriptiveId` text COLLATE utf8_unicode_ci,
  `spec` longtext COLLATE utf8_unicode_ci NOT NULL,
  `data` longtext COLLATE utf8_unicode_ci,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rfstimspec`
--

LOCK TABLES `rfstimspec` WRITE;
/*!40000 ALTER TABLE `rfstimspec` DISABLE KEYS */;
/*!40000 ALTER TABLE `rfstimspec` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sessionlog`
--

DROP TABLE IF EXISTS `sessionlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sessionlog` (
  `tstamp` bigint(20) NOT NULL,
  `sessionNum` text COLLATE utf8_unicode_ci,
  `cellNum` int(11) DEFAULT NULL,
  `notes` longtext COLLATE utf8_unicode_ci
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sessionlog`
--

LOCK TABLES `sessionlog` WRITE;
/*!40000 ALTER TABLE `sessionlog` DISABLE KEYS */;
/*!40000 ALTER TABLE `sessionlog` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stimobjdata`
--

DROP TABLE IF EXISTS `stimobjdata`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `stimobjdata` (
  `id` bigint(20) NOT NULL DEFAULT '0',
  `descId` text COLLATE utf8_unicode_ci NOT NULL,
  `javaspec` longtext COLLATE utf8_unicode_ci NOT NULL,
  `mstickspec` longtext COLLATE utf8_unicode_ci NOT NULL,
  `matspec` longtext COLLATE utf8_unicode_ci,
  `dataspec` longtext COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stimobjdata`
--

LOCK TABLES `stimobjdata` WRITE;
/*!40000 ALTER TABLE `stimobjdata` DISABLE KEYS */;
/*!40000 ALTER TABLE `stimobjdata` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stimobjdata_occluder`
--

DROP TABLE IF EXISTS `stimobjdata_occluder`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `stimobjdata_occluder` (
  `id` bigint(11) unsigned NOT NULL AUTO_INCREMENT,
  `descGenId` text COLLATE utf8_unicode_ci,
  `lb_x` double DEFAULT NULL,
  `lb_y` double DEFAULT NULL,
  `rt_x` double DEFAULT NULL,
  `rt_y` double DEFAULT NULL,
  `color_r` float DEFAULT NULL,
  `color_g` float DEFAULT NULL,
  `color_b` float DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stimobjdata_occluder`
--

LOCK TABLES `stimobjdata_occluder` WRITE;
/*!40000 ALTER TABLE `stimobjdata_occluder` DISABLE KEYS */;
/*!40000 ALTER TABLE `stimobjdata_occluder` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stimobjdata_vert`
--

DROP TABLE IF EXISTS `stimobjdata_vert`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `stimobjdata_vert` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `descId` text COLLATE utf8_unicode_ci,
  `vertspec` mediumblob,
  `faceSpec` mediumblob,
  `normSpec` mediumblob,
  `texSpec` mediumblob,
  `texFaceSpec` mediumblob,
  `vertspec_vis` mediumblob,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stimobjdata_vert`
--

LOCK TABLES `stimobjdata_vert` WRITE;
/*!40000 ALTER TABLE `stimobjdata_vert` DISABLE KEYS */;
/*!40000 ALTER TABLE `stimobjdata_vert` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stimspec`
--

DROP TABLE IF EXISTS `stimspec`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `stimspec` (
  `id` bigint(20) NOT NULL DEFAULT '0',
  `spec` longtext COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stimspec`
--

LOCK TABLES `stimspec` WRITE;
/*!40000 ALTER TABLE `stimspec` DISABLE KEYS */;
/*!40000 ALTER TABLE `stimspec` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `systemvar`
--

DROP TABLE IF EXISTS `systemvar`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `systemvar` (
  `name` varchar(255) COLLATE utf8_unicode_ci NOT NULL DEFAULT '',
  `arr_ind` int(11) NOT NULL DEFAULT '0',
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `val` text COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`tstamp`,`name`,`arr_ind`),
  KEY `name_arr_ind` (`name`,`arr_ind`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `systemvar`
--

LOCK TABLES `systemvar` WRITE;
/*!40000 ALTER TABLE `systemvar` DISABLE KEYS */;
INSERT INTO `systemvar` VALUES ('xper_slide_length',0,1097000000000010,'750'),('xper_inter_slide_interval',0,1097000000000012,'250'),('xper_inter_trial_interval',0,1097000000000020,'1500'),('xper_delay_after_trial_complete',0,1097000000000020,'20'),('xper_time_before_fixation_point_on',0,1097000000000040,'20'),('xper_time_allowed_for_initial_eye_in',0,1097000000000040,'1000'),('xper_required_eye_in_and_hold_time',0,1097000000000040,'250'),('xper_slides_per_trial',0,1097000000000040,'4'),('xper_do_empty_task',0,1097000000000040,'true'),('xper_first_slide_length',0,1097000000000014,'500'),('xper_first_inter_slide_interval',0,1097000000000016,'500'),('xper_eye_window_center',0,1097000000000100,'0'),('xper_eye_window_center',1,1097000000000100,'0'),('xper_eye_window_algorithm_base_window_size',0,1097000000000100,'1.5'),('xper_eye_window_algorithm_initial_window_size',0,1097000000000100,'1.5'),('xper_eye_window_algorithm_ramp_length',0,1097000000000100,'10'),('xper_right_iscan_eye_zero_algorithm_span',0,1097000000000320,'10'),('xper_right_iscan_eye_zero_algorithm_min_sample',0,1097000000000320,'10'),('xper_right_iscan_eye_zero_algorithm_eye_window_threshold',0,1097000000000320,'1'),('xper_right_iscan_eye_zero_update_enabled',0,1097000000000320,'true'),('xper_right_iscan_channel_reference',0,1097000000000310,'diff'),('xper_right_iscan_channel_reference',1,1097000000000310,'diff'),('xper_right_iscan_channel_max_value',1,1097000000000310,'10'),('xper_right_iscan_channel_max_value',0,1097000000000310,'10'),('xper_right_iscan_channel_min_value',1,1097000000000310,'-10'),('xper_right_iscan_channel_min_value',0,1097000000000310,'-10'),('xper_eye_monitor_in_time_threshold',0,1097000000000100,'100'),('xper_eye_monitor_out_time_threshold',0,1097000000000100,'105'),('xper_eye_sampling_interval',0,1097000000000100,'10'),('xper_monkey_screen_width',0,1097000000000200,'812'),('xper_monkey_screen_height',0,1097000000000200,'305'),('xper_monkey_screen_depth',0,1097000000000200,'6000'),('xper_monkey_screen_distance',0,1097000000000200,'500'),('xper_monkey_pupil_distance',0,1097000000000200,'31'),('xper_monkey_screen_inverted',0,1097000000000200,'true'),('xper_fixation_position',0,1097000000000240,'0'),('xper_fixation_position',1,1097000000000240,'0'),('xper_fixation_point_color',0,1097000000000240,'0.5'),('xper_fixation_point_color',1,1097000000000240,'0.5'),('xper_fixation_point_color',2,1097000000000240,'0'),('xper_fixation_point_size',0,1097000000000240,'1'),('xper_fixation_on_with_stimuli',0,1097000000000240,'true'),('xper_screen_marker_size',0,1097000000000260,'20'),('xper_screen_marker_viewport_index',0,1097000000000260,'1'),('xper_time_allowed_for_initial_target_selection',0,1097000000000140,'500'),('xper_required_target_selection_hold_time',0,1097000000000140,'0'),('xper_target_selection_eye_in_time_threshold',0,1097000000000140,'0'),('xper_target_selection_eye_out_time_threshold',0,1097000000000140,'0'),('xper_target_selection_eye_monitor_start_delay',0,1097000000000140,'0'),('xper_choice_target_size',0,1097000000000180,'2.0'),('xper_choice_target_distance_from_origin',0,1097000000000180,'5.0'),('xper_choice_target_eye_window_size',0,1097000000000180,'30.0'),('xper_juice_channel',0,1097000000000270,'0'),('xper_juice_channel_min_value',0,1097000000000270,'-10'),('xper_juice_channel_max_value',0,1097000000000270,'10'),('xper_juice_channel_reference',0,1097000000000270,'common'),('xper_juice_delay',0,1097000000000270,'50'),('xper_juice_reward_length',0,1097000000000270,'200'),('xper_juice_bonus_delay',0,1097000000000270,'450'),('xper_juice_bonus_probability',0,1097000000000270,'0.1'),('xper_device',0,1097000000000290,'/dev/comedi0'),('acq_device',0,1097000000000400,'/dev/comedi0'),('acq_data_chan',0,1097000000000400,'0'),('acq_master_frequency',0,1097000000000400,'25000'),('acq_even_marker_chan',0,1097000000000400,'1'),('acq_odd_marker_chan',0,1097000000000400,'2'),('acq_device_buffer_size',0,1097000000000400,'25000'),('acq_device_buffer_count',0,1097000000000400,'1000'),('acq_data_block_size',0,1097000000000400,'10000'),('acq_n_channel',0,1097000000000400,'16'),('acq_channel',0,1097000000000400,'0'),('acq_channel',1,1097000000000400,'1'),('acq_channel',2,1097000000000400,'2'),('acq_channel',3,1097000000000400,'3'),('acq_channel',4,1097000000000400,'4'),('acq_channel',5,1097000000000400,'5'),('acq_channel',6,1097000000000400,'6'),('acq_channel',7,1097000000000400,'7'),('acq_channel_type',0,1097000000000400,'half_digital'),('acq_channel_min_value',0,1097000000000400,'-10'),('acq_channel_max_value',0,1097000000000400,'10'),('acq_channel_digital_v0',0,1097000000000400,'1.0'),('acq_channel_digital_v1',0,1097000000000400,'4.0'),('acq_channel_frequency',0,1097000000000400,'20000'),('acq_channel_reference',0,1097000000000400,'common'),('acq_channel_type',1,1097000000000400,'half_digital'),('acq_channel_min_value',1,1097000000000400,'-10'),('acq_channel_max_value',1,1097000000000400,'10'),('acq_channel_digital_v0',1,1097000000000400,'1.0'),('acq_channel_digital_v1',1,1097000000000400,'4.0'),('acq_channel_frequency',1,1097000000000400,'100'),('acq_channel_reference',1,1097000000000400,'common'),('acq_channel_type',2,1097000000000400,'half_digital'),('acq_channel_min_value',2,1097000000000400,'-10'),('acq_channel_max_value',2,1097000000000400,'10'),('acq_channel_digital_v0',2,1097000000000400,'1.0'),('acq_channel_digital_v1',2,1097000000000400,'4.0'),('acq_channel_frequency',2,1097000000000400,'100'),('acq_channel_reference',2,1097000000000400,'common'),('acq_channel_type',3,1097000000000400,'analog'),('acq_channel_min_value',3,1097000000000400,'-10'),('acq_channel_max_value',3,1097000000000400,'10'),('acq_channel_digital_v0',3,1097000000000400,'1.0'),('acq_channel_digital_v1',3,1097000000000400,'4.0'),('acq_channel_frequency',3,1097000000000400,'100'),('acq_channel_reference',3,1097000000000400,'diff'),('acq_channel_type',4,1097000000000400,'analog'),('acq_channel_min_value',4,1097000000000400,'-10'),('acq_channel_max_value',4,1097000000000400,'10'),('acq_channel_digital_v0',4,1097000000000400,'1.0'),('acq_channel_digital_v1',4,1097000000000400,'4.0'),('acq_channel_frequency',4,1097000000000400,'100'),('acq_channel_reference',4,1097000000000400,'diff'),('acq_channel_type',5,1097000000000400,'analog'),('acq_channel_min_value',5,1097000000000400,'-10'),('acq_channel_max_value',5,1097000000000400,'10'),('acq_channel_digital_v0',5,1097000000000400,'1.0'),('acq_channel_digital_v1',5,1097000000000400,'4.0'),('acq_channel_frequency',5,1097000000000400,'100'),('acq_channel_reference',5,1097000000000400,'diff'),('acq_channel_type',6,1097000000000400,'analog'),('acq_channel_min_value',6,1097000000000400,'-10'),('acq_channel_max_value',6,1097000000000400,'10'),('acq_channel_digital_v0',6,1097000000000400,'1.0'),('acq_channel_digital_v1',6,1097000000000400,'4.0'),('acq_channel_frequency',6,1097000000000400,'100'),('acq_channel_reference',6,1097000000000400,'diff'),('acq_channel_type',7,1097000000000400,'half_digital'),('acq_channel_min_value',7,1097000000000400,'-10'),('acq_channel_max_value',7,1097000000000400,'10'),('acq_channel_digital_v0',7,1097000000000400,'1.0'),('acq_channel_digital_v1',7,1097000000000400,'4.0'),('acq_channel_frequency',7,1097000000000400,'100'),('acq_channel_reference',7,1097000000000400,'diff'),('xper_rds_fixation_point_color',0,1097000000000280,'1'),('xper_rds_fixation_point_color',1,1097000000000280,'1'),('xper_rds_fixation_point_color',2,1097000000000280,'1'),('xper_rds_fixation_point_size',0,1097000000000280,'0'),('xper_rds_background_color',0,1097000000000280,'0.2'),('xper_rds_background_color',1,1097000000000280,'0.2'),('xper_rds_background_color',2,1097000000000280,'0.2'),('xper_rds_background_size',0,1097000000000280,'100'),('xper_blank_target_screen_display_time',0,1097000000000140,'500'),('xper_left_iscan_channel_min_value',1,1097000000000310,'-10'),('xper_left_iscan_channel_max_value',0,1097000000000310,'10'),('xper_left_iscan_channel_max_value',1,1097000000000310,'10'),('xper_left_iscan_channel_reference',0,1097000000000310,'diff'),('xper_left_iscan_channel_reference',1,1097000000000310,'diff'),('xper_left_iscan_eye_zero_update_enabled',0,1097000000000320,'true'),('xper_left_iscan_eye_zero_algorithm_eye_window_threshold',0,1097000000000320,'1'),('xper_left_iscan_eye_zero_algorithm_min_sample',0,1097000000000320,'10'),('xper_left_iscan_eye_zero_algorithm_span',0,1097000000000320,'10'),('xper_right_iscan_channel',0,1097000000000300,'2'),('xper_right_iscan_channel',1,1097000000000300,'3'),('xper_left_iscan_channel_min_value',0,1097000000000310,'-10'),('xper_left_iscan_channel',0,1097000000000300,'0'),('xper_left_iscan_channel',1,1097000000000300,'1'),('acq_channel',8,1097000000000400,'8'),('acq_channel',9,1097000000000400,'9'),('acq_channel',10,1097000000000400,'10'),('acq_channel',11,1097000000000400,'11'),('acq_channel',12,1097000000000400,'12'),('acq_channel',13,1097000000000400,'13'),('acq_channel',14,1097000000000400,'14'),('acq_channel',15,1097000000000400,'15'),('acq_data_chan',1,1097000000000400,'8'),('acq_data_chan',2,1097000000000400,'9'),('acq_data_chan',3,1097000000000400,'10'),('acq_channel_digital_v0',8,1097000000000400,'1.0'),('acq_channel_digital_v0',9,1097000000000400,'1.0'),('acq_channel_digital_v0',10,1097000000000400,'1.0'),('acq_channel_digital_v0',11,1097000000000400,'1.0'),('acq_channel_digital_v0',12,1097000000000400,'1.0'),('acq_channel_digital_v0',13,1097000000000400,'1.0'),('acq_channel_digital_v0',14,1097000000000400,'1.0'),('acq_channel_digital_v0',15,1097000000000400,'1.0'),('acq_channel_digital_v1',8,1097000000000400,'4.0'),('acq_channel_digital_v1',9,1097000000000400,'4.0'),('acq_channel_digital_v1',10,1097000000000400,'4.0'),('acq_channel_digital_v1',11,1097000000000400,'4.0'),('acq_channel_digital_v1',12,1097000000000400,'4.0'),('acq_channel_digital_v1',13,1097000000000400,'4.0'),('acq_channel_digital_v1',14,1097000000000400,'4.0'),('acq_channel_digital_v1',15,1097000000000400,'4.0'),('acq_channel_frequency',8,1097000000000400,'20000'),('acq_channel_frequency',9,1097000000000400,'20000'),('acq_channel_frequency',10,1097000000000400,'20000'),('acq_channel_frequency',11,1097000000000400,'100'),('acq_channel_frequency',12,1097000000000400,'100'),('acq_channel_frequency',13,1097000000000400,'100'),('acq_channel_frequency',14,1097000000000400,'100'),('acq_channel_frequency',15,1097000000000400,'100'),('acq_channel_max_value',8,1097000000000400,'10'),('acq_channel_max_value',9,1097000000000400,'10'),('acq_channel_max_value',10,1097000000000400,'10'),('acq_channel_max_value',11,1097000000000400,'10'),('acq_channel_max_value',12,1097000000000400,'10'),('acq_channel_max_value',13,1097000000000400,'10'),('acq_channel_max_value',14,1097000000000400,'10'),('acq_channel_max_value',15,1097000000000400,'10'),('acq_channel_min_value',8,1097000000000400,'-10'),('acq_channel_min_value',9,1097000000000400,'-10'),('acq_channel_min_value',10,1097000000000400,'-10'),('acq_channel_min_value',11,1097000000000400,'-10'),('acq_channel_min_value',12,1097000000000400,'-10'),('acq_channel_min_value',13,1097000000000400,'-10'),('acq_channel_min_value',14,1097000000000400,'-10'),('acq_channel_min_value',15,1097000000000400,'-10'),('acq_channel_reference',8,1097000000000400,'common'),('acq_channel_reference',9,1097000000000400,'common'),('acq_channel_reference',10,1097000000000400,'common'),('acq_channel_reference',11,1097000000000400,'diff'),('acq_channel_reference',12,1097000000000400,'diff'),('acq_channel_reference',13,1097000000000400,'diff'),('acq_channel_reference',14,1097000000000400,'diff'),('acq_channel_reference',15,1097000000000400,'diff'),('acq_channel_type',8,1097000000000400,'half_digital'),('acq_channel_type',9,1097000000000400,'half_digital'),('acq_channel_type',10,1097000000000400,'half_digital'),('acq_channel_type',11,1097000000000400,'analog'),('acq_channel_type',12,1097000000000400,'analog'),('acq_channel_type',13,1097000000000400,'analog'),('acq_channel_type',14,1097000000000400,'analog'),('acq_channel_type',15,1097000000000400,'analog'),('xper_stim_color_foreground',2,1097000000000400,'1'),('xper_stim_color_foreground',1,1097000000000400,'1'),('xper_stim_color_foreground',0,1097000000000400,'1'),('xper_stim_color_background',2,1097000000000400,'0.3'),('xper_stim_color_background',1,1097000000000400,'0.3'),('xper_stim_color_background',0,1097000000000400,'0.3'),('xper_fixation_sync_channel',0,1097000000000400,'1'),('xper_fixation_sync_channel_reference',0,1097000000000400,'common'),('xper_fixation_sync_high_volt',0,1097000000000400,'4'),('xper_timeout_base_delay',0,1097000000000020,'0'),('xper_left_iscan_mapping_algorithm_parameter',1,1538842228581342,'0.008415319788298615'),('xper_left_iscan_mapping_algorithm_parameter',2,1538842228581342,'0.003484667487008997'),('xper_left_iscan_mapping_algorithm_parameter',3,1538842228581342,'-0.13500916990092832'),('xper_right_iscan_eye_zero',0,1538842228581342,'-1.537916713418668'),('xper_right_iscan_eye_zero',1,1538842228581342,'3.800480472583959'),('xper_right_iscan_mapping_algorithm_parameter',0,1538842228581342,'-0.09616891157060115'),('xper_right_iscan_mapping_algorithm_parameter',1,1538842228581342,'0.0022943420316536398'),('xper_right_iscan_mapping_algorithm_parameter',2,1538842228581342,'6.329947225709452E-4'),('xper_right_iscan_mapping_algorithm_parameter',3,1538842228581342,'0.14349339177709153'),('xper_right_iscan_mapping_algorithm_parameter',3,1097000000000340,'1'),('xper_right_iscan_mapping_algorithm_parameter',2,1097000000000340,'0'),('xper_right_iscan_mapping_algorithm_parameter',1,1097000000000340,'0'),('xper_right_iscan_mapping_algorithm_parameter',0,1097000000000340,'1'),('xper_left_iscan_mapping_algorithm_parameter',0,1097000000000340,'1'),('xper_left_iscan_mapping_algorithm_parameter',1,1097000000000340,'0'),('xper_left_iscan_mapping_algorithm_parameter',2,1097000000000340,'0'),('xper_left_iscan_mapping_algorithm_parameter',3,1097000000000340,'1'),('xper_right_iscan_eye_zero',0,1097000000000320,'0'),('xper_right_iscan_eye_zero',1,1097000000000320,'0'),('xper_left_iscan_eye_zero',0,1097000000000320,'0'),('xper_left_iscan_eye_zero',1,1097000000000320,'0'),('xper_left_iscan_eye_zero',0,1538842228581342,'0.6043923591729126'),('xper_left_iscan_eye_zero',1,1538842228581342,'-1.673491011322254'),('xper_left_iscan_mapping_algorithm_parameter',0,1538842228581342,'0.11997878692675464');
/*!40000 ALTER TABLE `systemvar` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `taskdone`
--

DROP TABLE IF EXISTS `taskdone`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `taskdone` (
  `tstamp` bigint(20) NOT NULL DEFAULT '0',
  `task_id` bigint(20) NOT NULL DEFAULT '0',
  `part_done` tinyint(4) NOT NULL DEFAULT '0',
  PRIMARY KEY (`tstamp`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci COMMENT='Timestamp: when the stim is shown.';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `taskdone`
--

LOCK TABLES `taskdone` WRITE;
/*!40000 ALTER TABLE `taskdone` DISABLE KEYS */;
/*!40000 ALTER TABLE `taskdone` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tasktodo`
--

DROP TABLE IF EXISTS `tasktodo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tasktodo` (
  `task_id` bigint(20) NOT NULL DEFAULT '0',
  `stim_id` bigint(20) NOT NULL DEFAULT '0',
  `xfm_id` bigint(20) NOT NULL DEFAULT '0',
  `gen_id` bigint(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`task_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tasktodo`
--

LOCK TABLES `tasktodo` WRITE;
/*!40000 ALTER TABLE `tasktodo` DISABLE KEYS */;
/*!40000 ALTER TABLE `tasktodo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `thumbnail`
--

DROP TABLE IF EXISTS `thumbnail`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `thumbnail` (
  `id` bigint(20) NOT NULL DEFAULT '0',
  `data` longblob NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `thumbnail`
--

LOCK TABLES `thumbnail` WRITE;
/*!40000 ALTER TABLE `thumbnail` DISABLE KEYS */;
/*!40000 ALTER TABLE `thumbnail` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `xfmspec`
--

DROP TABLE IF EXISTS `xfmspec`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `xfmspec` (
  `id` bigint(20) NOT NULL DEFAULT '0',
  `spec` longtext COLLATE utf8_unicode_ci NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `xfmspec`
--

LOCK TABLES `xfmspec` WRITE;
/*!40000 ALTER TABLE `xfmspec` DISABLE KEYS */;
/*!40000 ALTER TABLE `xfmspec` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2022-08-12 16:42:05
