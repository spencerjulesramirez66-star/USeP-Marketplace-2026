-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: usep_marketplace
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `accounts_campus`
--

DROP TABLE IF EXISTS `accounts_campus`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_campus` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `campus_code` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `campus_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `campus_code` (`campus_code`),
  UNIQUE KEY `campus_name` (`campus_name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_campus`
--

LOCK TABLES `accounts_campus` WRITE;
/*!40000 ALTER TABLE `accounts_campus` DISABLE KEYS */;
INSERT INTO `accounts_campus` VALUES (1,'TA','Tagum Campus'),(2,'MA','Mabini Campus'),(3,'OB','Obrero Campus'),(4,'MI','Mintal Campus');
/*!40000 ALTER TABLE `accounts_campus` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_college`
--

DROP TABLE IF EXISTS `accounts_college`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_college` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `college_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `college_name` (`college_name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_college`
--

LOCK TABLES `accounts_college` WRITE;
/*!40000 ALTER TABLE `accounts_college` DISABLE KEYS */;
INSERT INTO `accounts_college` VALUES (1,'College of Engineering'),(2,'College of Teacher Education and Technology'),(4,'USeP Academic Programs');
/*!40000 ALTER TABLE `accounts_college` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_emailotp`
--

DROP TABLE IF EXISTS `accounts_emailotp`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_emailotp` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `otp_hash` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `expires_at` datetime(6) NOT NULL,
  `attempts` int unsigned NOT NULL,
  `is_used` tinyint(1) NOT NULL,
  `user_id` bigint NOT NULL,
  `purpose` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `accounts_emailotp_user_id_137ae83b_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `accounts_emailotp_user_id_137ae83b_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `accounts_emailotp_chk_1` CHECK ((`attempts` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_emailotp`
--

LOCK TABLES `accounts_emailotp` WRITE;
/*!40000 ALTER TABLE `accounts_emailotp` DISABLE KEYS */;
INSERT INTO `accounts_emailotp` VALUES (1,'pbkdf2_sha256$1200000$2f5N9sdXHc7Qg8VPfiFhSH$0oWcu12fB6RfTlGC0iuWZmzw7+cHEvNtwdXph/8VuZs=','2026-09-05 13:41:50.854424','2026-09-05 13:51:50.854002',0,0,1,'EMAIL_VERIFICATION');
/*!40000 ALTER TABLE `accounts_emailotp` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_major`
--

DROP TABLE IF EXISTS `accounts_major`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_major` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `major_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `program_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_major_per_program` (`program_id`,`major_name`),
  CONSTRAINT `accounts_major_program_id_adb3b662_fk_accounts_program_id` FOREIGN KEY (`program_id`) REFERENCES `accounts_program` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_major`
--

LOCK TABLES `accounts_major` WRITE;
/*!40000 ALTER TABLE `accounts_major` DISABLE KEYS */;
INSERT INTO `accounts_major` VALUES (2,'Machinery and Power Engineering',1),(1,'Major in Land and Water Resources Engineering',1),(3,'Process Engineering',1),(4,'Structures and Environment Engineering',1),(7,'Major in English',4),(6,'Major in Mathematics',4),(16,'Major in Agricultural Crops Technology',6),(5,'Major in Animal Production',6),(8,'Information Security',7),(13,'Major in English',9),(14,'Major in Filipino',9),(15,'Major in Mathematics',9);
/*!40000 ALTER TABLE `accounts_major` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_program`
--

DROP TABLE IF EXISTS `accounts_program`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_program` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `program_name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `college_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_program_per_college` (`college_id`,`program_name`),
  CONSTRAINT `accounts_program_college_id_3d44903e_fk_accounts_college_id` FOREIGN KEY (`college_id`) REFERENCES `accounts_college` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_program`
--

LOCK TABLES `accounts_program` WRITE;
/*!40000 ALTER TABLE `accounts_program` DISABLE KEYS */;
INSERT INTO `accounts_program` VALUES (1,'Bachelor of Science in Agricultural and Biosystems Engineering',1),(2,'Bachelor of Early Childhood Education (BECEd)',2),(3,'Bachelor of Elementary Education (BEEd)',2),(7,'Bachelor of Science in Information Technology (BSIT)',2),(4,'Bachelor of Science in Secondary Education',2),(5,'Bachelor of Special Needs Education (BSNEd)',2),(6,'Bachelor of Technical-Vocational Teacher Education (BTVTEd)',2),(9,'Bachelor of Secondary Education (BSEd)',4);
/*!40000 ALTER TABLE `accounts_program` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_sellerprofile`
--

DROP TABLE IF EXISTS `accounts_sellerprofile`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_sellerprofile` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `is_verified` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `accounts_sellerprofile_user_id_8976d036_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_sellerprofile`
--

LOCK TABLES `accounts_sellerprofile` WRITE;
/*!40000 ALTER TABLE `accounts_sellerprofile` DISABLE KEYS */;
/*!40000 ALTER TABLE `accounts_sellerprofile` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_staffprofile`
--

DROP TABLE IF EXISTS `accounts_staffprofile`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_staffprofile` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `staff_id` varchar(7) COLLATE utf8mb4_unicode_ci NOT NULL,
  `staff_type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `campus_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `staff_id` (`staff_id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `accounts_staffprofile_campus_id_9e96af70_fk_accounts_campus_id` (`campus_id`),
  CONSTRAINT `accounts_staffprofile_campus_id_9e96af70_fk_accounts_campus_id` FOREIGN KEY (`campus_id`) REFERENCES `accounts_campus` (`id`),
  CONSTRAINT `accounts_staffprofile_user_id_1ed1af60_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_staffprofile`
--

LOCK TABLES `accounts_staffprofile` WRITE;
/*!40000 ALTER TABLE `accounts_staffprofile` DISABLE KEYS */;
INSERT INTO `accounts_staffprofile` VALUES (1,'TEST001','TEACHING',1,2);
/*!40000 ALTER TABLE `accounts_staffprofile` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_studentprofile`
--

DROP TABLE IF EXISTS `accounts_studentprofile`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_studentprofile` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `student_id` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `year_level` varchar(1) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `major_id` bigint DEFAULT NULL,
  `user_id` bigint NOT NULL,
  `program_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `student_id` (`student_id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `accounts_studentprofile_major_id_8cd3c448_fk_accounts_major_id` (`major_id`),
  KEY `accounts_studentprof_program_id_b6284558_fk_accounts_` (`program_id`),
  CONSTRAINT `accounts_studentprof_program_id_b6284558_fk_accounts_` FOREIGN KEY (`program_id`) REFERENCES `accounts_program` (`id`),
  CONSTRAINT `accounts_studentprofile_major_id_8cd3c448_fk_accounts_major_id` FOREIGN KEY (`major_id`) REFERENCES `accounts_major` (`id`),
  CONSTRAINT `accounts_studentprofile_user_id_04a48d2e_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_studentprofile`
--

LOCK TABLES `accounts_studentprofile` WRITE;
/*!40000 ALTER TABLE `accounts_studentprofile` DISABLE KEYS */;
INSERT INTO `accounts_studentprofile` VALUES (1,'TEST000001','3',NULL,1,7),(2,'B00000003',NULL,NULL,3,7),(3,'B00000004',NULL,NULL,4,7),(4,'B00000005',NULL,NULL,5,7),(5,'B00000006',NULL,NULL,6,7),(6,'B00000007',NULL,NULL,7,7),(7,'B00000008',NULL,NULL,8,7);
/*!40000 ALTER TABLE `accounts_studentprofile` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_user`
--

DROP TABLE IF EXISTS `accounts_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email_verified` tinyint(1) NOT NULL,
  `is_first_login` tinyint(1) NOT NULL,
  `first_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `middle_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_num` varchar(11) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `profile_picture` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `date_joined` datetime(6) NOT NULL,
  `is_seller` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `contact_num` (`contact_num`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_user`
--

LOCK TABLES `accounts_user` WRITE;
/*!40000 ALTER TABLE `accounts_user` DISABLE KEYS */;
INSERT INTO `accounts_user` VALUES (1,'pbkdf2_sha256$1200000$CfHjB1LfcmgDmLrKf8sdgf$BU20zaIQ/GGUjJ4+A9nedULLRHgrNvAOoi974u7cL/s=',NULL,0,'spejdjdjjd@gmail.com',0,1,'Test','','Student','09123456781','USER',1,0,'','2026-08-17 01:40:53.206279',0),(2,'pbkdf2_sha256$1200000$o1yryQHboDM7ktIQe01Yt1$Mg0mYBeT5y4uY0/gsF0Ao7PmRrvXkkpVtyeIh022llo=',NULL,0,'spencerjulesramirez66@gmail.com',0,1,'Spencer','','Ramirez','09123456782','USER',1,0,'','2026-08-17 01:40:54.030073',0),(3,'pbkdf2_sha256$1200000$TJTQ6ActhjfWaoS6bUN9Tw$LM3AXERgCjzfIyVj7az3BqBz8YDCAdBEkwqecD5o6MI=','2026-09-14 01:58:02.417196',0,'marketplace.demo@usep.edu.ph',1,0,'Marketplace','','Demo','09000000000','USER',1,0,'','2026-09-05 12:53:21.138142',0),(4,'pbkdf2_sha256$1200000$raUXfNZ6Ih2AZuKJincWix$UUeQORfwlmkY+68AmphEDwsKZi0EtBQqGkEebV4VLa0=','2026-09-19 02:18:34.990227',0,'test.buyer@usep.edu.ph',1,0,'Test','','Buyer','09000000001','USER',1,0,'uploads/ScreenShot-2022-5-31_1-28-7.png','2026-09-05 13:00:01.148112',1),(5,'pbkdf2_sha256$1200000$FdmPEdp04XNKBkMwL3pRTR$WQLkk5ZjStjDwVgmIe9XhSZrFJSvkxRS9SP7Bbd/BFU=','2026-09-19 02:19:10.974912',0,'test.seller@usep.edu.ph',1,0,'Miguel','','Rivera','09000000002','USER',1,0,'uploads/anime_guy_in_malcolm_in_the_middle_intro.png','2026-09-05 13:00:01.927283',1),(6,'pbkdf2_sha256$1200000$T9dM0cpWlTPKSEDQnq4598$0bM5IbMFCCj7WwNYbxKywun+Xy4Ln8v1ieSSM35D+2A=','2026-09-14 01:49:45.492992',0,'maria.santos@usep.edu.ph',1,0,'Maria','','Santos','09000000003','USER',1,0,'uploads/Prison_Mike.webp','2026-09-05 13:30:38.371743',1),(7,'pbkdf2_sha256$1200000$KxZnd6APETGs0cywL9LE4e$322Rt3DUO5/zF9LqYTePRXlmxMHGWFkBrUIPB16Pb94=','2026-09-19 07:24:39.666944',0,'juan.reyes@usep.edu.ph',1,0,'Juan','','Reyes','09000000004','USER',1,0,'uploads/aesthetic-pingu-meme-desktop-wallpaper-preview.webp','2026-09-05 13:30:39.108528',1),(8,'pbkdf2_sha256$1200000$gPY6UcLl6GNF5N5koQjNyz$jSG7WAU70bdkErkZXe39KCkl+OVhq1lAXoNUZB/gWMQ=','2026-09-14 01:52:29.788496',0,'elena.gutierrez@usep.edu.ph',1,0,'Elena','','Gutierrez','09000000005','USER',1,0,'','2026-09-05 13:30:39.830558',1);
/*!40000 ALTER TABLE `accounts_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_user_groups`
--

DROP TABLE IF EXISTS `accounts_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_user_groups_user_id_group_id_59c0b32f_uniq` (`user_id`,`group_id`),
  KEY `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` (`group_id`),
  CONSTRAINT `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `accounts_user_groups_user_id_52b62117_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_user_groups`
--

LOCK TABLES `accounts_user_groups` WRITE;
/*!40000 ALTER TABLE `accounts_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `accounts_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `accounts_user_user_permissions`
--

DROP TABLE IF EXISTS `accounts_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `accounts_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_user_user_permi_user_id_permission_id_2ab516c2_uniq` (`user_id`,`permission_id`),
  KEY `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` (`permission_id`),
  CONSTRAINT `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `accounts_user_user_p_user_id_e4f0a161_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `accounts_user_user_permissions`
--

LOCK TABLES `accounts_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `accounts_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `accounts_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=97 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add campus',1,'add_campus'),(2,'Can change campus',1,'change_campus'),(3,'Can delete campus',1,'delete_campus'),(4,'Can view campus',1,'view_campus'),(5,'Can add college',2,'add_college'),(6,'Can change college',2,'change_college'),(7,'Can delete college',2,'delete_college'),(8,'Can view college',2,'view_college'),(9,'Can add user',8,'add_user'),(10,'Can change user',8,'change_user'),(11,'Can delete user',8,'delete_user'),(12,'Can view user',8,'view_user'),(13,'Can add program',5,'add_program'),(14,'Can change program',5,'change_program'),(15,'Can delete program',5,'delete_program'),(16,'Can view program',5,'view_program'),(17,'Can add major',4,'add_major'),(18,'Can change major',4,'change_major'),(19,'Can delete major',4,'delete_major'),(20,'Can view major',4,'view_major'),(21,'Can add staff profile',6,'add_staffprofile'),(22,'Can change staff profile',6,'change_staffprofile'),(23,'Can delete staff profile',6,'delete_staffprofile'),(24,'Can view staff profile',6,'view_staffprofile'),(25,'Can add student profile',7,'add_studentprofile'),(26,'Can change student profile',7,'change_studentprofile'),(27,'Can delete student profile',7,'delete_studentprofile'),(28,'Can view student profile',7,'view_studentprofile'),(29,'Can add email otp',3,'add_emailotp'),(30,'Can change email otp',3,'change_emailotp'),(31,'Can delete email otp',3,'delete_emailotp'),(32,'Can view email otp',3,'view_emailotp'),(33,'Can add log entry',9,'add_logentry'),(34,'Can change log entry',9,'change_logentry'),(35,'Can delete log entry',9,'delete_logentry'),(36,'Can view log entry',9,'view_logentry'),(37,'Can add permission',11,'add_permission'),(38,'Can change permission',11,'change_permission'),(39,'Can delete permission',11,'delete_permission'),(40,'Can view permission',11,'view_permission'),(41,'Can add group',10,'add_group'),(42,'Can change group',10,'change_group'),(43,'Can delete group',10,'delete_group'),(44,'Can view group',10,'view_group'),(45,'Can add content type',12,'add_contenttype'),(46,'Can change content type',12,'change_contenttype'),(47,'Can delete content type',12,'delete_contenttype'),(48,'Can view content type',12,'view_contenttype'),(49,'Can add session',13,'add_session'),(50,'Can change session',13,'change_session'),(51,'Can delete session',13,'delete_session'),(52,'Can view session',13,'view_session'),(53,'Can add category',14,'add_category'),(54,'Can change category',14,'change_category'),(55,'Can delete category',14,'delete_category'),(56,'Can view category',14,'view_category'),(57,'Can add listing',16,'add_listing'),(58,'Can change listing',16,'change_listing'),(59,'Can delete listing',16,'delete_listing'),(60,'Can view listing',16,'view_listing'),(61,'Can add conversation',15,'add_conversation'),(62,'Can change conversation',15,'change_conversation'),(63,'Can delete conversation',15,'delete_conversation'),(64,'Can view conversation',15,'view_conversation'),(65,'Can add message',17,'add_message'),(66,'Can change message',17,'change_message'),(67,'Can delete message',17,'delete_message'),(68,'Can view message',17,'view_message'),(69,'Can add saved item',18,'add_saveditem'),(70,'Can change saved item',18,'change_saveditem'),(71,'Can delete saved item',18,'delete_saveditem'),(72,'Can view saved item',18,'view_saveditem'),(73,'Can add listing image',19,'add_listingimage'),(74,'Can change listing image',19,'change_listingimage'),(75,'Can delete listing image',19,'delete_listingimage'),(76,'Can view listing image',19,'view_listingimage'),(77,'Can add listing transaction',20,'add_listingtransaction'),(78,'Can change listing transaction',20,'change_listingtransaction'),(79,'Can delete listing transaction',20,'delete_listingtransaction'),(80,'Can view listing transaction',20,'view_listingtransaction'),(81,'Can add seller profile',21,'add_sellerprofile'),(82,'Can change seller profile',21,'change_sellerprofile'),(83,'Can delete seller profile',21,'delete_sellerprofile'),(84,'Can view seller profile',21,'view_sellerprofile'),(85,'Can add message revision',22,'add_messagerevision'),(86,'Can change message revision',22,'change_messagerevision'),(87,'Can delete message revision',22,'delete_messagerevision'),(88,'Can view message revision',22,'view_messagerevision'),(89,'Can add conversation user state',23,'add_conversationuserstate'),(90,'Can change conversation user state',23,'change_conversationuserstate'),(91,'Can delete conversation user state',23,'delete_conversationuserstate'),(92,'Can view conversation user state',23,'view_conversationuserstate'),(93,'Can add message attachment',24,'add_messageattachment'),(94,'Can change message attachment',24,'change_messageattachment'),(95,'Can delete message attachment',24,'delete_messageattachment'),(96,'Can view message attachment',24,'view_messageattachment');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dashboard_category`
--

DROP TABLE IF EXISTS `dashboard_category`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dashboard_category` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `slug` varchar(110) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `slug` (`slug`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dashboard_category`
--

LOCK TABLES `dashboard_category` WRITE;
/*!40000 ALTER TABLE `dashboard_category` DISABLE KEYS */;
INSERT INTO `dashboard_category` VALUES (1,'Textbooks','textbooks'),(2,'Electronics','electronics'),(3,'Uniforms','uniforms'),(4,'Dorm essentials','dorm-essentials'),(5,'Services','services');
/*!40000 ALTER TABLE `dashboard_category` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dashboard_conversation`
--

DROP TABLE IF EXISTS `dashboard_conversation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dashboard_conversation` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `buyer_id` bigint NOT NULL,
  `seller_id` bigint NOT NULL,
  `listing_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_conversation_per_listing` (`buyer_id`,`seller_id`,`listing_id`),
  KEY `dashboard_conversation_seller_id_d672d592_fk_accounts_user_id` (`seller_id`),
  KEY `dashboard_conversati_listing_id_ab6c2b21_fk_dashboard` (`listing_id`),
  CONSTRAINT `dashboard_conversati_listing_id_ab6c2b21_fk_dashboard` FOREIGN KEY (`listing_id`) REFERENCES `dashboard_listing` (`id`),
  CONSTRAINT `dashboard_conversation_buyer_id_2cf14546_fk_accounts_user_id` FOREIGN KEY (`buyer_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `dashboard_conversation_seller_id_d672d592_fk_accounts_user_id` FOREIGN KEY (`seller_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dashboard_conversation`
--

LOCK TABLES `dashboard_conversation` WRITE;
/*!40000 ALTER TABLE `dashboard_conversation` DISABLE KEYS */;
INSERT INTO `dashboard_conversation` VALUES (1,'2026-09-05 13:02:37.211299','2026-09-19 03:13:00.487354',4,5,3),(2,'2026-09-19 03:27:08.194122','2026-09-19 09:02:10.203252',5,4,14),(3,'2026-09-19 07:24:01.114027','2026-09-19 15:32:16.925085',4,7,10),(4,'2026-09-19 07:32:41.862284','2026-09-19 07:32:41.862307',7,5,8),(5,'2026-09-19 09:21:02.726078','2026-09-19 14:59:55.419907',7,4,16),(6,'2026-09-19 09:30:02.524877','2026-09-19 09:58:27.675146',7,4,14);
/*!40000 ALTER TABLE `dashboard_conversation` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dashboard_conversationuserstate`
--

DROP TABLE IF EXISTS `dashboard_conversationuserstate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dashboard_conversationuserstate` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `cleared_at` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `cleared_through_message_id` bigint DEFAULT NULL,
  `conversation_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_conversation_user_state` (`conversation_id`,`user_id`),
  KEY `dashboard_conversati_cleared_through_mess_20c4b292_fk_dashboard` (`cleared_through_message_id`),
  KEY `dashboard_conversati_user_id_31f64af6_fk_accounts_` (`user_id`),
  CONSTRAINT `dashboard_conversati_cleared_through_mess_20c4b292_fk_dashboard` FOREIGN KEY (`cleared_through_message_id`) REFERENCES `dashboard_message` (`id`),
  CONSTRAINT `dashboard_conversati_conversation_id_bbe5aba8_fk_dashboard` FOREIGN KEY (`conversation_id`) REFERENCES `dashboard_conversation` (`id`),
  CONSTRAINT `dashboard_conversati_user_id_31f64af6_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dashboard_conversationuserstate`
--

LOCK TABLES `dashboard_conversationuserstate` WRITE;
/*!40000 ALTER TABLE `dashboard_conversationuserstate` DISABLE KEYS */;
INSERT INTO `dashboard_conversationuserstate` VALUES (1,'2026-09-19 09:58:39.799888','2026-09-19 09:55:37.795855','2026-09-19 09:58:39.799971',55,6,4),(2,'2026-09-19 09:58:35.532334','2026-09-19 09:58:35.531276','2026-09-19 09:58:35.532443',55,6,7);
/*!40000 ALTER TABLE `dashboard_conversationuserstate` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dashboard_listing`
--

DROP TABLE IF EXISTS `dashboard_listing`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dashboard_listing` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(180) COLLATE utf8mb4_unicode_ci NOT NULL,
  `slug` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `condition` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `location` varchar(180) COLLATE utf8mb4_unicode_ci NOT NULL,
  `image` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `views` int unsigned NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `category_id` bigint NOT NULL,
  `seller_id` bigint NOT NULL,
  `image_urls` json NOT NULL DEFAULT (_utf8mb4'[]'),
  `stock_quantity` int unsigned NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  KEY `dashboard_l_status_037e2b_idx` (`status`,`created_at`),
  KEY `dashboard_l_seller__1029af_idx` (`seller_id`,`status`),
  KEY `dashboard_listing_category_id_107db240_fk_dashboard_category_id` (`category_id`),
  CONSTRAINT `dashboard_listing_category_id_107db240_fk_dashboard_category_id` FOREIGN KEY (`category_id`) REFERENCES `dashboard_category` (`id`),
  CONSTRAINT `dashboard_listing_seller_id_f7a997c3_fk_accounts_user_id` FOREIGN KEY (`seller_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `dashboard_listing_chk_1` CHECK ((`views` >= 0)),
  CONSTRAINT `dashboard_listing_chk_2` CHECK ((`stock_quantity` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dashboard_listing`
--

LOCK TABLES `dashboard_listing` WRITE;
/*!40000 ALTER TABLE `dashboard_listing` DISABLE KEYS */;
INSERT INTO `dashboard_listing` VALUES (1,'Engineering Mechanics Textbook','engineering-mechanics-textbook','4th edition textbook with minimal highlighting. All pages are intact.',450.00,'Good condition','USeP campus','listings/engineeringmechanics.webp','ACTIVE',6,'2026-09-05 12:53:21.144587','2026-09-14 01:58:24.297817',1,3,'[]',1),(2,'Scientific Calculator','scientific-calculator','Casio fx-991 in excellent working condition.',900.00,'Barely used','USeP campus','listings/calclator.webp','ACTIVE',1,'2026-09-05 12:53:21.147834','2026-09-14 01:58:15.826297',2,3,'[]',1),(3,'Calculus Textbook','test-seller-calculus-book','A clean calculus textbook ready for another student.',550.00,'Good condition','USeP campus library','listings/calculus.webp','ACTIVE',8,'2026-09-05 13:00:01.930419','2026-09-14 01:48:31.728083',1,5,'[]',1),(4,'USB-C Multi-Charger','test-seller-usb-charger','Compact charger with multiple ports for campus use.',450.00,'Like new','USeP campus library','listings/usb_c_multicharger.webp','ACTIVE',2,'2026-09-05 13:00:01.933809','2026-09-14 01:48:23.393012',2,5,'[]',1),(5,'Adjustable Study Lamp','test-seller-study-lamp','Desk lamp with adjustable brightness for late-night study.',650.00,'Barely used','USeP campus library','listings/adjustablelamp.webp','ACTIVE',1,'2026-09-05 13:00:01.937005','2026-09-14 01:48:16.284107',4,5,'[]',1),(6,'Resume Review Service','test-seller-resume-help','One-on-one resume review and improvement suggestions.',250.00,'Available by appointment','Online or USeP campus','listings/resume_review.webp','ACTIVE',10,'2026-09-05 13:00:01.939663','2026-09-14 01:48:01.246888',5,5,'[]',0),(7,'Test listing','test-listing','sdfsdfsdfsdf',1212122.00,'Barely used','OSAS','listings/ScreenShot-2022-5-31_1-46-46_hHZJFWo.png','SOLD',24,'2026-09-05 13:05:50.303825','2026-09-06 10:40:35.846834',2,5,'[]',1),(8,'Kratos Gwapo','sdasdasd','asdasdasdasd',123123.00,'Like new','OSAS','listings/ScreenShot-2022-5-31_1-28-7.png','ACTIVE',33,'2026-09-05 13:19:55.954986','2026-09-05 14:33:32.152455',2,5,'[]',1),(9,'Engineering Mechanics Notes','maria-engineering-notes','Organized review notes for engineering mechanics.',180.00,'Good condition','Engineering building','listings/engineeringnotes.webp','ACTIVE',2,'2026-09-05 13:30:38.375214','2026-09-14 01:50:47.076708',1,6,'[]',1),(10,'Python Programming Book','juan-programming-book','Beginner-friendly Python reference book.',380.00,'Like new','ICT building','listings/pythonprogramming.webp','ACTIVE',2,'2026-09-05 13:30:39.111092','2026-09-14 01:51:29.246686',1,7,'[]',1),(11,'PE Uniform, Medium','elena-pe-uniform','Clean campus PE uniform in medium size.',250.00,'Good condition','Student center','listings/PE.webp','ACTIVE',7,'2026-09-05 13:30:39.834129','2026-09-14 01:52:52.484993',3,8,'[]',1),(14,'Test Listing for Video','test-listing-for-video-idfk','Ambot nigger',121212.00,'Good condition','OSAS','listings/listings/1c8d22426a601810c705f0491b51a6ba.webp','ACTIVE',30,'2026-09-06 10:36:47.450667','2026-09-14 03:00:09.600815',4,4,'[]',6),(15,'Test 123','test-123','12121reaewf sffdfgs',121212.00,'Good condition','OSAS','listings/A_dope_ass_wallpaper_I_found_on_yt_its_download_link_is_broken_lol.png','ARCHIVED',12,'2026-09-09 10:27:35.678402','2026-09-09 10:41:16.403668',3,4,'[]',6),(16,'System Development','system-development','Can help you build a system for thesis',1212.00,'Available by appointment','USeP campus','listings/Heckercat.webp','ACTIVE',11,'2026-09-14 02:23:44.563416','2026-09-19 01:57:20.761676',5,4,'[]',0),(17,'test for db','test-for-db','ueifhiweufh',232323.00,'Like new','USeP campus','','ACTIVE',1,'2026-09-14 03:01:15.757385','2026-09-14 03:01:15.757432',1,4,'[]',5);
/*!40000 ALTER TABLE `dashboard_listing` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dashboard_listingimage`
--

DROP TABLE IF EXISTS `dashboard_listingimage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dashboard_listingimage` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `image` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `listing_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `dashboard_listingima_listing_id_08ef0340_fk_dashboard` (`listing_id`),
  CONSTRAINT `dashboard_listingima_listing_id_08ef0340_fk_dashboard` FOREIGN KEY (`listing_id`) REFERENCES `dashboard_listing` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=56 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dashboard_listingimage`
--

LOCK TABLES `dashboard_listingimage` WRITE;
/*!40000 ALTER TABLE `dashboard_listingimage` DISABLE KEYS */;
INSERT INTO `dashboard_listingimage` VALUES (1,'listings/gallery/ScreenShot-2022-5-31_1-28-7.png','2026-09-05 13:19:55.986098',8),(2,'listings/gallery/ScreenShot-2022-5-31_1-45-44.png','2026-09-05 13:19:56.004542',8),(3,'listings/gallery/ScreenShot-2022-5-31_1-46-46.png','2026-09-05 13:19:56.020364',8),(31,'listings/gallery/1c8d22426a601810c705f0491b51a6ba_52iR7Qn.jpg','2026-09-06 10:36:47.464380',14),(32,'listings/gallery/5159aMovjzL_xEr7Gwn.jpg','2026-09-06 10:36:47.469708',14),(35,'listings/gallery/ScreenShot-2022-12-28_1-22-26.png','2026-09-06 10:37:18.584583',14),(37,'listings/gallery/ScreenShot-2022-5-31_1-46-46_CHPvuNg.png','2026-09-06 10:40:13.653499',7),(38,'listings/gallery/ScreenShot-2022-5-31_1-50-57_AkzWlJH.png','2026-09-06 10:40:13.675963',7),(39,'listings/gallery/ScreenShot-2022-5-31_1-52-14_cpEhP6i.png','2026-09-06 10:40:13.692890',7),(40,'listings/gallery/ScreenShot-2022-5-31_1-48-2.png','2026-09-06 10:40:29.515038',7),(41,'listings/gallery/RobloxScreenShot20260326_233507720.png','2026-09-06 17:07:45.085004',14),(42,'listings/gallery/A_dope_ass_wallpaper_I_found_on_yt_its_download_link_is_broken_lol.png','2026-09-09 10:27:35.707468',15),(43,'listings/gallery/Another_screenshot_of_my_cool_background.png','2026-09-09 10:27:35.727753',15),(45,'listings/gallery/resume_review.webp','2026-09-14 01:48:01.397939',6),(46,'listings/gallery/adjustablelamp.webp','2026-09-14 01:48:16.489941',5),(47,'listings/gallery/usb_c_multicharger.webp','2026-09-14 01:48:23.516260',4),(48,'listings/gallery/calculus.webp','2026-09-14 01:48:31.879423',3),(49,'listings/gallery/engineeringnotes.webp','2026-09-14 01:50:47.449633',9),(50,'listings/gallery/pythonprogramming.webp','2026-09-14 01:51:29.339496',10),(51,'listings/gallery/PE.webp','2026-09-14 01:52:52.587007',11),(52,'listings/gallery/calclator.webp','2026-09-14 01:58:15.925400',2),(53,'listings/gallery/engineeringmechanics.webp','2026-09-14 01:58:24.401152',1),(54,'listings/gallery/Heckercat.webp','2026-09-14 02:23:44.580364',16),(55,'listings/gallery/cat.webp','2026-09-19 01:57:20.939092',16);
/*!40000 ALTER TABLE `dashboard_listingimage` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dashboard_listingtransaction`
--

DROP TABLE IF EXISTS `dashboard_listingtransaction`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dashboard_listingtransaction` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `quantity` int unsigned NOT NULL,
  `payment_method` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payment_proof` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `buyer_id` bigint DEFAULT NULL,
  `listing_id` bigint NOT NULL,
  `seller_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `dashboard_listingtra_buyer_id_92f1434b_fk_accounts_` (`buyer_id`),
  KEY `dashboard_listingtra_listing_id_7fa6dcc4_fk_dashboard` (`listing_id`),
  KEY `dashboard_listingtra_seller_id_b6390631_fk_accounts_` (`seller_id`),
  CONSTRAINT `dashboard_listingtra_buyer_id_92f1434b_fk_accounts_` FOREIGN KEY (`buyer_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `dashboard_listingtra_listing_id_7fa6dcc4_fk_dashboard` FOREIGN KEY (`listing_id`) REFERENCES `dashboard_listing` (`id`),
  CONSTRAINT `dashboard_listingtra_seller_id_b6390631_fk_accounts_` FOREIGN KEY (`seller_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `dashboard_listingtransaction_chk_1` CHECK ((`quantity` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dashboard_listingtransaction`
--

LOCK TABLES `dashboard_listingtransaction` WRITE;
/*!40000 ALTER TABLE `dashboard_listingtransaction` DISABLE KEYS */;
INSERT INTO `dashboard_listingtransaction` VALUES (1,1,'CASH','','2026-09-07 02:02:13.630205',4,14,4);
/*!40000 ALTER TABLE `dashboard_listingtransaction` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dashboard_message`
--

DROP TABLE IF EXISTS `dashboard_message`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dashboard_message` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `body` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `is_read` tinyint(1) NOT NULL,
  `conversation_id` bigint NOT NULL,
  `sender_id` bigint NOT NULL,
  `attachment` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `deleted_at` datetime(6) DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `edited_at` datetime(6) DEFAULT NULL,
  `is_edited` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `dashboard_message_conversation_id_2b6f3322_fk_dashboard` (`conversation_id`),
  KEY `dashboard_message_sender_id_1b9e6203_fk_accounts_user_id` (`sender_id`),
  CONSTRAINT `dashboard_message_conversation_id_2b6f3322_fk_dashboard` FOREIGN KEY (`conversation_id`) REFERENCES `dashboard_conversation` (`id`),
  CONSTRAINT `dashboard_message_sender_id_1b9e6203_fk_accounts_user_id` FOREIGN KEY (`sender_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=75 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dashboard_message`
--

LOCK TABLES `dashboard_message` WRITE;
/*!40000 ALTER TABLE `dashboard_message` DISABLE KEYS */;
INSERT INTO `dashboard_message` VALUES (1,'Hi, is this listing still available?','2026-09-05 13:02:37.216068',1,1,4,NULL,NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(2,'Hi! Is the calculus textbook still available for pickup on campus?','2026-09-19 02:30:49.596258',1,1,4,NULL,NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(3,'Yes, it is available. We can meet near the library this week.','2026-09-19 02:30:49.600028',1,1,5,NULL,NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(4,'fdgdfg','2026-09-19 03:05:53.593066',1,1,4,'',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(5,'wait whatttt','2026-09-19 03:13:00.483467',1,1,5,'',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(6,'hello is this still available?','2026-09-19 03:27:24.651452',1,2,5,'',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(7,'','2026-09-19 03:27:29.113978',1,2,5,'messages/a580.png',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(8,'hello uh yes dumbass','2026-09-19 04:20:30.322135',1,2,4,'',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(9,'','2026-09-19 04:20:50.632377',1,2,4,'messages/5159aMovjzL.jpg',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(10,'alright testing','2026-09-19 04:27:53.901733',1,2,4,'',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(11,'awesome i got your bitchass message fuck you','2026-09-19 04:28:07.385680',1,2,5,'',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(12,'ey fuck you','2026-09-19 04:28:13.119421',1,2,4,'',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(13,'','2026-09-19 04:28:27.428979',1,2,5,'messages/editorirjmisSLOAP-4517838-45.pdf',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(14,'cool','2026-09-19 04:28:39.223586',1,2,5,'',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(15,'https://www.youtube.com/watch?v=-05WmSAmLK4','2026-09-19 04:28:57.583770',1,2,4,'',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(16,'https://www.youtube.com/watch?v=h8yfMjX_mnw','2026-09-19 04:44:49.435531',1,2,4,'',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(17,'Good morning everyone. Share ko diri sa link sa pictures kagabie. Thanks to Bern ni Sofia..😀..https://drive.google.com/drive/folders/1S5q26dMrG5-IjwD4VA58KolEjtbnKtI3?usp=sharing','2026-09-19 04:48:55.749124',1,2,4,'','2026-09-19 06:47:43.567554',1,'2026-09-19 06:47:43.567653',NULL,0),(18,'facebook.com','2026-09-19 04:53:26.189199',1,2,4,'','2026-09-19 05:18:08.308034',1,'2026-09-19 05:18:08.308121',NULL,0),(19,'youtube.com','2026-09-19 04:58:44.010902',1,2,4,'','2026-09-19 05:17:55.520785',1,'2026-09-19 05:17:55.521028',NULL,0),(20,'friv.com','2026-09-19 05:04:04.034787',1,2,5,'',NULL,0,'2026-09-19 05:16:03.576830',NULL,0),(21,'meron din namang ganda ang uisahdaisuhd','2026-09-19 06:49:54.658964',1,2,4,'',NULL,0,'2026-09-19 07:07:22.104477','2026-09-19 07:07:22.104319',1),(22,'pwede nang mangarap','2026-09-19 06:51:02.539279',1,2,5,'',NULL,0,'2026-09-19 06:51:02.539297',NULL,0),(23,'hi','2026-09-19 06:51:09.758462',1,2,5,'','2026-09-19 06:51:41.553742',1,'2026-09-19 06:51:41.553884',NULL,0),(24,'hello','2026-09-19 06:51:12.555022',1,2,4,'',NULL,0,'2026-09-19 06:51:12.555038',NULL,0),(25,'hello','2026-09-19 07:24:53.654596',1,3,4,'',NULL,0,'2026-09-19 07:24:53.654613',NULL,0),(26,'pakyu','2026-09-19 07:25:02.512746',1,3,7,'',NULL,0,'2026-09-19 07:32:27.233965','2026-09-19 07:32:27.233769',1),(27,'asdasda','2026-09-19 07:32:56.647524',1,3,4,'',NULL,0,'2026-09-19 07:32:56.647542',NULL,0),(28,'naa pani bitchass?','2026-09-19 07:42:42.477543',1,3,4,'',NULL,0,'2026-09-19 07:42:42.477564',NULL,0),(29,'hello','2026-09-19 07:46:38.900528',1,3,4,'',NULL,0,'2026-09-19 07:46:38.900546',NULL,0),(30,'bitvch','2026-09-19 07:46:53.503719',1,3,7,'',NULL,0,'2026-09-19 07:46:53.503735',NULL,0),(31,'sdfsd','2026-09-19 07:47:00.461333',1,3,7,'',NULL,0,'2026-09-19 07:47:00.461356',NULL,0),(32,'sdfsdfs','2026-09-19 07:52:53.482161',1,3,7,'',NULL,0,'2026-09-19 07:52:53.482180',NULL,0),(33,'sadasd','2026-09-19 07:53:10.440792',1,3,4,'',NULL,0,'2026-09-19 07:53:10.440809',NULL,0),(34,'asdasd','2026-09-19 07:53:18.961373',1,3,4,'',NULL,0,'2026-09-19 07:53:18.961389',NULL,0),(35,'sdfsdf','2026-09-19 07:59:16.743630',1,3,4,'',NULL,0,'2026-09-19 07:59:16.743647',NULL,0),(36,'fuck you','2026-09-19 08:05:14.027912',1,3,7,'',NULL,0,'2026-09-19 08:05:14.027928',NULL,0),(37,'pwede nang mangarap','2026-09-19 08:05:45.008772',1,3,4,'',NULL,0,'2026-09-19 08:18:48.814401','2026-09-19 08:18:48.814303',1),(38,'hey fuck you','2026-09-19 08:09:34.594801',1,3,7,'',NULL,0,'2026-09-19 08:09:34.594820',NULL,0),(39,'sdfs\\','2026-09-19 08:09:44.192467',1,3,7,'',NULL,0,'2026-09-19 08:09:44.192486',NULL,0),(40,'sadasda','2026-09-19 08:09:53.716584',1,3,7,'',NULL,0,'2026-09-19 08:09:53.716612',NULL,0),(41,'hello','2026-09-19 08:14:43.299718',1,3,7,'',NULL,0,'2026-09-19 08:14:43.299748',NULL,0),(42,'asdasda','2026-09-19 08:22:16.178279',1,3,7,'',NULL,0,'2026-09-19 08:22:16.178299',NULL,0),(43,'bitch','2026-09-19 08:26:24.078824',1,3,7,'',NULL,0,'2026-09-19 08:26:24.078846',NULL,0),(44,'asdasd','2026-09-19 08:26:46.459221',1,3,7,'','2026-09-19 08:27:43.771396',1,'2026-09-19 08:27:43.771495',NULL,0),(45,'oishsoadh','2026-09-19 08:52:38.773073',1,3,7,'',NULL,0,'2026-09-19 08:52:38.773091',NULL,0),(46,'asdasdas','2026-09-19 08:52:53.852234',1,3,7,'',NULL,0,'2026-09-19 08:52:53.852253',NULL,0),(47,'Sasa','2026-09-19 08:53:15.797802',1,3,7,'messages/1660ti.jpg',NULL,0,'2026-09-19 08:53:15.797830',NULL,0),(48,'FB.COM','2026-09-19 08:53:41.011710',1,3,4,'',NULL,0,'2026-09-19 08:53:41.011728',NULL,0),(49,'https://www.youtube.com/watch?v=h8yfMjX_mnw','2026-09-19 08:54:03.691019',1,3,4,'',NULL,0,'2026-09-19 08:54:03.691037',NULL,0),(50,'Good morning everyone. Share ko diri sa link sa pictures kagabie. Thanks to Bern ni Sofia..😀..https://drive.google.com/drive/folders/1S5q26dMrG5-IjwD4VA58KolEjtbnKtI3?usp=sharing','2026-09-19 09:02:10.196374',0,2,4,'',NULL,0,'2026-09-19 09:02:10.196397',NULL,0),(51,'thats goood','2026-09-19 09:20:20.101513',1,3,4,'',NULL,0,'2026-09-19 09:20:20.101531',NULL,0),(52,'sdfsdwf','2026-09-19 09:20:29.582106',1,3,4,'',NULL,0,'2026-09-19 09:20:29.582124',NULL,0),(53,'hey bitch wtf im not typing anymore','2026-09-19 09:21:11.722728',1,5,7,'',NULL,0,'2026-09-19 14:59:55.418434','2026-09-19 14:59:55.418231',1),(54,'hello','2026-09-19 09:37:58.663968',1,6,7,'',NULL,0,'2026-09-19 09:37:58.663995',NULL,0),(55,'FUCK YOU','2026-09-19 09:58:27.665131',1,6,7,'',NULL,0,'2026-09-19 09:58:27.665150',NULL,0),(56,'HELLO','2026-09-19 09:59:35.141163',1,5,7,'',NULL,0,'2026-09-19 09:59:35.141181',NULL,0),(57,'gf dfsdg\\','2026-09-19 09:59:48.863655',1,3,7,'',NULL,0,'2026-09-19 09:59:48.863676',NULL,0),(58,'asdasd','2026-09-19 09:59:54.200192',1,3,7,'',NULL,0,'2026-09-19 09:59:54.200211',NULL,0),(59,'hoy','2026-09-19 10:05:45.586320',1,3,7,'',NULL,0,'2026-09-19 10:05:45.586350',NULL,0),(60,'asdasd','2026-09-19 10:16:36.328836',1,3,7,'','2026-09-19 10:16:46.078417',1,'2026-09-19 10:16:46.078519',NULL,0),(61,'ill edit this 3','2026-09-19 10:16:52.563299',1,3,7,'',NULL,0,'2026-09-19 10:17:04.743093','2026-09-19 10:17:04.743009',1),(62,'dasdas','2026-09-19 10:17:23.072581',1,3,4,'','2026-09-19 10:17:42.792609',1,'2026-09-19 10:17:42.792764',NULL,0),(63,'this is it','2026-09-19 14:13:32.373851',1,3,7,'',NULL,0,'2026-09-19 14:13:32.373869',NULL,0),(64,'asdas','2026-09-19 14:33:42.535826',1,3,7,'',NULL,0,'2026-09-19 14:33:42.535846',NULL,0),(65,'asddsasd','2026-09-19 14:33:50.497929',1,3,4,'',NULL,0,'2026-09-19 14:33:50.497957',NULL,0),(66,'asdasd','2026-09-19 14:33:57.970845',1,3,7,'',NULL,0,'2026-09-19 14:33:57.970864',NULL,0),(67,'asd','2026-09-19 14:43:52.135327',1,3,4,'',NULL,0,'2026-09-19 14:43:52.135347',NULL,0),(68,'gfdfgfdg','2026-09-19 15:13:08.364489',1,3,7,'',NULL,0,'2026-09-19 15:13:08.364508',NULL,0),(69,'uydtguasydgasuydg\'','2026-09-19 15:30:57.995272',1,3,7,'',NULL,0,'2026-09-19 15:30:57.995291',NULL,0),(70,'helllo','2026-09-19 15:31:19.994323',1,3,7,'',NULL,0,'2026-09-19 15:31:19.994346',NULL,0),(71,'hello','2026-09-19 15:31:24.030140',1,3,4,'',NULL,0,'2026-09-19 15:31:24.030170',NULL,0),(72,'asdasd','2026-09-19 15:31:53.010453',1,3,4,'',NULL,0,'2026-09-19 15:31:53.010475',NULL,0),(73,'asdasd','2026-09-19 15:32:04.897461',1,3,7,'',NULL,0,'2026-09-19 15:32:04.897487',NULL,0),(74,'hello 123','2026-09-19 15:32:16.910811',1,3,4,'',NULL,0,'2026-09-19 15:32:16.910837',NULL,0);
/*!40000 ALTER TABLE `dashboard_message` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dashboard_messageattachment`
--

DROP TABLE IF EXISTS `dashboard_messageattachment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dashboard_messageattachment` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `file` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `message_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `dashboard_messageatt_message_id_721533f3_fk_dashboard` (`message_id`),
  CONSTRAINT `dashboard_messageatt_message_id_721533f3_fk_dashboard` FOREIGN KEY (`message_id`) REFERENCES `dashboard_message` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dashboard_messageattachment`
--

LOCK TABLES `dashboard_messageattachment` WRITE;
/*!40000 ALTER TABLE `dashboard_messageattachment` DISABLE KEYS */;
/*!40000 ALTER TABLE `dashboard_messageattachment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dashboard_messagerevision`
--

DROP TABLE IF EXISTS `dashboard_messagerevision`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dashboard_messagerevision` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `body` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `edited_at` datetime(6) NOT NULL,
  `editor_id` bigint NOT NULL,
  `message_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `dashboard_messagerevision_editor_id_0b6dcb58_fk_accounts_user_id` (`editor_id`),
  KEY `dashboard_messagerev_message_id_8b742f87_fk_dashboard` (`message_id`),
  CONSTRAINT `dashboard_messagerev_message_id_8b742f87_fk_dashboard` FOREIGN KEY (`message_id`) REFERENCES `dashboard_message` (`id`),
  CONSTRAINT `dashboard_messagerevision_editor_id_0b6dcb58_fk_accounts_user_id` FOREIGN KEY (`editor_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dashboard_messagerevision`
--

LOCK TABLES `dashboard_messagerevision` WRITE;
/*!40000 ALTER TABLE `dashboard_messagerevision` DISABLE KEYS */;
INSERT INTO `dashboard_messagerevision` VALUES (1,'meron din namang ganda ang buhay','2026-09-19 07:07:22.103267',4,21),(2,'hello','2026-09-19 07:32:27.232891',7,26),(3,'sadasdas','2026-09-19 08:18:48.813390',4,37),(4,'ill edit this','2026-09-19 10:16:57.806455',7,61),(5,'ill edit this 1','2026-09-19 10:17:02.213908',7,61),(6,'ill edit this 2','2026-09-19 10:17:04.742268',7,61),(7,'hello','2026-09-19 14:59:55.415735',7,53);
/*!40000 ALTER TABLE `dashboard_messagerevision` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dashboard_saveditem`
--

DROP TABLE IF EXISTS `dashboard_saveditem`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dashboard_saveditem` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(6) NOT NULL,
  `buyer_id` bigint NOT NULL,
  `listing_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_saved_listing_per_buyer` (`buyer_id`,`listing_id`),
  KEY `dashboard_saveditem_listing_id_43d5a8b6_fk_dashboard_listing_id` (`listing_id`),
  CONSTRAINT `dashboard_saveditem_buyer_id_c820b66e_fk_accounts_user_id` FOREIGN KEY (`buyer_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `dashboard_saveditem_listing_id_43d5a8b6_fk_dashboard_listing_id` FOREIGN KEY (`listing_id`) REFERENCES `dashboard_listing` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dashboard_saveditem`
--

LOCK TABLES `dashboard_saveditem` WRITE;
/*!40000 ALTER TABLE `dashboard_saveditem` DISABLE KEYS */;
INSERT INTO `dashboard_saveditem` VALUES (5,'2026-09-05 14:08:35.859227',5,9),(6,'2026-09-05 14:09:59.266336',6,8),(12,'2026-09-19 09:20:39.175036',7,8),(13,'2026-09-19 14:36:22.208691',7,6);
/*!40000 ALTER TABLE `dashboard_saveditem` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext COLLATE utf8mb4_unicode_ci,
  `object_repr` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (1,'accounts','campus'),(2,'accounts','college'),(3,'accounts','emailotp'),(4,'accounts','major'),(5,'accounts','program'),(21,'accounts','sellerprofile'),(6,'accounts','staffprofile'),(7,'accounts','studentprofile'),(8,'accounts','user'),(9,'admin','logentry'),(10,'auth','group'),(11,'auth','permission'),(12,'contenttypes','contenttype'),(14,'dashboard','category'),(15,'dashboard','conversation'),(23,'dashboard','conversationuserstate'),(16,'dashboard','listing'),(19,'dashboard','listingimage'),(20,'dashboard','listingtransaction'),(17,'dashboard','message'),(24,'dashboard','messageattachment'),(22,'dashboard','messagerevision'),(18,'dashboard','saveditem'),(13,'sessions','session');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=45 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2026-08-17 01:40:50.628428'),(2,'contenttypes','0002_remove_content_type_name','2026-08-17 01:40:50.736470'),(3,'auth','0001_initial','2026-08-17 01:40:51.036330'),(4,'auth','0002_alter_permission_name_max_length','2026-08-17 01:40:51.102862'),(5,'auth','0003_alter_user_email_max_length','2026-08-17 01:40:51.114053'),(6,'auth','0004_alter_user_username_opts','2026-08-17 01:40:51.120663'),(7,'auth','0005_alter_user_last_login_null','2026-08-17 01:40:51.127375'),(8,'auth','0006_require_contenttypes_0002','2026-08-17 01:40:51.131537'),(9,'auth','0007_alter_validators_add_error_messages','2026-08-17 01:40:51.141205'),(10,'auth','0008_alter_user_username_max_length','2026-08-17 01:40:51.149861'),(11,'auth','0009_alter_user_last_name_max_length','2026-08-17 01:40:51.159060'),(12,'auth','0010_alter_group_name_max_length','2026-08-17 01:40:51.184040'),(13,'auth','0011_update_proxy_permissions','2026-08-17 01:40:51.196658'),(14,'auth','0012_alter_user_first_name_max_length','2026-08-17 01:40:51.207620'),(15,'accounts','0001_initial','2026-08-17 01:40:52.226876'),(16,'accounts','0002_database_seeder','2026-08-17 01:40:52.300986'),(17,'accounts','0003_emailotp','2026-08-17 01:40:52.404853'),(18,'accounts','0004_seed_test_users','2026-08-17 01:40:54.036387'),(19,'admin','0001_initial','2026-08-17 01:40:54.208702'),(20,'admin','0002_logentry_remove_auto_add','2026-08-17 01:40:54.218181'),(21,'admin','0003_logentry_add_action_flag_choices','2026-08-17 01:40:54.229880'),(22,'sessions','0001_initial','2026-08-17 01:40:54.271853'),(23,'accounts','0005_emailotp_purpose','2026-08-29 10:13:29.714503'),(24,'dashboard','0001_initial','2026-09-05 12:53:21.090991'),(25,'dashboard','0002_seed_marketplace','2026-09-05 12:53:21.151965'),(26,'dashboard','0003_listing_image_urls','2026-09-05 12:53:21.261970'),(27,'dashboard','0004_seed_test_marketplace_accounts','2026-09-05 13:00:01.943951'),(28,'dashboard','0005_listingimage','2026-09-05 13:14:39.564684'),(29,'dashboard','0006_seed_named_sellers','2026-09-05 13:30:39.837763'),(30,'accounts','0006_user_is_seller','2026-09-05 13:46:23.193426'),(31,'dashboard','0007_mark_seeded_sellers','2026-09-05 13:46:23.214397'),(32,'accounts','0007_normalize_account_profiles','2026-09-06 17:13:56.458070'),(33,'accounts','0008_apply_profile_backfill','2026-09-06 17:13:57.965750'),(34,'dashboard','0008_inventory_and_transactions','2026-09-07 01:54:45.054489'),(35,'dashboard','0009_remove_listing_stock_auto_sold','2026-09-09 10:26:02.377371'),(36,'accounts','0005_seller_profile_and_catalog_cleanup','2026-09-19 02:08:42.583488'),(37,'dashboard','0010_set_marketplace_demo_password','2026-09-19 02:08:43.376502'),(38,'dashboard','0010_seed_sample_conversation','2026-09-19 02:30:49.605086'),(39,'dashboard','0011_message_attachment','2026-09-19 02:30:49.636171'),(40,'dashboard','0012_merge_20260919_1030','2026-09-19 02:30:49.639810'),(41,'dashboard','0012_message_soft_delete','2026-09-19 05:16:03.599979'),(42,'dashboard','0013_message_edit_history','2026-09-19 06:59:20.990603'),(43,'dashboard','0014_conversation_user_state','2026-09-19 09:54:40.870282'),(44,'dashboard','0015_message_attachment_collection','2026-09-19 14:08:48.058304');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `session_data` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
INSERT INTO `django_session` VALUES ('xki8khtj7a8w8s3z7cnjvd5hdb7d2r52','.eJxVjMsOgjAQAP9lz6Zx-6AsR-98A9lui0VNm1A4Gf_dkHDQ68xk3jDxvuVpb2mdlggDeLj8ssDyTOUQ8cHlXpXUsq1LUEeiTtvUWGN63c72b5C5ZRgAySDqxJJsR4F0tDFqmZG8sS74PhgtjOwCu1l6Ik3YoSF_tVqMZQ-fL9yyN0Y:1x7pR9:Oif2CHn01nlBvI_5Q_mGEhVR2_zldJ3dXiqjBr0OYD0','2026-10-03 07:24:39.671765'),('y4o3jnz64x2p3qdqwf4qyr2yz2upkbqv','.eJxVjMsOwiAQAP9lz4bQ5WHp0Xu_gbAsSNVAUtqT8d9Nkx70OjOZN_iwb8XvPa1-YZhAw-WXUYjPVA_Bj1DvTcRWt3UhcSTitF3MjdPrdrZ_gxJ6gQmsVShNJCNtwIEMkbNRSWeiZs7XhCiTlTkTWkwms0NUhuOYR8faDQyfL9cdN9U:1x7kex:Irb6m2_E7rJF2gWguLOxQFQ7ZEKdvS_bd-pifKLBY48','2026-10-03 02:18:35.162938');
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'usep_marketplace'
--

--
-- Dumping routines for database 'usep_marketplace'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-19 23:43:35
