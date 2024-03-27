DROP TABLE IF EXISTS AllBestTrack;
CREATE TABLE AllBestTrack(
   SID              VARCHAR(13) NOT NULL
  ,SEASON           INTEGER  NOT NULL
  ,NUMBER           INTEGER  NOT NULL
  ,BASIN            VARCHAR(2) NOT NULL
  ,SUBBASIN         VARCHAR(2) NOT NULL
  ,NAME             VARCHAR(16) NOT NULL
  ,ISO_TIME         VARCHAR(19) NOT NULL
  ,NATURE           VARCHAR(2) NOT NULL
  ,LAT              NUMERIC(8,5) NOT NULL
  ,LON              NUMERIC(8,5) NOT NULL
  ,WMO_WIND         INTEGER
  ,WMO_PRES         INTEGER
  ,WMO_AGENCY       VARCHAR(10)
  ,TRACK_TYPE       VARCHAR(11) NOT NULL
  ,DIST2LAND        INTEGER  NOT NULL
  ,LANDFALL         INTEGER
  ,IFLAG            VARCHAR(14) NOT NULL
  ,USA_AGENCY       VARCHAR(14)
  ,USA_ATCF_ID      VARCHAR(8)
  ,USA_LAT          NUMERIC(8,5)
  ,USA_LON          NUMERIC(8,5)
  ,USA_RECORD       VARCHAR(1)
  ,USA_STATUS       VARCHAR(2)
  ,USA_WIND         INTEGER
  ,USA_PRES         INTEGER
  ,USA_SSHS         INTEGER  NOT NULL
  ,USA_R34_NE       INTEGER
  ,USA_R34_SE       INTEGER
  ,USA_R34_SW       INTEGER
  ,USA_R34_NW       INTEGER
  ,USA_R50_NE       INTEGER
  ,USA_R50_SE       INTEGER
  ,USA_R50_SW       INTEGER
  ,USA_R50_NW       INTEGER
  ,USA_R64_NE       INTEGER
  ,USA_R64_SE       INTEGER
  ,USA_R64_SW       INTEGER
  ,USA_R64_NW       INTEGER
  ,USA_POCI         INTEGER
  ,USA_ROCI         INTEGER
  ,USA_RMW          INTEGER
  ,USA_EYE          INTEGER
  ,TOKYO_LAT        NUMERIC(8,5)
  ,TOKYO_LON        NUMERIC(8,5)
  ,TOKYO_GRADE      INTEGER
  ,TOKYO_WIND       INTEGER
  ,TOKYO_PRES       INTEGER
  ,TOKYO_R50_DIR    INTEGER
  ,TOKYO_R50_LONG   INTEGER
  ,TOKYO_R50_SHORT  INTEGER
  ,TOKYO_R30_DIR    INTEGER
  ,TOKYO_R30_LONG   INTEGER
  ,TOKYO_R30_SHORT  INTEGER
  ,TOKYO_LAND       BIT
  ,CMA_LAT          NUMERIC(8,5)
  ,CMA_LON          NUMERIC(8,5)
  ,CMA_CAT          INTEGER
  ,CMA_WIND         INTEGER
  ,CMA_PRES         INTEGER
  ,HKO_LAT          NUMERIC(8,5)
  ,HKO_LON          NUMERIC(8,5)
  ,HKO_CAT          VARCHAR(6)
  ,HKO_WIND         INTEGER
  ,HKO_PRES         INTEGER
  ,NEWDELHI_LAT     NUMERIC(8,5)
  ,NEWDELHI_LON     NUMERIC(8,5)
  ,NEWDELHI_GRADE   VARCHAR(4)
  ,NEWDELHI_WIND    INTEGER
  ,NEWDELHI_PRES    INTEGER
  ,NEWDELHI_CI      NUMERIC(7,5)
  ,NEWDELHI_DP      INTEGER
  ,NEWDELHI_POCI    VARCHAR(1)
  ,REUNION_LAT      NUMERIC(8,5)
  ,REUNION_LON      NUMERIC(8,5)
  ,REUNION_TYPE     INTEGER
  ,REUNION_WIND     INTEGER
  ,REUNION_PRES     INTEGER
  ,REUNION_TNUM     NUMERIC(7,5)
  ,REUNION_CI       NUMERIC(7,5)
  ,REUNION_RMW      INTEGER
  ,REUNION_R34_NE   INTEGER
  ,REUNION_R34_SE   INTEGER
  ,REUNION_R34_SW   INTEGER
  ,REUNION_R34_NW   INTEGER
  ,REUNION_R50_NE   INTEGER
  ,REUNION_R50_SE   INTEGER
  ,REUNION_R50_SW   INTEGER
  ,REUNION_R50_NW   INTEGER
  ,REUNION_R64_NE   VARCHAR(1)
  ,REUNION_R64_SE   VARCHAR(1)
  ,REUNION_R64_SW   VARCHAR(1)
  ,REUNION_R64_NW   VARCHAR(1)
  ,BOM_LAT          NUMERIC(8,5)
  ,BOM_LON          NUMERIC(8,5)
  ,BOM_TYPE         INTEGER
  ,BOM_WIND         INTEGER
  ,BOM_PRES         INTEGER
  ,BOM_TNUM         NUMERIC(7,5)
  ,BOM_CI           NUMERIC(7,5)
  ,BOM_RMW          INTEGER
  ,BOM_R34_NE       INTEGER
  ,BOM_R34_SE       INTEGER
  ,BOM_R34_SW       INTEGER
  ,BOM_R34_NW       INTEGER
  ,BOM_R50_NE       INTEGER
  ,BOM_R50_SE       INTEGER
  ,BOM_R50_SW       INTEGER
  ,BOM_R50_NW       INTEGER
  ,BOM_R64_NE       INTEGER
  ,BOM_R64_SE       INTEGER
  ,BOM_R64_SW       INTEGER
  ,BOM_R64_NW       INTEGER
  ,BOM_ROCI         INTEGER
  ,BOM_POCI         INTEGER
  ,BOM_EYE          INTEGER
  ,BOM_POS_METHOD   INTEGER
  ,BOM_PRES_METHOD  INTEGER
  ,NADI_LAT         NUMERIC(8,5)
  ,NADI_LON         NUMERIC(8,5)
  ,NADI_CAT         INTEGER
  ,NADI_WIND        INTEGER
  ,NADI_PRES        INTEGER
  ,WELLINGTON_LAT   NUMERIC(8,5)
  ,WELLINGTON_LON   NUMERIC(8,5)
  ,WELLINGTON_WIND  INTEGER
  ,WELLINGTON_PRES  INTEGER
  ,DS824_LAT        NUMERIC(8,5)
  ,DS824_LON        NUMERIC(8,5)
  ,DS824_STAGE      VARCHAR(1)
  ,DS824_WIND       INTEGER
  ,DS824_PRES       INTEGER
  ,TD9636_LAT       NUMERIC(8,5)
  ,TD9636_LON       NUMERIC(8,5)
  ,TD9636_STAGE     VARCHAR(1)
  ,TD9636_WIND      INTEGER
  ,TD9636_PRES      INTEGER
  ,TD9635_LAT       NUMERIC(8,5)
  ,TD9635_LON       NUMERIC(8,5)
  ,TD9635_WIND      INTEGER
  ,TD9635_PRES      INTEGER
  ,TD9635_ROCI      VARCHAR(1)
  ,NEUMANN_LAT      NUMERIC(8,5)
  ,NEUMANN_LON      NUMERIC(8,5)
  ,NEUMANN_CLASS    VARCHAR(1)
  ,NEUMANN_WIND     INTEGER
  ,NEUMANN_PRES     INTEGER
  ,MLC_LAT          NUMERIC(8,5)
  ,MLC_LON          NUMERIC(8,5)
  ,MLC_CLASS        VARCHAR(1)
  ,MLC_WIND         INTEGER
  ,MLC_PRES         INTEGER
  ,USA_GUST         INTEGER
  ,BOM_GUST         INTEGER
  ,BOM_GUST_PER     INTEGER
  ,REUNION_GUST     INTEGER
  ,REUNION_GUST_PER BIT
  ,USA_SEAHGT       INTEGER
  ,USA_SEARAD_NE    INTEGER
  ,USA_SEARAD_SE    INTEGER
  ,USA_SEARAD_SW    INTEGER
  ,USA_SEARAD_NW    INTEGER
  ,STORM_SPEED      INTEGER
  ,STORM_DIR        INTEGER
);
.import ibtracs_all_NO_HEADING.csv AllBestTrack --csv
