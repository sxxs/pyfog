-- Test data for pyfog: six hosts, two images, two groups, tasks in every
-- state, one multicast session, imaging and snapin logs. Load after
-- fog-schema.sql. Timestamps are relative to NOW() so ages look plausible.
SET SESSION sql_mode = '';
DELETE FROM images; DELETE FROM nfsGroups; DELETE FROM nfsGroupMembers; DELETE FROM imageGroupAssoc;
DELETE FROM hosts; DELETE FROM hostMAC; DELETE FROM groups; DELETE FROM groupMembers; DELETE FROM tasks;
DELETE FROM multicastSessions; DELETE FROM multicastSessionsAssoc; DELETE FROM imagingLog; DELETE FROM taskLog;
DELETE FROM snapins; DELETE FROM snapinJobs; DELETE FROM snapinTasks; DELETE FROM scheduledTasks;

INSERT INTO images (imageID,imageName,imageDesc,imagePath,imageTypeID,imagePartitionTypeID,imageOSID,imageFormat,imageEnabled,imageProtect,imageServerSize,imageSize,imageLastDeploy,imageDateTime,imageCreateBy) VALUES
 (1,'Win11-Lab','Windows 11 lab image','win11lab',1,1,9,'5','1',0,12345678901,'500107862016:',NOW()-INTERVAL 1 DAY,NOW()-INTERVAL 30 DAY,'admin'),
 (2,'Ubuntu-Lab','','ubuntulab',1,1,50,'0','0',1,2345678901,'',0,NOW()-INTERVAL 60 DAY,'admin');
INSERT INTO nfsGroups (ngID,ngName,ngDesc) VALUES (1,'default','');
INSERT INTO nfsGroupMembers (ngmID,ngmMemberName,ngmIsMasterNode,ngmGroupID,ngmRootPath,ngmIsEnabled,ngmHostname,ngmMaxClients,ngmInterface) VALUES
 (1,'DefaultMember','1',1,'/images','1','127.0.0.1',10,'eth0');
INSERT INTO imageGroupAssoc (igaImageID,igaStorageGroupID,igaPrimary) VALUES (1,1,'1'),(2,1,'1');

INSERT INTO hosts (hostID,hostName,hostDesc,hostIP,hostImage,hostSecTime,hostPending,hostLastDeploy,hostCreateDate) VALUES
 (1,'pc01','Lab A seat 1','10.0.0.11',1,NOW()+INTERVAL 25 MINUTE,'0',NOW()-INTERVAL 1 DAY,NOW()-INTERVAL 100 DAY),
 (2,'pc02','','10.0.0.12',1,NOW()-INTERVAL 2 DAY,'0','0000-00-00 00:00:00',NOW()-INTERVAL 100 DAY),
 (3,'pc03','','10.0.0.13',1,'0000-00-00 00:00:00','0','0000-00-00 00:00:00',NOW()-INTERVAL 100 DAY),
 (4,'pc04','','10.0.0.14',1,NOW()+INTERVAL 10 MINUTE,'0','0000-00-00 00:00:00',NOW()-INTERVAL 100 DAY),
 (5,'pc05','','10.0.0.15',1,NOW()-INTERVAL 5 HOUR,'0',NOW()-INTERVAL 1 DAY,NOW()-INTERVAL 100 DAY),
 (6,'pc06','Ubuntu box','10.0.0.16',2,NOW()+INTERVAL 29 MINUTE,'1','0000-00-00 00:00:00',NOW()-INTERVAL 1 DAY);
INSERT INTO hostMAC (hmHostID,hmMAC,hmPrimary,hmPending) VALUES
 (1,'00:11:22:33:44:01','1','0'),(1,'aa:bb:cc:dd:ee:ff','0','0'),(2,'00:11:22:33:44:02','1','0'),
 (3,'00:11:22:33:44:03','1','0'),(4,'00:11:22:33:44:04','1','0'),(5,'00:11:22:33:44:05','1','0'),(6,'00:11:22:33:44:06','1','0');
INSERT INTO groups (groupID,groupName,groupDesc,groupCreateBy) VALUES (1,'Lab-A','Pool A','admin'),(2,'Lab-B','','admin');
INSERT INTO groupMembers (gmHostID,gmGroupID) VALUES (1,1),(2,1),(3,1),(4,2),(5,2),(6,2);

-- 1 deploy running, 2 checked in but silent (stale), 3 queued capture,
-- 4-6 one multicast session, 7 completed yesterday, 8 cancelled
INSERT INTO tasks (taskID,taskName,taskCreateTime,taskCheckIn,taskHostID,taskImageID,taskStateID,taskCreateBy,taskForce,taskScheduledStartTime,taskTypeID,taskPCT,taskBPM,taskTimeElapsed,taskTimeRemaining,taskDataCopied,taskDataTotal,taskNFSGroupID,taskNFSMemberID,taskWOL) VALUES
 (1,'Deploy - pc01',NOW()-INTERVAL 10 MINUTE,NOW()-INTERVAL 30 SECOND,1,1,3,'admin','0','0000-00-00 00:00:00',1,45,'1.20','00:05:12','00:06:00','10.2GB','22.5GB',1,1,'1'),
 (2,'Deploy - pc02',NOW()-INTERVAL 40 MINUTE,NOW()-INTERVAL 20 MINUTE,2,1,2,'admin','0','0000-00-00 00:00:00',1,0,'','','','','',1,1,'0'),
 (3,'Capture - pc03',NOW()-INTERVAL 2 MINUTE,'0000-00-00 00:00:00',3,1,1,'dominik','1',NOW()+INTERVAL 1 HOUR,2,0,'','','','','',1,1,'0'),
 (4,'Multi-Cast - Lab-A',NOW()-INTERVAL 8 MINUTE,NOW()-INTERVAL 15 SECOND,1,1,3,'admin','0','0000-00-00 00:00:00',8,30,'0.9','00:03:00','00:07:00','6.0GB','22.5GB',1,1,'0'),
 (5,'Multi-Cast - Lab-A',NOW()-INTERVAL 8 MINUTE,NOW()-INTERVAL 10 SECOND,2,1,3,'admin','0','0000-00-00 00:00:00',8,31,'0.9','00:03:00','00:07:00','6.1GB','22.5GB',1,1,'0'),
 (6,'Multi-Cast - Lab-A',NOW()-INTERVAL 8 MINUTE,'0000-00-00 00:00:00',3,1,1,'admin','0','0000-00-00 00:00:00',8,0,'','','','','',1,1,'0'),
 (7,'Deploy - pc05',NOW()-INTERVAL 1 DAY-INTERVAL 30 MINUTE,NOW()-INTERVAL 1 DAY,5,1,4,'admin','0','0000-00-00 00:00:00',1,100,'','00:20:00','00:00:00','','',1,1,'0'),
 (8,'Capture - pc06',NOW()-INTERVAL 3 DAY,NOW()-INTERVAL 3 DAY,6,2,5,'admin','0','0000-00-00 00:00:00',2,0,'','','','','',1,1,'0'),
 -- pc04: the multicast manager completed the task when udp-sender exited; the host
 -- never got to report, so imagingLog stays open and taskLog has no Complete row.
 (9,'Multi-Cast - Lab-A',NOW()-INTERVAL 45 MINUTE,NOW()-INTERVAL 35 MINUTE,4,1,4,'admin','0','0000-00-00 00:00:00',8,97,'0.9','00:05:00','00:00:10','21.8GB','22.5GB',1,1,'0'),
 -- pc06: someone cancelled the session while this host was already writing
 -- the image. A cancelled host never reports a finish, so its imagingLog
 -- row stays open although nothing is running any more.
 (10,'Multi-Cast - Lab-B',NOW()-INTERVAL 25 MINUTE,NOW()-INTERVAL 21 MINUTE,6,1,5,'admin','0','0000-00-00 00:00:00',8,12,'0.9','00:01:30','00:08:00','2.7GB','22.5GB',1,1,'0');
-- msSenderPID 0: no sender process to look for. Set it to the pid of a
-- running /bin/sh with udp-sender children to exercise the process check.
-- msClients is a marker, not a count: 0 for the ordinary group deploy of
-- registered hosts, -2 while a named session takes unregistered clients,
-- 0 again once one is finished. The number of hosts is the assoc rows
-- below; msSessClients only sizes a named session.
INSERT INTO multicastSessions (msID,msName,msBasePort,msLogPath,msImage,msClients,msSessClients,msInterface,msStartDateTime,msPercent,msState,msCompleteDateTime,msNFSGroupID,msSenderPID,msSenderNode,msSenderStart) VALUES
 (1,'Multi-Cast - Lab-A',63100,'/images/win11lab','1',0,0,'eth0',NOW()-INTERVAL 8 MINUTE,30,3,'0000-00-00 00:00:00',1,0,1,NOW()-INTERVAL 8 MINUTE),
 (2,'Multi-Cast - old',63102,'/images/win11lab','1',0,0,'eth0',NOW()-INTERVAL 5 DAY,100,4,NOW()-INTERVAL 5 DAY+INTERVAL 20 MINUTE,1,0,0,NOW()-INTERVAL 5 DAY);
INSERT INTO multicastSessionsAssoc (msID,tID) VALUES (1,4),(1,5),(1,6);

-- pc05 finished yesterday; pc01 imaging with a task; pc04 imaging without one
INSERT INTO imagingLog (ilHostID,ilStartTime,ilFinishTime,ilImageName,ilType,ilCreatedBy) VALUES
 (5,NOW()-INTERVAL 1 DAY-INTERVAL 20 MINUTE,NOW()-INTERVAL 1 DAY,'Win11-Lab','down','admin'),
 (1,NOW()-INTERVAL 5 MINUTE,'0000-00-00 00:00:00','Win11-Lab','down','admin'),
 (4,NOW()-INTERVAL 40 MINUTE,'0000-00-00 00:00:00','Win11-Lab','down','admin'),
 (6,NOW()-INTERVAL 20 MINUTE,'0000-00-00 00:00:00','Win11-Lab','down','admin'),
 (6,NOW()-INTERVAL 3 DAY,NOW()-INTERVAL 3 DAY+INTERVAL 15 MINUTE,'Ubuntu-Lab','up','admin');
INSERT INTO taskLog (taskID,taskStateID,ip,createTime,createdBy) VALUES
 ('7',3,'10.0.0.15',NOW()-INTERVAL 1 DAY-INTERVAL 20 MINUTE,'admin'),('7',4,'10.0.0.15',NOW()-INTERVAL 1 DAY,'admin'),
 ('9',3,'10.0.0.14',NOW()-INTERVAL 40 MINUTE,'admin'),
 ('10',3,'10.0.0.16',NOW()-INTERVAL 21 MINUTE,'admin'),('10',5,'10.0.0.16',NOW()-INTERVAL 19 MINUTE,'admin');

INSERT INTO snapins (sID,sName,sDesc,sFilePath,sCreator) VALUES
 (1,'Office','','/opt/fog/snapins/office.exe','admin'),(2,'Chrome','','/opt/fog/snapins/chrome.msi','admin');
INSERT INTO snapinJobs (sjID,sjHostID,sjStateID,sjCreateTime) VALUES (1,1,4,NOW()-INTERVAL 2 HOUR),(2,2,1,NOW()-INTERVAL 5 MINUTE);
INSERT INTO snapinTasks (stJobID,stState,stCheckinDate,stCompleteDate,stSnapinID,stReturnCode,stReturnDetails) VALUES
 (1,4,NOW()-INTERVAL 2 HOUR,NOW()-INTERVAL 110 MINUTE,1,0,''),
 (1,4,NOW()-INTERVAL 110 MINUTE,NOW()-INTERVAL 100 MINUTE,2,1603,'Fatal error during installation'),
 (2,1,NOW()-INTERVAL 5 MINUTE,'0000-00-00 00:00:00',1,0,'');
INSERT INTO scheduledTasks (stID,stName,stType,stTaskTypeID,stMinute,stHour,stDOM,stMonth,stDOW,stIsGroup,stGroupHostID,stImageID,stActive,stDateTime) VALUES
 (1,'Nightly deploy','C',1,'0','3','*','*','1-5','1',1,1,'1',0),
 (2,'Deploy pc02 later','S',1,'','','','','','0',2,1,'1',UNIX_TIMESTAMP(NOW()+INTERVAL 2 HOUR));
