#!/bin/sh
set -eu
export MYSQL_PWD="$(cat /run/secrets/mysql-root-password)"
result="$(mysql --protocol=socket -uroot --batch --skip-column-names -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${MYSQL_DATABASE}' AND table_name IN ('config_info','config_info_aggr','config_info_beta','config_info_tag','config_tags_relation','group_capacity','his_config_info','tenant_capacity','tenant_info','users','roles','permissions');")"
[ "$result" = 12 ]
