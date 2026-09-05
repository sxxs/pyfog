-- FOG database layout for testing pyfog without a FOG server.
--
-- Generated from FOG 1.5.10 (branch stable, packages/web/commons/schema.php,
-- GPLv3, https://github.com/FOGProject/fogproject) by running all 279
-- migration steps against an empty MariaDB and dumping the result:
-- table definitions plus the reference rows FOG inserts itself
-- (taskStates, taskTypes, os, imageTypes, imagePartitionTypes, supportedOS,
-- modules, globalSettings; installer-provided settings hold dummy values).
-- Not needed at runtime; see README "Verification".
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
/*M!999999\- enable the sandbox mode */ 
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `clientUpdates` (
  `cuID` int(11) NOT NULL AUTO_INCREMENT,
  `cuName` varchar(200) NOT NULL,
  `cuMD5` varchar(100) NOT NULL,
  `cuType` varchar(30) NOT NULL,
  `cuFile` longblob NOT NULL,
  PRIMARY KEY (`cuID`),
  KEY `new_index` (`cuName`),
  KEY `new_index1` (`cuType`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `dirCleaner` (
  `dcID` int(11) NOT NULL AUTO_INCREMENT,
  `dcPath` longtext NOT NULL,
  PRIMARY KEY (`dcID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `globalSettings` (
  `settingID` int(11) NOT NULL AUTO_INCREMENT,
  `settingKey` varchar(255) NOT NULL,
  `settingDesc` longtext NOT NULL,
  `settingValue` longtext NOT NULL,
  `settingCategory` longtext NOT NULL,
  PRIMARY KEY (`settingID`),
  UNIQUE KEY `settingKey` (`settingKey`),
  UNIQUE KEY `settingKey_2` (`settingKey`),
  UNIQUE KEY `settingKey_3` (`settingKey`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `greenFog` (
  `gfID` int(11) NOT NULL AUTO_INCREMENT,
  `gfHostID` int(11) NOT NULL,
  `gfHour` int(11) NOT NULL,
  `gfMin` int(11) NOT NULL,
  `gfAction` varchar(2) NOT NULL,
  `gfDays` varchar(25) NOT NULL,
  PRIMARY KEY (`gfID`),
  KEY `new_index` (`gfHostID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `groupMembers` (
  `gmID` int(11) NOT NULL AUTO_INCREMENT,
  `gmHostID` int(11) NOT NULL,
  `gmGroupID` int(11) NOT NULL,
  PRIMARY KEY (`gmID`),
  UNIQUE KEY `gmHostID` (`gmHostID`,`gmGroupID`),
  UNIQUE KEY `gmGroupID` (`gmHostID`,`gmGroupID`),
  KEY `new_index` (`gmHostID`),
  KEY `new_index1` (`gmGroupID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `groups` (
  `groupID` int(11) NOT NULL AUTO_INCREMENT,
  `groupName` varchar(50) NOT NULL,
  `groupDesc` longtext NOT NULL,
  `groupDateTime` timestamp NOT NULL DEFAULT current_timestamp(),
  `groupCreateBy` varchar(50) NOT NULL,
  `groupBuilding` int(11) NOT NULL,
  `groupKernel` varchar(255) NOT NULL,
  `groupKernelArgs` varchar(255) NOT NULL,
  `groupPrimaryDisk` varchar(255) NOT NULL,
  PRIMARY KEY (`groupID`),
  UNIQUE KEY `groupName` (`groupName`),
  UNIQUE KEY `groupName_2` (`groupName`),
  KEY `new_index` (`groupName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `history` (
  `hID` int(11) NOT NULL AUTO_INCREMENT,
  `hText` varchar(255) NOT NULL,
  `hUser` varchar(200) NOT NULL,
  `hTime` timestamp NOT NULL DEFAULT current_timestamp(),
  `hIP` varchar(50) NOT NULL,
  PRIMARY KEY (`hID`),
  UNIQUE KEY `updateTime` (`hText`,`hTime`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `hookEvents` (
  `heID` int(11) NOT NULL AUTO_INCREMENT,
  `heName` varchar(255) NOT NULL,
  PRIMARY KEY (`heID`),
  UNIQUE KEY `name` (`heName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `hostAutoLogOut` (
  `haloID` int(11) NOT NULL AUTO_INCREMENT,
  `haloHostID` int(11) NOT NULL,
  `haloTime` varchar(10) NOT NULL,
  PRIMARY KEY (`haloID`),
  UNIQUE KEY `haloHostID` (`haloHostID`),
  KEY `new_index` (`haloHostID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `hostMAC` (
  `hmID` int(11) NOT NULL AUTO_INCREMENT,
  `hmHostID` int(11) NOT NULL,
  `hmMAC` varchar(59) NOT NULL,
  `hmDesc` longtext NOT NULL,
  `hmPrimary` enum('0','1') NOT NULL,
  `hmPending` enum('0','1') NOT NULL,
  `hmIgnoreClient` enum('0','1') NOT NULL,
  `hmIgnoreImaging` enum('0','1') NOT NULL,
  PRIMARY KEY (`hmID`),
  UNIQUE KEY `hmHostID` (`hmMAC`),
  UNIQUE KEY `hmMAC` (`hmMAC`),
  UNIQUE KEY `hmMAC_2` (`hmMAC`),
  KEY `idxHostID` (`hmHostID`),
  KEY `idxMac` (`hmMAC`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `hostScreenSettings` (
  `hssID` int(11) NOT NULL AUTO_INCREMENT,
  `hssHostID` int(11) NOT NULL,
  `hssWidth` int(11) NOT NULL,
  `hssHeight` int(11) NOT NULL,
  `hssRefresh` int(11) NOT NULL,
  `hssOrientation` int(11) NOT NULL,
  `hssOther1` int(11) NOT NULL,
  `hssOther2` int(11) NOT NULL,
  PRIMARY KEY (`hssID`),
  UNIQUE KEY `hssHostID` (`hssHostID`),
  KEY `new_index` (`hssHostID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `hosts` (
  `hostID` int(11) NOT NULL AUTO_INCREMENT,
  `hostName` varchar(16) NOT NULL,
  `hostDesc` longtext NOT NULL,
  `hostIP` varchar(25) NOT NULL,
  `hostImage` int(11) NOT NULL,
  `hostBuilding` int(11) NOT NULL,
  `hostCreateDate` timestamp NOT NULL DEFAULT current_timestamp(),
  `hostLastDeploy` datetime NOT NULL,
  `hostCreateBy` varchar(50) NOT NULL,
  `hostUseAD` char(1) NOT NULL,
  `hostADDomain` varchar(250) NOT NULL,
  `hostADOU` longtext NOT NULL,
  `hostADUser` varchar(250) NOT NULL,
  `hostADPass` varchar(250) NOT NULL,
  `hostADPassLegacy` longtext NOT NULL,
  `hostProductKey` longtext DEFAULT NULL,
  `hostPrinterLevel` varchar(2) NOT NULL,
  `hostKernelArgs` varchar(250) NOT NULL,
  `hostKernel` varchar(250) NOT NULL,
  `hostDevice` varchar(250) NOT NULL,
  `hostInit` longtext DEFAULT NULL,
  `hostPending` enum('0','1') NOT NULL,
  `hostPubKey` longtext NOT NULL,
  `hostSecToken` longtext NOT NULL,
  `hostSecTime` timestamp NOT NULL,
  `hostPingCode` varchar(20) DEFAULT NULL,
  `hostExitBios` longtext DEFAULT NULL,
  `hostExitEfi` longtext DEFAULT NULL,
  `hostEnforce` enum('0','1') NOT NULL DEFAULT '1',
  `hostInfoKey` varchar(255) DEFAULT NULL,
  `hostInfoLock` tinyint(1) DEFAULT 0,
  `hostSecTokenPrev` longtext NOT NULL,
  PRIMARY KEY (`hostID`),
  UNIQUE KEY `hostName` (`hostName`),
  KEY `new_index` (`hostName`),
  KEY `new_index1` (`hostIP`),
  KEY `new_index4` (`hostUseAD`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `imageGroupAssoc` (
  `igaID` mediumint(9) NOT NULL AUTO_INCREMENT,
  `igaImageID` mediumint(9) NOT NULL,
  `igaStorageGroupID` mediumint(9) NOT NULL,
  `igaPrimary` enum('0','1') NOT NULL,
  PRIMARY KEY (`igaID`),
  UNIQUE KEY `igaImageID` (`igaImageID`,`igaStorageGroupID`),
  UNIQUE KEY `igaImageID_2` (`igaImageID`,`igaStorageGroupID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `imagePartitionTypes` (
  `imagePartitionTypeID` mediumint(9) NOT NULL AUTO_INCREMENT,
  `imagePartitionTypeName` varchar(100) NOT NULL,
  `imagePartitionTypeValue` varchar(10) NOT NULL,
  PRIMARY KEY (`imagePartitionTypeID`),
  UNIQUE KEY `imagePartitionTypeName` (`imagePartitionTypeName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `imageTypes` (
  `imageTypeID` mediumint(9) NOT NULL AUTO_INCREMENT,
  `imageTypeName` varchar(100) NOT NULL,
  `imageTypeValue` varchar(10) NOT NULL,
  PRIMARY KEY (`imageTypeID`),
  UNIQUE KEY `imageTypeValue` (`imageTypeValue`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `images` (
  `imageID` int(11) NOT NULL AUTO_INCREMENT,
  `imageName` varchar(40) NOT NULL,
  `imageDesc` longtext NOT NULL,
  `imagePath` longtext NOT NULL,
  `imageProtect` mediumint(9) NOT NULL,
  `imageMagnetUri` longtext NOT NULL,
  `imageDateTime` timestamp NOT NULL DEFAULT current_timestamp(),
  `imageCreateBy` varchar(50) NOT NULL,
  `imageBuilding` int(11) NOT NULL,
  `imageSize` varchar(255) NOT NULL,
  `imageTypeID` mediumint(9) NOT NULL,
  `imagePartitionTypeID` mediumint(9) NOT NULL,
  `imageOSID` mediumint(9) NOT NULL,
  `imageFormat` char(1) DEFAULT NULL,
  `imageLastDeploy` datetime NOT NULL,
  `imageCompress` int(11) DEFAULT NULL,
  `imageEnabled` enum('0','1') NOT NULL DEFAULT '1',
  `imageReplicate` enum('0','1') NOT NULL DEFAULT '1',
  `imageServerSize` bigint(20) unsigned NOT NULL DEFAULT 0,
  PRIMARY KEY (`imageID`),
  UNIQUE KEY `imageName` (`imageName`),
  KEY `new_index` (`imageName`),
  KEY `new_index1` (`imageBuilding`),
  KEY `new_index2` (`imageTypeID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `imagingLog` (
  `ilID` int(11) NOT NULL AUTO_INCREMENT,
  `ilHostID` int(11) NOT NULL,
  `ilStartTime` datetime NOT NULL,
  `ilFinishTime` datetime NOT NULL,
  `ilImageName` varchar(64) NOT NULL,
  `ilType` varchar(64) NOT NULL,
  `ilCreatedBy` varchar(255) NOT NULL,
  PRIMARY KEY (`ilID`),
  KEY `new_index` (`ilHostID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `inventory` (
  `iID` int(11) NOT NULL AUTO_INCREMENT,
  `iHostID` int(11) NOT NULL,
  `iPrimaryUser` varchar(50) NOT NULL,
  `iOtherTag` varchar(50) NOT NULL,
  `iOtherTag1` varchar(50) NOT NULL,
  `iCreateDate` timestamp NOT NULL DEFAULT current_timestamp(),
  `iDeleteDate` datetime NOT NULL,
  `iSysman` varchar(250) NOT NULL,
  `iSysproduct` varchar(250) NOT NULL,
  `iSysversion` varchar(250) NOT NULL,
  `iSysserial` varchar(250) NOT NULL,
  `iSystype` varchar(250) NOT NULL,
  `iBiosversion` varchar(250) NOT NULL,
  `iBiosvendor` varchar(250) NOT NULL,
  `iBiosdate` varchar(250) NOT NULL,
  `iMbman` varchar(250) NOT NULL,
  `iMbproductname` varchar(250) NOT NULL,
  `iMbversion` varchar(250) NOT NULL,
  `iMbserial` varchar(250) NOT NULL,
  `iMbasset` varchar(250) NOT NULL,
  `iCpuman` varchar(250) NOT NULL,
  `iCpuversion` varchar(250) NOT NULL,
  `iCpucurrent` varchar(250) NOT NULL,
  `iCpumax` varchar(250) NOT NULL,
  `iMem` varchar(250) NOT NULL,
  `iHdmodel` varchar(250) NOT NULL,
  `iHdfirmware` varchar(250) NOT NULL,
  `iHdserial` varchar(250) NOT NULL,
  `iCaseman` varchar(250) NOT NULL,
  `iCasever` varchar(250) NOT NULL,
  `iCaseserial` varchar(250) NOT NULL,
  `iCaseasset` varchar(250) NOT NULL,
  `iSystemUUID` varchar(255) NOT NULL,
  `iGpuvendors` varchar(255) NOT NULL,
  `iGpuproducts` varchar(255) NOT NULL,
  PRIMARY KEY (`iID`),
  UNIQUE KEY `iHostID_2` (`iHostID`),
  KEY `iHostID` (`iHostID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `ipxeTable` (
  `ipxeID` mediumint(9) NOT NULL AUTO_INCREMENT,
  `ipxeProduct` longtext NOT NULL,
  `ipxeManufacturer` longtext NOT NULL,
  `ipxeFilename` longtext NOT NULL,
  `ipxeMAC` varchar(17) NOT NULL,
  `ipxeSuccess` varchar(2) NOT NULL,
  `ipxeFailure` varchar(2) NOT NULL,
  `ipxeVersion` longtext NOT NULL,
  PRIMARY KEY (`ipxeID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `keySequence` (
  `ksID` int(11) NOT NULL AUTO_INCREMENT,
  `ksValue` varchar(25) NOT NULL,
  `ksAscii` varchar(25) NOT NULL,
  PRIMARY KEY (`ksID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `moduleStatusByHost` (
  `msID` int(11) NOT NULL AUTO_INCREMENT,
  `msHostID` int(11) NOT NULL,
  `msModuleID` int(11) NOT NULL,
  `msState` varchar(1) NOT NULL,
  PRIMARY KEY (`msID`),
  UNIQUE KEY `msHostID` (`msHostID`,`msModuleID`),
  UNIQUE KEY `msHostID_2` (`msHostID`,`msModuleID`),
  KEY `new_index` (`msHostID`),
  KEY `new_index2` (`msModuleID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `modules` (
  `id` mediumint(9) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `short_name` varchar(30) NOT NULL,
  `description` text NOT NULL,
  `default` int(11) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  UNIQUE KEY `short_name` (`short_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `multicastSessions` (
  `msID` int(11) NOT NULL AUTO_INCREMENT,
  `msName` varchar(250) NOT NULL,
  `msBasePort` int(11) NOT NULL,
  `msLogPath` longtext NOT NULL,
  `msImage` longtext NOT NULL,
  `msClients` int(11) NOT NULL,
  `msSessClients` int(11) NOT NULL,
  `msInterface` varchar(250) NOT NULL,
  `msStartDateTime` datetime NOT NULL,
  `msPercent` int(11) NOT NULL,
  `msState` int(11) NOT NULL,
  `msCompleteDateTime` datetime NOT NULL,
  `msIsDD` int(11) NOT NULL,
  `msNFSGroupID` int(11) NOT NULL,
  `msAnon3` varchar(250) NOT NULL,
  `msAnon4` varchar(250) NOT NULL,
  `msAnon5` varchar(250) NOT NULL,
  `msSenderPID` int(11) NOT NULL DEFAULT 0,
  `msSenderNode` int(11) NOT NULL DEFAULT 0,
  `msSenderStart` datetime DEFAULT NULL,
  PRIMARY KEY (`msID`),
  KEY `new_index` (`msNFSGroupID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `multicastSessionsAssoc` (
  `msaID` int(11) NOT NULL AUTO_INCREMENT,
  `msID` int(11) NOT NULL,
  `tID` int(11) NOT NULL,
  PRIMARY KEY (`msaID`),
  UNIQUE KEY `msID` (`msID`,`tID`),
  KEY `new_index` (`msID`),
  KEY `new_index1` (`tID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `nfsFailures` (
  `nfID` int(11) NOT NULL AUTO_INCREMENT,
  `nfNodeID` int(11) NOT NULL,
  `nfTaskID` int(11) NOT NULL,
  `nfHostID` int(11) NOT NULL,
  `nfGroupID` int(11) NOT NULL,
  `nfDateTime` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`nfID`),
  UNIQUE KEY `nfNodeID` (`nfNodeID`,`nfHostID`,`nfTaskID`),
  KEY `new_index` (`nfNodeID`),
  KEY `new_index1` (`nfTaskID`),
  KEY `new_index2` (`nfHostID`),
  KEY `new_index3` (`nfGroupID`),
  KEY `new_index4` (`nfDateTime`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `nfsGroupMembers` (
  `ngmID` int(11) NOT NULL AUTO_INCREMENT,
  `ngmMemberName` varchar(250) NOT NULL,
  `ngmMemberDescription` longtext NOT NULL,
  `ngmIsMasterNode` char(1) NOT NULL,
  `ngmGroupID` int(11) NOT NULL,
  `ngmRootPath` longtext NOT NULL,
  `ngmSSLPath` longtext NOT NULL,
  `ngmFTPPath` longtext NOT NULL,
  `ngmMaxBitrate` varchar(25) DEFAULT NULL,
  `ngmHelloInterval` varchar(8) DEFAULT NULL,
  `ngmGraphColor` varchar(6) DEFAULT NULL,
  `ngmSnapinPath` longtext NOT NULL,
  `ngmIsEnabled` char(1) NOT NULL,
  `ngmHostname` varchar(250) NOT NULL,
  `ngmMaxClients` int(11) NOT NULL,
  `ngmBandwidthLimit` int(20) NOT NULL,
  `ngmUser` varchar(250) NOT NULL,
  `ngmPass` varchar(250) NOT NULL,
  `ngmKey` varchar(250) NOT NULL,
  `ngmInterface` varchar(25) NOT NULL DEFAULT 'dummy-storage_interface',
  `ngmGraphEnabled` enum('0','1') NOT NULL DEFAULT '1',
  `ngmWebroot` longtext NOT NULL,
  PRIMARY KEY (`ngmID`),
  UNIQUE KEY `ngmMemberName` (`ngmMemberName`),
  UNIQUE KEY `ngmMemberName_2` (`ngmMemberName`),
  KEY `new_index` (`ngmMemberName`),
  KEY `new_index2` (`ngmIsMasterNode`),
  KEY `new_index3` (`ngmGroupID`),
  KEY `new_index4` (`ngmIsEnabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `nfsGroups` (
  `ngID` int(11) NOT NULL AUTO_INCREMENT,
  `ngName` varchar(250) NOT NULL,
  `ngDesc` longtext NOT NULL,
  PRIMARY KEY (`ngID`),
  UNIQUE KEY `ngName` (`ngName`),
  UNIQUE KEY `ngName_2` (`ngName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `notifyEvents` (
  `neID` int(11) NOT NULL AUTO_INCREMENT,
  `neName` varchar(255) NOT NULL,
  PRIMARY KEY (`neID`),
  UNIQUE KEY `name` (`neName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `os` (
  `osID` mediumint(9) NOT NULL AUTO_INCREMENT,
  `osName` varchar(30) NOT NULL,
  `osDescription` text NOT NULL,
  PRIMARY KEY (`osID`),
  UNIQUE KEY `osName` (`osName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `oui` (
  `ouiID` int(11) NOT NULL AUTO_INCREMENT,
  `ouiMACPrefix` varchar(8) NOT NULL,
  `ouiMan` varchar(254) NOT NULL,
  PRIMARY KEY (`ouiID`),
  UNIQUE KEY `ouiMACPrefix` (`ouiMACPrefix`,`ouiMan`),
  KEY `idxMac` (`ouiMACPrefix`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `plugins` (
  `pID` int(11) NOT NULL AUTO_INCREMENT,
  `pName` varchar(100) NOT NULL,
  `pState` char(1) NOT NULL,
  `pInstalled` char(1) NOT NULL,
  `pVersion` varchar(100) NOT NULL,
  `pAnon1` varchar(100) NOT NULL,
  `pAnon2` varchar(100) NOT NULL,
  `pAnon3` varchar(100) NOT NULL,
  `pAnon4` varchar(100) NOT NULL,
  `pAnon5` varchar(100) NOT NULL,
  PRIMARY KEY (`pID`),
  UNIQUE KEY `pName` (`pName`),
  KEY `new_index` (`pName`),
  KEY `new_index1` (`pState`),
  KEY `new_index2` (`pInstalled`),
  KEY `new_index3` (`pVersion`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `powerManagement` (
  `pmID` int(11) NOT NULL AUTO_INCREMENT,
  `pmHostID` int(11) NOT NULL,
  `pmMin` varchar(50) NOT NULL,
  `pmHour` varchar(50) NOT NULL,
  `pmDom` varchar(50) NOT NULL,
  `pmMonth` varchar(50) NOT NULL,
  `pmDow` varchar(50) NOT NULL,
  `pmAction` enum('shutdown','reboot','wol') NOT NULL,
  `pmOndemand` enum('0','1') NOT NULL,
  PRIMARY KEY (`pmID`),
  UNIQUE KEY `cron` (`pmHostID`,`pmMin`,`pmHour`,`pmDom`,`pmMonth`,`pmDow`,`pmAction`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `printerAssoc` (
  `paID` int(11) NOT NULL AUTO_INCREMENT,
  `paHostID` int(11) NOT NULL,
  `paPrinterID` int(11) NOT NULL,
  `paIsDefault` varchar(2) NOT NULL,
  `paAnon1` varchar(2) NOT NULL,
  `paAnon2` varchar(2) NOT NULL,
  `paAnon3` varchar(2) NOT NULL,
  `paAnon4` varchar(2) NOT NULL,
  `paAnon5` varchar(2) NOT NULL,
  PRIMARY KEY (`paID`),
  UNIQUE KEY `paHostID` (`paHostID`,`paPrinterID`),
  KEY `new_index1` (`paHostID`),
  KEY `new_index2` (`paPrinterID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `printers` (
  `pID` int(11) NOT NULL AUTO_INCREMENT,
  `pPort` longtext NOT NULL,
  `pDefFile` longtext NOT NULL,
  `pModel` varchar(250) NOT NULL,
  `pAlias` varchar(250) NOT NULL,
  `pConfig` varchar(10) NOT NULL,
  `pConfigFile` varchar(255) NOT NULL,
  `pIP` varchar(255) NOT NULL,
  `pAnon2` varchar(10) NOT NULL,
  `pAnon3` varchar(10) NOT NULL,
  `pAnon4` varchar(10) NOT NULL,
  `pAnon5` varchar(10) NOT NULL,
  `pDesc` longtext DEFAULT NULL,
  PRIMARY KEY (`pID`),
  UNIQUE KEY `pAlias` (`pAlias`),
  KEY `new_index1` (`pModel`),
  KEY `new_index2` (`pAlias`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `pxeMenu` (
  `pxeID` mediumint(9) NOT NULL AUTO_INCREMENT,
  `pxeName` varchar(100) NOT NULL,
  `pxeDesc` longtext NOT NULL,
  `pxeParams` longtext NOT NULL,
  `pxeRegOnly` int(11) NOT NULL DEFAULT 0,
  `pxeArgs` varchar(250) DEFAULT NULL,
  `pxeDefault` int(11) NOT NULL DEFAULT 0,
  `pxeHotKeyEnable` enum('0','1') NOT NULL,
  `pxeKeySequence` varchar(255) NOT NULL,
  PRIMARY KEY (`pxeID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `scheduledTasks` (
  `stID` int(11) NOT NULL AUTO_INCREMENT,
  `stName` varchar(240) NOT NULL,
  `stDesc` longtext NOT NULL,
  `stType` varchar(24) NOT NULL,
  `stTaskTypeID` mediumint(9) NOT NULL,
  `stMinute` varchar(240) NOT NULL,
  `stHour` varchar(240) NOT NULL,
  `stDOM` varchar(240) NOT NULL,
  `stMonth` varchar(240) NOT NULL,
  `stDOW` varchar(240) NOT NULL,
  `stIsGroup` varchar(2) NOT NULL DEFAULT '0',
  `stGroupHostID` int(11) NOT NULL,
  `stImageID` int(11) NOT NULL,
  `stShutDown` varchar(2) NOT NULL,
  `stOther1` varchar(240) NOT NULL,
  `stOther2` varchar(240) NOT NULL,
  `stOther3` varchar(240) NOT NULL,
  `stOther4` varchar(240) NOT NULL,
  `stOther5` varchar(240) NOT NULL,
  `stDateTime` bigint(20) unsigned NOT NULL DEFAULT 0,
  `stActive` varchar(2) NOT NULL DEFAULT '1',
  PRIMARY KEY (`stID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `schemaVersion` (
  `vID` int(11) NOT NULL AUTO_INCREMENT,
  `vValue` int(11) NOT NULL,
  PRIMARY KEY (`vID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `snapinAssoc` (
  `saID` int(11) NOT NULL AUTO_INCREMENT,
  `saHostID` int(11) NOT NULL,
  `saSnapinID` int(11) NOT NULL,
  PRIMARY KEY (`saID`),
  UNIQUE KEY `saHostID` (`saHostID`,`saSnapinID`),
  UNIQUE KEY `saSnapinID` (`saSnapinID`,`saHostID`),
  KEY `new_index` (`saHostID`),
  KEY `new_index1` (`saSnapinID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `snapinGroupAssoc` (
  `sgaID` mediumint(9) NOT NULL AUTO_INCREMENT,
  `sgaSnapinID` mediumint(9) NOT NULL,
  `sgaStorageGroupID` mediumint(9) NOT NULL,
  `sgaPrimary` enum('0','1') NOT NULL,
  PRIMARY KEY (`sgaID`),
  UNIQUE KEY `sgaSnapinID` (`sgaSnapinID`,`sgaStorageGroupID`),
  UNIQUE KEY `sgaStorageGroupID` (`sgaStorageGroupID`,`sgaSnapinID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `snapinJobs` (
  `sjID` int(11) NOT NULL AUTO_INCREMENT,
  `sjHostID` int(11) NOT NULL,
  `sjStateID` int(11) NOT NULL,
  `sjCreateTime` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`sjID`),
  KEY `new_index` (`sjHostID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `snapinTasks` (
  `stID` int(11) NOT NULL AUTO_INCREMENT,
  `stJobID` int(11) NOT NULL,
  `stState` int(11) NOT NULL,
  `stCheckinDate` timestamp NOT NULL DEFAULT current_timestamp(),
  `stCompleteDate` datetime NOT NULL,
  `stSnapinID` int(11) NOT NULL,
  `stReturnCode` int(11) NOT NULL,
  `stReturnDetails` varchar(250) NOT NULL,
  PRIMARY KEY (`stID`),
  UNIQUE KEY `stJobID` (`stJobID`,`stSnapinID`),
  KEY `new_index` (`stJobID`),
  KEY `new_index1` (`stState`),
  KEY `new_index2` (`stSnapinID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `snapins` (
  `sID` int(11) NOT NULL AUTO_INCREMENT,
  `sName` varchar(200) NOT NULL,
  `sDesc` longtext NOT NULL,
  `sFilePath` longtext NOT NULL,
  `sArgs` longtext NOT NULL,
  `sCreateDate` timestamp NOT NULL DEFAULT current_timestamp(),
  `sCreator` varchar(200) NOT NULL,
  `sReboot` varchar(1) NOT NULL,
  `sRunWith` varchar(245) NOT NULL,
  `sRunWithArgs` varchar(200) NOT NULL,
  `sAnon3` varchar(45) NOT NULL,
  `snapinProtect` mediumint(9) NOT NULL,
  `sEnabled` enum('0','1') NOT NULL DEFAULT '1',
  `sReplicate` enum('0','1') NOT NULL DEFAULT '1',
  `sShutdown` enum('0','1') NOT NULL DEFAULT '0',
  `sHideLog` enum('0','1') NOT NULL DEFAULT '0',
  `sTimeout` int(11) NOT NULL DEFAULT 0,
  `sPackType` enum('0','1') NOT NULL DEFAULT '0',
  `sHash` varchar(255) NOT NULL DEFAULT '',
  `sSize` bigint(20) NOT NULL DEFAULT 0,
  PRIMARY KEY (`sID`),
  UNIQUE KEY `sName` (`sName`),
  KEY `new_index` (`sName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `supportedOS` (
  `osID` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `osName` varchar(150) NOT NULL,
  `osValue` int(10) unsigned NOT NULL,
  PRIMARY KEY (`osID`),
  UNIQUE KEY `osName` (`osName`),
  KEY `new_index` (`osValue`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `taskLog` (
  `id` mediumint(9) NOT NULL AUTO_INCREMENT,
  `taskID` mediumtext NOT NULL,
  `taskStateID` mediumint(9) NOT NULL,
  `ip` varchar(15) NOT NULL,
  `createTime` timestamp NOT NULL DEFAULT current_timestamp(),
  `createdBy` varchar(30) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `taskStates` (
  `tsID` int(11) NOT NULL AUTO_INCREMENT,
  `tsName` varchar(30) NOT NULL,
  `tsDescription` text NOT NULL,
  `tsOrder` tinyint(4) NOT NULL DEFAULT 0,
  `tsIcon` varchar(255) NOT NULL,
  PRIMARY KEY (`tsID`),
  UNIQUE KEY `tsName` (`tsName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `taskTypes` (
  `ttID` mediumint(9) NOT NULL AUTO_INCREMENT,
  `ttName` varchar(30) NOT NULL,
  `ttDescription` text NOT NULL,
  `ttIcon` varchar(30) NOT NULL,
  `ttKernel` varchar(100) NOT NULL,
  `ttKernelArgs` text NOT NULL,
  `ttType` enum('fog','user') NOT NULL DEFAULT 'user',
  `ttIsAdvanced` enum('0','1') NOT NULL DEFAULT '0',
  `ttIsAccess` enum('both','host','group') NOT NULL DEFAULT 'both',
  `ttInitrd` longtext NOT NULL,
  PRIMARY KEY (`ttID`),
  UNIQUE KEY `ttName` (`ttName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tasks` (
  `taskID` int(11) NOT NULL AUTO_INCREMENT,
  `taskName` varchar(250) NOT NULL,
  `taskCreateTime` timestamp NOT NULL DEFAULT current_timestamp(),
  `taskCheckIn` datetime NOT NULL,
  `taskHostID` int(11) NOT NULL,
  `taskImageID` int(11) NOT NULL,
  `taskStateID` int(11) NOT NULL,
  `taskIsDebug` mediumint(9) NOT NULL,
  `taskCreateBy` varchar(200) NOT NULL,
  `taskForce` varchar(1) NOT NULL,
  `taskScheduledStartTime` datetime NOT NULL,
  `taskTypeID` mediumint(9) NOT NULL,
  `taskPCT` int(10) unsigned zerofill NOT NULL,
  `taskBPM` varchar(250) NOT NULL,
  `taskTimeElapsed` varchar(250) NOT NULL,
  `taskTimeRemaining` varchar(250) NOT NULL,
  `taskDataCopied` varchar(250) NOT NULL,
  `taskPercentText` varchar(250) NOT NULL,
  `taskDataTotal` varchar(250) NOT NULL,
  `taskNFSGroupID` int(11) NOT NULL,
  `taskNFSMemberID` int(11) NOT NULL,
  `taskNFSFailures` char(1) NOT NULL,
  `taskLastMemberID` int(11) NOT NULL,
  `taskWOL` enum('0','1') NOT NULL,
  `taskPassreset` varchar(250) NOT NULL,
  `taskShutdown` char(1) NOT NULL,
  PRIMARY KEY (`taskID`),
  KEY `new_index` (`taskHostID`),
  KEY `new_index1` (`taskCheckIn`),
  KEY `new_index2` (`taskStateID`),
  KEY `new_index3` (`taskForce`),
  KEY `new_index4` (`taskTypeID`),
  KEY `new_index5` (`taskNFSGroupID`),
  KEY `new_index6` (`taskNFSMemberID`),
  KEY `new_index7` (`taskNFSFailures`),
  KEY `new_index8` (`taskLastMemberID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `userCleanup` (
  `ucID` int(11) NOT NULL AUTO_INCREMENT,
  `ucName` varchar(254) NOT NULL,
  PRIMARY KEY (`ucID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `userTracking` (
  `utID` int(11) NOT NULL AUTO_INCREMENT,
  `utHostID` int(11) NOT NULL,
  `utUserName` varchar(50) NOT NULL,
  `utAction` varchar(2) NOT NULL,
  `utDateTime` timestamp NOT NULL DEFAULT current_timestamp(),
  `utDesc` varchar(250) NOT NULL,
  `utDate` date NOT NULL,
  `utAnon3` varchar(2) NOT NULL,
  PRIMARY KEY (`utID`),
  KEY `new_index` (`utHostID`),
  KEY `new_index1` (`utUserName`),
  KEY `new_index2` (`utAction`),
  KEY `new_index3` (`utDateTime`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `uId` int(11) NOT NULL AUTO_INCREMENT,
  `uName` varchar(40) NOT NULL,
  `uPass` longtext NOT NULL,
  `uCreateDate` datetime NOT NULL,
  `uCreateBy` varchar(40) NOT NULL,
  `uType` int(11) NOT NULL,
  `uDisplay` varchar(255) NOT NULL,
  `uAllowAPI` enum('0','1') NOT NULL DEFAULT '1',
  `uAPIToken` varchar(255) NOT NULL,
  PRIMARY KEY (`uId`),
  UNIQUE KEY `name` (`uName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `virus` (
  `vID` int(11) NOT NULL AUTO_INCREMENT,
  `vName` varchar(250) NOT NULL,
  `vHostMAC` varchar(50) NOT NULL,
  `vOrigFile` longtext NOT NULL,
  `vDateTime` timestamp NOT NULL DEFAULT current_timestamp(),
  `vMode` varchar(5) NOT NULL,
  `vAnon2` varchar(50) NOT NULL,
  PRIMARY KEY (`vID`),
  KEY `new_index` (`vHostMAC`),
  KEY `new_index2` (`vDateTime`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_general_ci ROW_FORMAT=DYNAMIC;
/*!40101 SET character_set_client = @saved_cs_client */;
/*M!999999\- enable the sandbox mode */ 
INSERT INTO `globalSettings` VALUES (1,'FOG_TFTP_HOST','Hostname or IP address of the TFTP Server.','dummy-tftp_host','TFTP Server');
INSERT INTO `globalSettings` VALUES (2,'FOG_TFTP_FTP_USERNAME','Username used to access the tftp server via ftp.','dummy-storage_ftp_username','TFTP Server');
INSERT INTO `globalSettings` VALUES (3,'FOG_TFTP_FTP_PASSWORD','Password used to access the tftp server via ftp.','dummy-tftp_ftp_password','TFTP Server');
INSERT INTO `globalSettings` VALUES (4,'FOG_TFTP_PXE_KERNEL_DIR','Location of kernel files on the PXE server.','/home/user/fogproject/fogproject/packages/web/service/ipxe/','TFTP Server');
INSERT INTO `globalSettings` VALUES (5,'FOG_TFTP_PXE_KERNEL','Location of kernel file on the PXE server,this should point to the kernel itself.','bzImage','TFTP Server');
INSERT INTO `globalSettings` VALUES (6,'FOG_KERNEL_RAMDISK_SIZE','This setting defines the amount of physical memory (in KB) you want to use for the boot image. This setting needs to be larger than the boot image and smaller that the total physical memory on the client.','275000','TFTP Server');
INSERT INTO `globalSettings` VALUES (7,'FOG_USE_SLOPPY_NAME_LOOKUPS','The settings was added to workaround a partial implementation of DHCP in the boot image. The boot image is unable to obtain a DNS server address from the DHCP server, so what this setting will do is resolve any hostnames to IP address on the FOG server before writing the config files.','1','General Settings');
INSERT INTO `globalSettings` VALUES (8,'FOG_MEMTEST_KERNEL','The settings defines where the memtest boot image/kernel is located.','memtest.bin','General Settings');
INSERT INTO `globalSettings` VALUES (9,'FOG_PXE_BOOT_IMAGE','The settings defines where the fog boot file system image is located.','init.xz','TFTP Server');
INSERT INTO `globalSettings` VALUES (15,'FOG_NFS_BANDWIDTHPATH','This setting defines the web page used to acquire the bandwidth used by the nfs server.','dummy-storage_bandwidthpath','NFS Server');
INSERT INTO `globalSettings` VALUES (16,'FOG_CAPTURERESIZEPCT','This setting defines the amount of padding applied to a partition before attempting resize the ntfs volume and capturing it.','5','General Settings');
INSERT INTO `globalSettings` VALUES (17,'FOG_WEB_HOST','This setting defines the hostname or ip address of the web server used with fog.','dummy-web_host','Web Server');
INSERT INTO `globalSettings` VALUES (18,'FOG_WEB_ROOT','This setting defines the path to the fog webserver\'s root directory.','/fog/','Web Server');
INSERT INTO `globalSettings` VALUES (22,'FOG_SNAPINDIR','This setting defines the location of the snapin files. These files must be hosted on the web server.','dummy-snapindir','FOG Client - Snapins');
INSERT INTO `globalSettings` VALUES (23,'FOG_CHECKIN_TIMEOUT','This setting defines the amount of time between client checks to determine if they are active clients.','600','General Settings');
INSERT INTO `globalSettings` VALUES (24,'FOG_USER_MINPASSLENGTH','This setting defines the minimum number of characters in a user\'s password.','4','User Management');
INSERT INTO `globalSettings` VALUES (25,'FOG_NFS_ETH_MONITOR','This setting defines which interface is monitored for traffic summaries.','dummy-nfs_eth_monitor','NFS Server');
INSERT INTO `globalSettings` VALUES (26,'FOG_UDPCAST_INTERFACE','This setting defines the interface used in multicast communications.','dummy-udpcast_interface','Multicast Settings');
INSERT INTO `globalSettings` VALUES (27,'FOG_UDPCAST_STARTINGPORT','This setting defines the starting port number used in multicast communications. This starting port number must be an even number.','63100','Multicast Settings');
INSERT INTO `globalSettings` VALUES (28,'FOG_MULTICAST_MAX_SESSIONS','This setting defines the maximum number of multicast sessions that can be running at one time.','64','Multicast Settings');
INSERT INTO `globalSettings` VALUES (30,'FOG_REPORT_DIR','This setting defines the location on the web server of the FOG reports.','dummy-fog_report_dir','Web Server');
INSERT INTO `globalSettings` VALUES (31,'FOG_THEME','This setting defines what css style sheet and theme to use for FOG.','default/fog.css','Web Server');
INSERT INTO `globalSettings` VALUES (32,'FOG_CAPTUREIGNOREPAGEHIBER','This setting defines if you would like to remove hibernate and swap files before capturing a Windows image.','1','General Settings');
INSERT INTO `globalSettings` VALUES (33,'FOG_CLIENT_DIRECTORYCLEANER_ENABLED','This setting defines if the Windows Service module directory cleaner should be enabled on client computers. This service is clean out the contents of a directory on when a user logs out of the workstation. (Valid values: 0 or 1).','1','FOG Client - Directory Cleaner');
INSERT INTO `globalSettings` VALUES (34,'FOG_USE_ANIMATION_EFFECTS','This setting defines if the FOG management portal uses animation effects on it. Valid values are 0 or 1','1','General Settings');
INSERT INTO `globalSettings` VALUES (35,'FOG_CLIENT_USERCLEANUP_ENABLED','This setting defines if user cleanup should be enabled. The User Cleanup module will remove all local windows users from the workstation on log off accept for users that are whitelisted. (Valid values are 0 or 1)','0','FOG Client - User Cleanup');
INSERT INTO `globalSettings` VALUES (36,'FOG_CLIENT_GREENFOG_ENABLED','This setting defines if the green fog module should be enabled. The green fog module will shutdown or restart a computer at a set time. (Valid values are 0 or 1)','1','FOG Client - Green Fog');
INSERT INTO `globalSettings` VALUES (37,'FOG_CLIENT_AUTOLOGOFF_ENABLED','This setting defines if the auto log off module should be enabled. This module will log off any active user after X minutes of inactivity.(Valid values are 0 or 1)','1','FOG Client - Auto Log Off');
INSERT INTO `globalSettings` VALUES (38,'FOG_CLIENT_DISPLAYMANAGER_ENABLED','This setting defines if the fog display manager should be active. The fog display manager will reset the clients screen resolution to a fixed size on log off and on computer start up.(Valid values are 0 or 1)','0','FOG Client - Display Manager');
INSERT INTO `globalSettings` VALUES (39,'FOG_CLIENT_DISPLAYMANAGER_X','This setting defines the default width in pixels to reset the computer display to with the fog display manager service.','1024','FOG Client - Display Manager');
INSERT INTO `globalSettings` VALUES (40,'FOG_CLIENT_DISPLAYMANAGER_Y','This setting defines the default height in pixels to reset the computer display to with the fog display manager service.','768','FOG Client - Display Manager');
INSERT INTO `globalSettings` VALUES (41,'FOG_CLIENT_DISPLAYMANAGER_R','This setting defines the default refresh rate to reset the computer display to with the fog display manager service.','60','FOG Client - Display Manager');
INSERT INTO `globalSettings` VALUES (42,'FOG_CLIENT_AUTOLOGOFF_BGIMAGE','This setting defines the location of the background image used in the auto log off module. The image should be 300px x 300px. This image can be located locally (such as c:\\images\\myimage.jpg) or on a web server (such as http://freeghost.sf.net/images/image.jpg)','c:\\program files\\fog\\images\\alo-bg.jpg','FOG Client - Auto Log Off');
INSERT INTO `globalSettings` VALUES (43,'FOG_CLIENT_AUTOLOGOFF_MIN','This setting defines the number of minutes to wait before logging a user off of a PC.(Value of 0 will disable this module.)','0','FOG Client - Auto Log Off');
INSERT INTO `globalSettings` VALUES (44,'FOG_KEYMAP','This setting defines the keymap used on the client boot image.','','General Settings');
INSERT INTO `globalSettings` VALUES (45,'FOG_CLIENT_HOSTNAMECHANGER_ENABLED','This setting defines if the fog hostname changer should be globally active. (Valid values are 0 or 1)','1','FOG Client - Hostname Changer');
INSERT INTO `globalSettings` VALUES (46,'FOG_CLIENT_SNAPIN_ENABLED','This setting defines if the fog snapin installer should be globally active. (Valid values are 0 or 1)','1','FOG Client - Snapins');
INSERT INTO `globalSettings` VALUES (47,'FOG_KERNEL_ARGS','This setting allows you to add additional kernel arguments to the client boot image. This setting is global for all hosts.','','General Settings');
INSERT INTO `globalSettings` VALUES (48,'FOG_CLIENT_CLIENTUPDATER_ENABLED','This setting defines if the fog client updater should be globally active. (Valid values are 0 or 1)','1','FOG Client - Client Updater');
INSERT INTO `globalSettings` VALUES (49,'FOG_CLIENT_HOSTREGISTER_ENABLED','This setting defines if the fog host register should be globally active. (Valid values are 0 or 1)','1','FOG Client - Host Register');
INSERT INTO `globalSettings` VALUES (50,'FOG_CLIENT_PRINTERMANAGER_ENABLED','This setting defines if the fog printer manager should be globally active. (Valid values are 0 or 1)','1','FOG Client - Printer Manager');
INSERT INTO `globalSettings` VALUES (51,'FOG_CLIENT_TASKREBOOT_ENABLED','This setting defines if the fog task reboot should be globally active. (Valid values are 0 or 1)','1','FOG Client - Task Reboot');
INSERT INTO `globalSettings` VALUES (52,'FOG_CLIENT_USERTRACKER_ENABLED','This setting defines if the fog user tracker should be globally active. (Valid values are 0 or 1)','1','FOG Client - User Tracker');
INSERT INTO `globalSettings` VALUES (53,'FOG_AD_DEFAULT_DOMAINNAME','This setting defines the default value to populate the host\'s Active Directory domain name value.','','Active Directory Defaults');
INSERT INTO `globalSettings` VALUES (54,'FOG_AD_DEFAULT_OU','This setting defines the default value to populate the host\'s Active Directory OU value.','','Active Directory Defaults');
INSERT INTO `globalSettings` VALUES (55,'FOG_AD_DEFAULT_USER','This setting defines the default value to populate the host\'s Active Directory user name value.','','Active Directory Defaults');
INSERT INTO `globalSettings` VALUES (56,'FOG_AD_DEFAULT_PASSWORD','This setting defines the default value to populate the host\'s Active Directory password value. This setting will encrypt and store then encrypted value of the plain text value entered in this field automatically.','','Active Directory Defaults');
INSERT INTO `globalSettings` VALUES (57,'FOG_UTIL_DIR','This setting defines the location of the fog utility directory.','/opt/fog/utils','FOG Utils');
INSERT INTO `globalSettings` VALUES (58,'FOG_PLUGINSYS_ENABLED','This setting defines if the fog plugin system should be enabled.','0','Plugin System');
INSERT INTO `globalSettings` VALUES (59,'FOG_PLUGINSYS_DIR','This setting defines the base location of fog plugins.','./plugins','Plugin System');
INSERT INTO `globalSettings` VALUES (60,'FOG_STORAGENODE_MYSQLUSER','This setting defines the username the storage nodes should use to connect to the fog server.','fogstorage','FOG Storage Nodes');
INSERT INTO `globalSettings` VALUES (63,'FOG_VIEW_DEFAULT_SCREEN','This setting defines which page is displayed in each section, valid settings includes <b>LIST</b> and <b>SEARCH</b>.','SEARCH','FOG View Settings');
INSERT INTO `globalSettings` VALUES (64,'FOG_PXE_MENU_TIMEOUT','This setting defines the default value for the pxe menu timeout.','3','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (65,'FOG_PROXY_IP','This setting defines the proxy ip address to use.','','Proxy Settings');
INSERT INTO `globalSettings` VALUES (66,'FOG_PROXY_PORT','This setting defines the proxy port address to use.','','Proxy Settings');
INSERT INTO `globalSettings` VALUES (67,'FOG_UTIL_BASE','This setting defines the location of util base, which is typically /opt/fog/','/opt/fog/','FOG Utils');
INSERT INTO `globalSettings` VALUES (68,'FOG_PXE_MENU_HIDDEN','This setting defines if you would like the FOG pxe menu hidden or displayed','0','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (69,'FOG_PXE_ADVANCED','This setting defines if you would like to append any settings to the end of your PXE default file.','','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (70,'FOG_USE_LEGACY_TASKLIST','This setting defines if you would like to use the legacy active tasks window. Note: The legacy screen will no longer be updated.','0','General Settings');
INSERT INTO `globalSettings` VALUES (71,'FOG_QUICKREG_AUTOPOP','Enable FOG Quick Registration auto population feature (0 = disabled, 1=enabled). If this feature is enabled, FOG will auto populate the host settings and automatically image the computer without any user intervention.','0','FOG Quick Registration');
INSERT INTO `globalSettings` VALUES (72,'FOG_QUICKREG_IMG_ID','FOG Quick Registration Image ID.','-1','FOG Quick Registration');
INSERT INTO `globalSettings` VALUES (73,'FOG_QUICKREG_OS_ID','FOG Quick Registration OS ID.','-1','FOG Quick Registration');
INSERT INTO `globalSettings` VALUES (74,'FOG_QUICKREG_SYS_NAME','FOG Quick Registration system name template. Use * for the autonumber feature.','PC-*','FOG Quick Registration');
INSERT INTO `globalSettings` VALUES (75,'FOG_QUICKREG_SYS_NUMBER','FOG Quick Registration system name auto number.','1','FOG Quick Registration');
INSERT INTO `globalSettings` VALUES (76,'FOG_DEFAULT_LOCALE','Default language code to use for FOG.','en','General Settings');
INSERT INTO `globalSettings` VALUES (77,'FOG_HOST_LOOKUP','Should FOG attempt to see if a host is active and display it as part of the UI?','1','General Settings');
INSERT INTO `globalSettings` VALUES (78,'FOG_UUID','This is a unique ID that is used to identify your installation. In most cases you do not want to change this value.','6a9bd8d8caf322.74472491','General Settings');
INSERT INTO `globalSettings` VALUES (79,'FOG_QUICKREG_MAX_PENDING_MACS','This setting defines how many mac addresses will be stored in the pending mac address table for each host.','4','FOG Client - Host Register');
INSERT INTO `globalSettings` VALUES (80,'FOG_QUICKREG_PENDING_MAC_FILTER','This is a list of MAC address fragments that is used to filter out pending mac address requests. For example, if you don\'t want to see pending mac address requests for VMWare NICs then you could filter by 00:05:69. This filter is comma separated, and is used like a *starts with* filter.','','FOG Client - Host Register');
INSERT INTO `globalSettings` VALUES (81,'FOG_ADVANCED_STATISTICS','Enable the collection and display of advanced statistics. This information WILL be sent to a remote server! This information is used by the FOG team to see how FOG is being used. The information that will be sent includes the server\'s UUID value, the number of hosts present in FOG, and number of images on your FOG server and well as total image space used. (0 = disabled, 1 = enabled).','0','General Settings');
INSERT INTO `globalSettings` VALUES (82,'FOG_DISABLE_CHKDSK','This is an experimental feature that will can be used to not set the dirty flag on a NTFS partition after resizing it. It is recommended to you run chkdsk. (0 = runs chkdsk, 1 = disables chkdsk).','1','General Settings');
INSERT INTO `globalSettings` VALUES (83,'FOG_CHANGE_HOSTNAME_EARLY','This is an experimental feature that will can be used to change the computers hostname right after imaging the box, without the need for the FOG service. (1 = enabled, 0 = disabled).','1','General Settings');
INSERT INTO `globalSettings` VALUES (84,'FOG_PIGZ_COMP','PIGZ Compression Rating','6','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (85,'FOG_KEY_SEQUENCE','Key Sequence for boot prompt.','0','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (86,'FOG_FORMAT_FLAG_IN_GUI','This setting allows you to set whether or not an image is legacy. (Valid values are 0 or 1)','0','General Settings');
INSERT INTO `globalSettings` VALUES (87,'FOG_PROXY_USERNAME','This setting defines the proxy username to use.','','Proxy Settings');
INSERT INTO `globalSettings` VALUES (88,'FOG_PROXY_PASSWORD','This setting defines the proxy password to use.','','Proxy Settings');
INSERT INTO `globalSettings` VALUES (89,'FOG_NO_MENU','This setting sets the system to no menu, if there is no task set, it boots to first device.','','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (90,'FOG_TFTP_PXE_KERNEL_32','Location of the 32 bit kernel file on the PXE server, this should point to the kernel itself.','bzImage32','TFTP Server');
INSERT INTO `globalSettings` VALUES (91,'FOG_PXE_BOOT_IMAGE_32','The settings defines where the 32 bit fog boot file system image is located.','init_32.xz','TFTP Server');
INSERT INTO `globalSettings` VALUES (92,'FOG_BOOT_EXIT_TYPE','The method of booting to the hard drive. Most will accept sanboot, but some require exit.','','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (93,'FOG_DATA_RETURNED','This setting presents the search bar if list has more returned than this number. (A value of 0 disables it)','0','FOG View Settings');
INSERT INTO `globalSettings` VALUES (94,'FOG_QUICKREG_GROUP_ASSOC','Allows a group to be assigned during quick registration. Default is no group assigned.','0','FOG Quick Registration');
INSERT INTO `globalSettings` VALUES (95,'FOG_ALWAYS_LOGGED_IN','This setting allows user to be signed in all the time or not. A value of 0 disables it.','0','Login Settings');
INSERT INTO `globalSettings` VALUES (96,'FOG_INACTIVITY_TIMEOUT','This setting allows user to be signed in all the time or not. Between 1 and 24 by hours.','1','Login Settings');
INSERT INTO `globalSettings` VALUES (97,'FOG_REGENERATE_TIMEOUT','This setting allows user to be signed in all the time or not. Between 0.25 and 24 by hours.','0.5','Login Settings');
INSERT INTO `globalSettings` VALUES (98,'FOG_ADVANCED_MENU_LOGIN','This setting enforces a login parameter to get into the advanced menu.','0','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (99,'FOG_TASK_FORCE_REBOOT','This setting enables or disables the Force reboot of tasks. This only affects if users are logged in. If users are logged in, the host will not reboot if this is disabled.','0','FOG Client - Task Reboot');
INSERT INTO `globalSettings` VALUES (100,'FOG_CLIENT_CHECKIN_TIME','This setting returns the client service checkin times to the server.','60','FOG Client');
INSERT INTO `globalSettings` VALUES (101,'FOG_UDPCAST_MAXWAIT','This setting sets the max time to wait for other clients before starting the session in minutes.','10','Multicast Settings');
INSERT INTO `globalSettings` VALUES (104,'FOG_CLIENT_MAXSIZE','This setting specifies the MAX size of the fog.log before it rolls over. It will only work for new clients.','204800000','FOG Client');
INSERT INTO `globalSettings` VALUES (108,'FOG_MEMORY_LIMIT','Default setting is the memory limit set in php.ini.','128','General Settings');
INSERT INTO `globalSettings` VALUES (109,'FOG_EMAIL_ACTION','Enables email reports of image actions as they\'re completed. Default setting is disabled.','0','FOG Email Settings');
INSERT INTO `globalSettings` VALUES (110,'FOG_EMAIL_ADDRESS','Email address(s) to send the reports to. Separate multiple emails by comma (e.g. user_a@domain.com, user_b@domain2.com). Token ${user-name} is replaced by the task creators username.','','FOG Email Settings');
INSERT INTO `globalSettings` VALUES (111,'FOG_EMAIL_BINARY','Path and arguments to the emailing binary php should use for the mail function. Default is \'/usr/sbin/sendmail -t -f noreply@${server-name}.com -i\'','/usr/sbin/sendmail -t -f noreply@${server-name}.com -i','FOG Email Settings');
INSERT INTO `globalSettings` VALUES (112,'FOG_FROM_EMAIL','Email from address. Default is fogserver. ${server-name} is set to the node name.','noreply@${server-name}.com','FOG Email Settings');
INSERT INTO `globalSettings` VALUES (113,'FOG_PXE_HIDDENMENU_TIMEOUT','This setting defines the default value for the pxe hidden menu timeout.','3','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (114,'FOG_USED_TASKS','This setting defines tasks to consider \'Used\' in the task count. Listing is comma separated, using the ID\'s of the tasks.','1,15,17','General Settings');
INSERT INTO `globalSettings` VALUES (115,'FOG_GRACE_TIMEOUT','This setting defines the grace period for the reboots and shutdowns. The value is specified in seconds.','60','FOG Client');
INSERT INTO `globalSettings` VALUES (116,'FOG_SNAPIN_LIMIT','This setting defines the maximum snapins allowed to be assigned to a host. Value of 0 means unlimited.','0','General Settings');
INSERT INTO `globalSettings` VALUES (117,'FOG_FTP_IMAGE_SIZE','This setting defines the global enabling of image on server size. Checkbox on or off is the enabling element. Default is off.','0','General Settings');
INSERT INTO `globalSettings` VALUES (118,'FOG_MULTICAST_ADDRESS','This setting defines an alternate Multicast Address. Default is 0 which means disabled, value will be ip validated if entered.','0','Multicast Settings');
INSERT INTO `globalSettings` VALUES (119,'FOG_MULTICAST_PORT_OVERRIDE','This setting defines the multicast base ports FOG may use. Enter a comma separated list, for example 63100,63200,63300 -- each port is one multicast session that can run at the same time, and a session takes the port plus the one above it. Ports must be even and between 1024 and 65534; anything else is ignored. Default is 0, which is disabled and lets FOG pick a port per session.','0','Multicast Settings');
INSERT INTO `globalSettings` VALUES (120,'FOG_MULTICAST_DUPLEX','This setting defines the duplex value. Default is FULL_DUPLEX.','--full-duplex','Multicast Settings');
INSERT INTO `globalSettings` VALUES (121,'FOG_REGISTRATION_ENABLED','This setting enables the capabilities to allow registration to occur or not. Default setting is enabled.','1','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (122,'FOG_TZ_INFO','This setting allows the user to set the system timezone. Default is UTC in the db, but will first try the ini set if possible.','UTC','General Settings');
INSERT INTO `globalSettings` VALUES (123,'FOG_KERNEL_DEBUG','This setting allows the user to have the kernel debug flag set. Default is off.','0','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (124,'FOG_KERNEL_LOGLEVEL','This setting allows the user to specify which loglevel the want. Default is 4.','4','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (125,'FOG_FTP_PORT','This setting allows the user to specify the ftp port to be used. Default Value is port 21.','21','General Settings');
INSERT INTO `globalSettings` VALUES (126,'FOG_FTP_TIMEOUT','This setting allows the user to specify the FTP Timeout. This value is entered in seconds. Default is 90.','90','General Settings');
INSERT INTO `globalSettings` VALUES (127,'FOG_AD_DEFAULT_PASSWORD_LEGACY','This setting defines the default value to populate the hosts Active Directory password value but only uses the old FOGCrypt method of encryption. This setting must be encrypted before stored.','','Active Directory Defaults');
INSERT INTO `globalSettings` VALUES (128,'FOG_NONREG_DEVICE','This setting defines a target disk to apply an image to specifically for non-registered hosts. If not set, a disk will be selected by the init.','','Non-Registered Host Image');
INSERT INTO `globalSettings` VALUES (129,'FOG_EFI_BOOT_EXIT_TYPE','The method (U)EFI uses to boot the next boot entry/hard drive. Most will require exit. (Default REFIND)','refind_efi','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (130,'SERVICE_LOG_PATH','The path of which to write logs for the linux side fog services. (Default /opt/fog/log/)','/opt/fog/log','FOG Linux Service Logs');
INSERT INTO `globalSettings` VALUES (131,'SERVICE_LOG_SIZE','The maximum size for logs before starting new in bytes (Default 1000000)','1000000','FOG Linux Service Logs');
INSERT INTO `globalSettings` VALUES (132,'MULTICASTLOGFILENAME','Filename to store the multicast log file to (Default multicast.log)','multicast.log','FOG Linux Service Logs');
INSERT INTO `globalSettings` VALUES (133,'IMAGEREPLICATORLOGFILENAME','Filename to store the image replicator log file to (Default fogreplicator.log)','fogreplicator.log','FOG Linux Service Logs');
INSERT INTO `globalSettings` VALUES (134,'SNAPINREPLICATORLOGFILENAME','Filename to store the snapin replicator log file to (Default fogsnapinrep.log)','fogsnapinrep.log','FOG Linux Service Logs');
INSERT INTO `globalSettings` VALUES (135,'SNAPINHASHLOGFILENAME','Filename to store the snapin hash log file to (Default fogsnapinhash.log)','fogsnapinhash.log','FOG Linux Service Logs');
INSERT INTO `globalSettings` VALUES (136,'SCHEDULERLOGFILENAME','Filename to store the scheduled tasks log file to (Default fogscheduled.log)','fogscheduler.log','FOG Linux Service Logs');
INSERT INTO `globalSettings` VALUES (137,'SERVICEMASTERLOGFILENAME','Filename to store the service master log file to (Default servicemaster.log)','servicemaster.log','FOG Linux Service Logs');
INSERT INTO `globalSettings` VALUES (138,'PINGHOSTLOGFILENAME','Filename to store the ping host log file to (Default pinghost.log)','pinghost.log','FOG Linux Service Logs');
INSERT INTO `globalSettings` VALUES (139,'PINGHOSTSLEEPTIME','The amount of time between ping host service runs. Value is in seconds. (Default 300)','300','FOG Linux Service Sleep Times');
INSERT INTO `globalSettings` VALUES (140,'SERVICESLEEPTIME','The amount of time between service master service runs. Value is in seconds. This is what restarts failed services. (Default 300)','300','FOG Linux Service Sleep Times');
INSERT INTO `globalSettings` VALUES (141,'SNAPINREPSLEEPTIME','The amount of time between snapin replicator service runs. Value is in seconds. (Default 600)','600','FOG Linux Service Sleep Times');
INSERT INTO `globalSettings` VALUES (142,'SNAPINHASHSLEEPTIME','The amount of time between snapin hash service runs. Value is in seconds. (Default 1800)','1800','FOG Linux Service Sleep Times');
INSERT INTO `globalSettings` VALUES (143,'SCHEDULERSLEEPTIME','The amount of time between task scheduler service runs. Value is in seconds. (Default 60)','60','FOG Linux Service Sleep Times');
INSERT INTO `globalSettings` VALUES (144,'IMAGEREPSLEEPTIME','The amount of time between image replicator service runs. Value is in seconds. (Default 600)','600','FOG Linux Service Sleep Times');
INSERT INTO `globalSettings` VALUES (145,'MULTICASTSLEEPTIME','The amount of time between multicast service runs. Value is in seconds. (Default 10)','10','FOG Linux Service Sleep Times');
INSERT INTO `globalSettings` VALUES (146,'MULTICASTDEVICEOUTPUT','The tty to output to for multicast. (Default /dev/tty2)','/dev/tty2','FOG Linux Service TTY Output');
INSERT INTO `globalSettings` VALUES (147,'IMAGEREPLICATORDEVICEOUTPUT','The tty to output to for image replicator. (Default /dev/tty3)','/dev/tty3','FOG Linux Service TTY Output');
INSERT INTO `globalSettings` VALUES (148,'SCHEDULERDEVICEOUTPUT','The tty to output to for task scheduler. (Default /dev/tty4)','/dev/tty4','FOG Linux Service TTY Output');
INSERT INTO `globalSettings` VALUES (149,'SNAPINREPLICATORDEVICEOUTPUT','The tty to output to for snapin replicator. (Default /dev/tty5)','/dev/tty5','FOG Linux Service TTY Output');
INSERT INTO `globalSettings` VALUES (150,'SNAPINHASHDEVICEOUTPUT','The tty to output to for snapin replicator. (Default /dev/tty5)','/dev/tty6','FOG Linux Service TTY Output');
INSERT INTO `globalSettings` VALUES (151,'PINGHOSTDEVICEOUTPUT','The tty to output to for ping hosts. (Default /dev/tty6)','/dev/tty6','FOG Linux Service TTY Output');
INSERT INTO `globalSettings` VALUES (152,'FOG_WIPE_TIMEOUT','This setting defines the number of seconds to wait for wiping disks. (Default 60)','60','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (153,'FOG_BANDWIDTH_TIME','This setting defines how often to refresh the bandwidth chart. Values are in seconds','1','General Settings');
INSERT INTO `globalSettings` VALUES (154,'FOG_ENFORCE_HOST_CHANGES','This setting only operates with the new client. Default value is 1 which allows the new client to enforce name changing on every cycle it checks in, so any change on FOG will take place on the next cycle. If unset (value 0) it will only perform hostname change and/or AD Joining on host restart.','1','Active Directory Defaults');
INSERT INTO `globalSettings` VALUES (155,'FOG_CLIENT_AUTOUPDATE','This setting lets the admin choose whether or not the clients on the hosts will be able to auto update. Default is enabled.','1','FOG Client');
INSERT INTO `globalSettings` VALUES (156,'FOG_CLIENT_POWERMANAGEMENT_ENABLED','This setting defines if the Windows Service module power management should be enabled on client computers. This service allows an on demand shutdown/reboot/wol of hosts. It also operates in a cron style setup to allow many different schedules of shutdowns, restarts, and/or wol. (Valid values: 0 or 1).','1','FOG Client - Power Management');
INSERT INTO `globalSettings` VALUES (157,'FOG_IPXE_MAIN_COLOURS','This setting allows the admin to define their own color (colour) elements for the iPXE Boot Menu. Each element must have a new line as a separator for multiple items.','colour --rgb 0x00567a 1 ||\ncolour --rgb 0x00567a 2 ||\ncolour --rgb 0x00567a 4 ||','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (158,'FOG_IPXE_MAIN_CPAIRS','This setting allows the admin to define their own cpair elements for the iPXE Boot Menu. Each element must have a new line as a separator for multiple items. Fallback will use FOG_IPXE_MAIN_FALLBACK_CPAIRS','cpair --foreground 7 --background 2 2 ||','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (159,'FOG_IPXE_MAIN_FALLBACK_CPAIRS','This setting allows the admin to define their own cpair elements for the iPXE Boot Menu. Each element must have a new line as a separator for multiple items. This is only called in case of failure to load menu with picture.','cpair --background 0 1 ||\ncpair --background 1 2 ||','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (160,'FOG_IPXE_VALID_HOST_COLOURS','This setting allows the admin to define their own color (colour) elements for the iPXE Boot Menu on how the host text will display if the host is registered. Each element must have a new line as a separator for multiple items.','colour --rgb 0x00567a 0 ||','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (161,'FOG_IPXE_INVALID_HOST_COLOURS','This setting allows the admin to define their own color (colour) elements for the iPXE Boot Menu on how the host text will display if the host is not registered. Each element must have a new line as a separator for multiple items.','colour --rgb 0xff0000 0 ||','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (162,'FOG_IPXE_HOST_CPAIRS','This setting allows the admin to define their own cpair elements for the iPXE Boot Menu of the host information. Each element must have a new line as a separator for multiple items.','cpair --foreground 1 1 ||\ncpair --foreground 0 3 ||\ncpair --foreground 4 4 ||','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (163,'FOG_IPXE_BG_FILE','This setting allows the admin to define their own background file. Files will need to be in the fog web root under service/ipxe. Default file is bg.png.','bg.png','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (164,'FOG_URL_AVAILABLE_TIMEOUT','This setting defines the available timeout in thousandths of a second. (Default is 2000 milliseconds)','2000','General Settings');
INSERT INTO `globalSettings` VALUES (165,'FOG_URL_BASE_CONNECT_TIMEOUT','This setting defines the available timeout to connect to a server to perform real actions.  This is set in seconds. (Default is 15 seconds)','15','General Settings');
INSERT INTO `globalSettings` VALUES (166,'FOG_URL_BASE_TIMEOUT','This setting defines the total timeout to perform url based actions, such as download, getting data, etc... This is set in seconds. (Default is 86400 seconds -- 1 day)','86400','General Settings');
INSERT INTO `globalSettings` VALUES (170,'FOG_CLIENT_BANNER_IMAGE','This setting defines an image for the banner on the fog client. The width must be 650 pixels, and the height must be 120 pixels.','','Rebranding');
INSERT INTO `globalSettings` VALUES (171,'FOG_CLIENT_BANNER_SHA','This setting stores the sha value of the banner to be applied.','','Rebranding');
INSERT INTO `globalSettings` VALUES (172,'FOG_COMPANY_NAME','This setting defines the name you would like presented on the client.','','Rebranding');
INSERT INTO `globalSettings` VALUES (173,'FOG_COMPANY_COLOR','This setting is the hex color code you want progress bar colors to display as.','','Rebranding');
INSERT INTO `globalSettings` VALUES (174,'FOG_COMPANY_TOS','This allows setting the company terms of service.','','Rebranding');
INSERT INTO `globalSettings` VALUES (175,'FOG_COMPANY_SUBNAME','This allows setting the sub unit, and is only used  on the Equipment loan report for tracking.','','Rebranding');
INSERT INTO `globalSettings` VALUES (176,'FOG_LOGIN_INFO_DISPLAY','This setting defines if the login page should or should not display fog version information. (Default is on)','1','General Settings');
INSERT INTO `globalSettings` VALUES (177,'IMAGEREPLICATORGLOBALENABLED','This setting defines if replication of images should occur (Default is enabled)','1','FOG Linux Service Enabled');
INSERT INTO `globalSettings` VALUES (178,'SNAPINREPLICATORGLOBALENABLED','This setting defines if replication of snapins should occur (Default is enabled)','1','FOG Linux Service Enabled');
INSERT INTO `globalSettings` VALUES (179,'SNAPINHASHGLOBALENABLED','This setting defines if hashing of snapins should occur (Default is enabled)','1','FOG Linux Service Enabled');
INSERT INTO `globalSettings` VALUES (180,'PINGHOSTGLOBALENABLED','This setting defines if ping hosts should occur (Default is enabled)','1','FOG Linux Service Enabled');
INSERT INTO `globalSettings` VALUES (181,'SCHEDULERGLOBALENABLED','This setting defines if scheduler service should occur (Default is enabled)','1','FOG Linux Service Enabled');
INSERT INTO `globalSettings` VALUES (182,'MULTICASTGLOBALENABLED','This setting defines if multicast service should occur (Default is enabled)','1','FOG Linux Service Enabled');
INSERT INTO `globalSettings` VALUES (183,'FOG_MULTICAST_RENDEZVOUS','This setting defines a rendez-vous for multicast tasks. (Default is empty)','','Multicast Settings');
INSERT INTO `globalSettings` VALUES (184,'FOG_QUICKREG_IMG_WHEN_REG','Image upon completion of registration. Values are 0 or 1, default is 1. This will only image clients if the image value is defined as well.','0','FOG Quick Registration');
INSERT INTO `globalSettings` VALUES (185,'IMAGESIZEGLOBALENABLED','This setting defines if image size should be enabled or not. (Default is enabled)','1','FOG Linux Service Enabled');
INSERT INTO `globalSettings` VALUES (186,'IMAGESIZESLEEPTIME','The amount of time between image size service runs. Value is in seconds. (Default 3600)','3600','FOG Linux Service Sleep Times');
INSERT INTO `globalSettings` VALUES (187,'IMAGESIZELOGFILENAME','Filename to store the image size log file to (Default fogimagesize.log)','fogimagesize.log','FOG Linux Service Logs');
INSERT INTO `globalSettings` VALUES (188,'IMAGESIZEDEVICEOUTPUT','The tty to output to for image size service. (Default /dev/tty3)','/dev/tty3','FOG Linux Service TTY Output');
INSERT INTO `globalSettings` VALUES (189,'FOG_IMAGE_COMPRESSION_FORMAT_DEFAULT','Compression Format Setting (Default to Partclone Zstd)','5','General Settings');
INSERT INTO `globalSettings` VALUES (190,'FOG_TASKING_ADV_SHUTDOWN_ENABLED','Tasking shutdown element checked (Default is off)','0','General Settings');
INSERT INTO `globalSettings` VALUES (191,'FOG_TASKING_ADV_WOL_ENABLED','Tasking wake on lan element checked (Default is on)','1','General Settings');
INSERT INTO `globalSettings` VALUES (192,'FOG_TASKING_ADV_DEBUG_ENABLED','Tasking debug element checked (Default is off)','0','General Settings');
INSERT INTO `globalSettings` VALUES (193,'FOG_API_ENABLED','Enables API Access (Defaults to off)','0','API System');
INSERT INTO `globalSettings` VALUES (194,'FOG_API_TOKEN','The API Token to use (Randomly generated at install)','86c6ec02ac70d573471470426c68b6ef035ee1eef0cd2a2db97648c638fb5ac2','API System');
INSERT INTO `globalSettings` VALUES (195,'FOG_IMAGE_LIST_MENU','Enables Image list on boot menu deploy image (Defaults to on)','1','FOG Boot Settings');
INSERT INTO `globalSettings` VALUES (196,'FOG_REAUTH_ON_DELETE','If deleting an item, require authentication or not. (Defaults to on)','1','General Settings');
INSERT INTO `globalSettings` VALUES (197,'FOG_REAUTH_ON_EXPORT','If exporting, require authentication or not. (Defaults to on)','1','General Settings');
INSERT INTO `globalSettings` VALUES (198,'FOG_QUICKREG_PROD_KEY_BIOS','Try pulling systems SLIC product key. Values are 0 or 1, default is 0.','0','FOG Quick Registration');
INSERT INTO `globalSettings` VALUES (199,'FOG_TFTP_PXE_KERNEL_ARM','Location of the ARM kernel file on the PXE server, this should point to the kernel itself.','arm_Image','TFTP Server');
INSERT INTO `globalSettings` VALUES (200,'FOG_PXE_BOOT_IMAGE_ARM','The settings defines where the ARM fog boot file system image is located.','arm_init.cpio.gz','TFTP Server');
INSERT INTO `globalSettings` VALUES (201,'FOG_HOSTKEY_ALLOWED_SOURCES','This setting restricts which source addresses may obtain a host token from status/hostgetkey.php, which is what unlocks the host information service (including Active Directory join credentials and the product key). Enter a comma separated list of imaging networks in CIDR form and/or individual addresses, for example 10.0.0.0/8,192.168.5.20. Leave empty to allow any source, which is the default and matches the behaviour of earlier versions.','','Security');
INSERT INTO `taskStates` VALUES (1,'Queued','Task has been created and FOG is waiting for the Host to check-in.',1,'bookmark-o');
INSERT INTO `taskStates` VALUES (2,'Checked In','PC has checked in and is in queue for imaging',2,'pause');
INSERT INTO `taskStates` VALUES (3,'In-Progress','Host is currently Imaging.',3,'spinner fa-pulse fa-fw');
INSERT INTO `taskStates` VALUES (4,'Complete','Imaging has been completed.',4,'check-circle');
INSERT INTO `taskStates` VALUES (5,'Cancelled','Task was aborted by user',5,'ban');
INSERT INTO `taskTypes` VALUES (1,'Deploy','Deploy action will send an image saved on the FOG server to the client computer with all included snapins.','download','','type=down','fog','0','both','');
INSERT INTO `taskTypes` VALUES (2,'Capture','Capture will pull an image from a client computer that will be saved on the server.','upload','','type=up','fog','0','host','');
INSERT INTO `taskTypes` VALUES (3,'Debug','Debug mode will load the boot image and load a prompt so you can run any commands you wish. When you are done, you must remember to remove the PXE file, by clicking on \"Active Tasks\" and clicking on the \"Kill Task\" button.','bug','','mode=onlydebug','fog','1','host','');
INSERT INTO `taskTypes` VALUES (4,'Memtest86+','Memtest86+ loads Memtest86+ on the client computer and will have it continue to run until stopped. When you are done, you must remember to remove the PXE file, by clicking on \"Active Tasks\" and clicking on the \"Kill Task\" button.','plus-square-o','fog/memtest/memtest','','fog','1','both','');
INSERT INTO `taskTypes` VALUES (5,'Test Disk','Test Disk loads the testdisk utility that can be used to check a hard disk and recover lost partitions.','hdd-o','','mode=checkdisk','fog','1','both','');
INSERT INTO `taskTypes` VALUES (6,'Disk Surface Test','Disk Surface Test checks the hard drive\'s surface sector by sector for any errors and reports back if errors are present.','user-md','','mode=badblocks','fog','1','both','');
INSERT INTO `taskTypes` VALUES (7,'Recover','Recover loads the photorec utility that can be used to recover lost files from a hard disk. When recovering files, make sure you save them to your NFS volume (ie: /images).','ambulance','','mode=photorec','fog','1','both','');
INSERT INTO `taskTypes` VALUES (8,'Multi-Cast','Deploy action will send an image saved on the FOG server to the client computer with all included snapins.','share-alt','','type=down mc=yes','fog','0','group','');
INSERT INTO `taskTypes` VALUES (10,'Hardware Inventory','The hardware inventory task will boot the client computer and pull basic hardware information from it and report it back to the FOG server.','list-alt','','mode=inventory deployed=1','fog','1','both','');
INSERT INTO `taskTypes` VALUES (11,'Password Reset','Password reset will blank out a Windows user password that may have been lost or forgotten.','key','','mode=winpassreset','fog','1','both','');
INSERT INTO `taskTypes` VALUES (12,'All Snapins','This option allows you to send all the snapins to host without imaging the computer. (Requires FOG Client to be installed on client)','cubes','','','fog','1','both','');
INSERT INTO `taskTypes` VALUES (13,'Single Snapin','This option allows you to send a single snapin to a host. (Requires FOG Client to be installed on client)','cube','','','fog','1','both','');
INSERT INTO `taskTypes` VALUES (14,'Wake-Up','Wake Up will attempt to send the Wake-On-LAN packet to the computer to turn the computer on. In switched environments, you typically need to configure your hardware to allow for this (iphelper).','plug','','','fog','1','both','');
INSERT INTO `taskTypes` VALUES (15,'Deploy - Debug','Deploy - Debug mode allows FOG to setup the environment to allow you send a specific image to a computer, but instead of sending the image, FOG will leave you at a prompt right before sending. If you actually wish to send the image all you need to do is type \"fog\" and hit enter.','arrow-circle-o-down','','type=down mode=debug','fog','1','host','');
INSERT INTO `taskTypes` VALUES (16,'Capture - Debug','Capture - Debug mode allows FOG to setup the environment to allow you capture a specific image from a computer, but instead of capturing the image, FOG will leave you at a prompt right before restoring. If you actually wish to capture the image all you need to do is type \"fog\" and hit enter.','arrow-circle-o-up','','type=up mode=debug','fog','1','host','');
INSERT INTO `taskTypes` VALUES (17,'Deploy - No Snapins','Deploy without snapins allows FOG to image the workstation, but after the task is complete any snapins linked to the host or group will NOT be sent.','chevron-circle-down','','type=down','fog','1','both','');
INSERT INTO `taskTypes` VALUES (18,'Fast Wipe','Fast wipe will boot the client computer and wipe the first few sectors of data on the hard disk. Data will not be overwritten but the boot up of the disk and partition layout will no longer exist.','hourglass-o','','mode=wipe wipemode=fast','fog','1','both','');
INSERT INTO `taskTypes` VALUES (19,'Normal Wipe','Normal wipe will boot the client computer and perform a full disk wipe. This method writes ONE pass of random data to the hard disk.','hourglass-2','','mode=wipe wipemode=normal','fog','1','both','');
INSERT INTO `taskTypes` VALUES (20,'Full Wipe','Full Wipe will boot the client computer and perform a full disk wipe. This method writes a few passes of random data to the hard disk.','hourglass','','mode=wipe wipemode=full','fog','1','both','');
INSERT INTO `taskTypes` VALUES (21,'Virus Scan','Anti-Virus loads Clam AV on the client boot image, updates the scanner and then scans the Windows partition.','exclamation-triangle','','mode=clamav avmode=s','fog','1','both','');
INSERT INTO `taskTypes` VALUES (22,'Virus Scan - Quarantine','Anti-Virus loads Clam AV on the client boot image, updates the scanner and then scans the Windows partition.','flag-o','','mode=clamav avmode=q','fog','1','both','');
INSERT INTO `os` VALUES (1,'Windows 2000/XP','');
INSERT INTO `os` VALUES (2,'Windows Vista','');
INSERT INTO `os` VALUES (3,'Windows 98','');
INSERT INTO `os` VALUES (4,'Windows Other','');
INSERT INTO `os` VALUES (5,'Windows 7','');
INSERT INTO `os` VALUES (6,'Windows 8','');
INSERT INTO `os` VALUES (7,'Windows 8.1','');
INSERT INTO `os` VALUES (8,'Apple Mac OS','');
INSERT INTO `os` VALUES (9,'Windows 10','');
INSERT INTO `os` VALUES (50,'Linux','');
INSERT INTO `os` VALUES (51,'Chromium OS','Chromium OS');
INSERT INTO `os` VALUES (99,'Other','');
INSERT INTO `imageTypes` VALUES (1,'Single Disk - Resizable','n');
INSERT INTO `imageTypes` VALUES (2,'Multiple Partition Image - Single Disk (Not Resizable)','mps');
INSERT INTO `imageTypes` VALUES (3,'Multiple Partition Image - All Disks  (Not Resizable)','mpa');
INSERT INTO `imageTypes` VALUES (4,'Raw Image (Sector By Sector, DD, Slow)','dd');
INSERT INTO `imagePartitionTypes` VALUES (1,'Everything','all');
INSERT INTO `imagePartitionTypes` VALUES (2,'Partition Table and MBR only','mbr');
INSERT INTO `imagePartitionTypes` VALUES (3,'Partition 1 only','1');
INSERT INTO `imagePartitionTypes` VALUES (4,'Partition 2 only','2');
INSERT INTO `imagePartitionTypes` VALUES (5,'Partition 3 only','3');
INSERT INTO `imagePartitionTypes` VALUES (6,'Partition 4 only','4');
INSERT INTO `imagePartitionTypes` VALUES (7,'Partition 5 only','5');
INSERT INTO `imagePartitionTypes` VALUES (8,'Partition 6 only','6');
INSERT INTO `imagePartitionTypes` VALUES (9,'Partition 7 only','7');
INSERT INTO `imagePartitionTypes` VALUES (10,'Partition 8 only','8');
INSERT INTO `imagePartitionTypes` VALUES (11,'Partition 9 only','9');
INSERT INTO `imagePartitionTypes` VALUES (12,'Partition 10 only','10');
INSERT INTO `supportedOS` VALUES (1,'Windows 2000/XP',1);
INSERT INTO `supportedOS` VALUES (2,'Windows Vista',2);
INSERT INTO `supportedOS` VALUES (3,'Other',99);
INSERT INTO `supportedOS` VALUES (4,'Windows 98',3);
INSERT INTO `supportedOS` VALUES (5,'Windows (other)',4);
INSERT INTO `supportedOS` VALUES (6,'Linux',50);
INSERT INTO `supportedOS` VALUES (7,'Windows 7',5);
INSERT INTO `supportedOS` VALUES (8,'Windows 8',6);
INSERT INTO `modules` VALUES (1,'Directory Cleaner','dircleanup','This setting will enable or disable the directory cleaner service module on this specific host. If the module is globally disabled, this setting is ignored.',1);
INSERT INTO `modules` VALUES (2,'User Cleanup','usercleanup','This setting will enable or disable the user cleaner service module on this specific host. If the module is globally disabled, this setting is ignored. The user clean up service will remove all stale users on the local machine, accept for user accounts that are whitelisted. This is typically used when dynamic local users is implemented on the workstation.',1);
INSERT INTO `modules` VALUES (3,'Display Manager','displaymanager','This setting will enable or disable the display manager service module on this specific host. If the module is globally disabled, this setting is ignored.',1);
INSERT INTO `modules` VALUES (4,'Auto Log Out','autologout','This setting will enable or disable the auto log out service module on this specific host. If the module is globally disabled, this setting is ignored.',1);
INSERT INTO `modules` VALUES (5,'Green FOG','greenfog','This setting will enable or disable the green fog service module on this specific host. If the module is globally disabled, this setting is ignored.',1);
INSERT INTO `modules` VALUES (6,'Snapins','snapinclient','This setting will enable or disable the snapin service module on this specific host. If the module is globally disabled, this setting is ignored.',1);
INSERT INTO `modules` VALUES (7,'Client Updater','clientupdater','This setting will enable or disable the client updater service module on this specific host. If the module is globally disabled, this setting is ignored.',1);
INSERT INTO `modules` VALUES (8,'Host Registration','hostregister','This setting will enable or disable the host register service module on this specific host. If the module is globally disabled, this setting is ignored.',1);
INSERT INTO `modules` VALUES (9,'Hostname Changer','hostnamechanger','This setting will enable or disable the hostname changer module on this specific host. If the module is globally disabled, this setting is ignored.',1);
INSERT INTO `modules` VALUES (10,'Printer Manager','printermanager','This setting will enable or disable the printer manager service module on this specific host. If the module is globally disabled, this setting is ignored.',1);
INSERT INTO `modules` VALUES (11,'Task Reboot','taskreboot','This setting will enable or disable the task reboot service module on this specific host. If the module is globally disabled, this setting is ignored.',1);
INSERT INTO `modules` VALUES (12,'User Tracker','usertracker','This setting will enable or disable the user tracker service module on this specific host. If the module is globally disabled, this setting is ignored.',1);
INSERT INTO `modules` VALUES (13,'Power Management','powermanagement','This setting will enable or disable the power management service module on this specific host. If the module is globally disabled, this setting is ignored.',1);
